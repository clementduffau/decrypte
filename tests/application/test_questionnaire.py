"""Tests de l'application : le questionnaire (cartes) et le calcul des résultats.

Le stockage est remplacé par un faux, en mémoire : pas de fichier, des tests instantanés.
"""

import random
from datetime import datetime, timezone

import pytest

from decrypte.application.questionnaire import (
    CalculerResultats,
    ConstruireQuestionnaire,
    est_publiable,
    identifiant_anonyme,
)
from decrypte.domaine.affinite import Reponse
from decrypte.domaine.erreurs import ProgrammeIntrouvable, ReponsesInvalides
from decrypte.domaine.modeles import (
    Candidat,
    ProgrammeExtrait,
    Proposition,
    StatutCitation,
    StatutRevue,
    Theme,
    Verification,
)
from decrypte.ports.stockage import StockageProgrammes
from tests.conftest import creer_document

# ---------------------------------------------------------------------------
# Les outils : un faux stockage et des programmes fictifs
# ---------------------------------------------------------------------------


class FauxStockage:
    """Faux stockage en mémoire : un dictionnaire identifiant du candidat → programme."""

    def __init__(self, *programmes: ProgrammeExtrait) -> None:
        self._programmes = {p.candidat.id: p for p in programmes}

    def enregistrer(self, programme: ProgrammeExtrait) -> str:
        self._programmes[programme.candidat.id] = programme
        return "en mémoire"

    def charger(self, candidat_id: str) -> ProgrammeExtrait:
        if candidat_id not in self._programmes:
            raise ProgrammeIntrouvable(candidat_id)
        return self._programmes[candidat_id]

    def lister_candidats(self) -> list[str]:
        return sorted(self._programmes)


def proposition(
    identifiant: str,
    statut: StatutCitation = StatutCitation.EXACTE,
    revue: StatutRevue = StatutRevue.A_VALIDER,
    theme: Theme = Theme.AUTRE,
) -> Proposition:
    candidat_id = identifiant.rsplit("-", 1)[0]                              # "candidat-a-1" → "candidat-a"
    etiquette = identifiant.removeprefix("candidat-").replace("-", "").upper()  # "candidat-a-1" → "A1"
    return Proposition(
        id=identifiant,
        candidat_id=candidat_id,
        citation=f"Citation de test pour la mesure {etiquette}, assez longue.",
        resume_neutre=f"Mesure {etiquette}",
        theme=theme,
        verification=Verification(statut=statut, score=1.0, page=1),
        revue=revue,
    )


def programme(candidat_id: str, nom: str, *propositions: Proposition) -> ProgrammeExtrait:
    return ProgrammeExtrait(
        candidat=Candidat(id=candidat_id, nom=nom, parti="Parti de test", election="test"),
        source=creer_document("texte").source,
        extrait_le=datetime(2026, 10, 15, tzinfo=timezone.utc),
        modele_llm="faux-modele",
        propositions=list(propositions),
    )


PROGRAMME_A = programme(
    "candidat-a", "Alice Exemple",
    proposition("candidat-a-1", theme=Theme.SANTE),
    proposition("candidat-a-2", theme=Theme.SANTE),
    proposition("candidat-a-3", statut=StatutCitation.APPROCHANTE),  # pas encore validée : non publiée
)
PROGRAMME_B = programme(
    "candidat-b", "Bruno Exemple",
    proposition("candidat-b-1", theme=Theme.EDUCATION),
    proposition("candidat-b-2", revue=StatutRevue.REJETEE),           # rejetée : non publiée
)


def carte_de(identifiant_proposition: str, cartes):
    """Retrouve la carte d'une proposition (dans les tests, on connaît le lien)."""
    cible = identifiant_anonyme(proposition(identifiant_proposition))
    return next(c for c in cartes if c.id == cible)


# ---------------------------------------------------------------------------
# La règle de publication et l'anonymat
# ---------------------------------------------------------------------------


def test_le_faux_stockage_respecte_le_contrat():
    assert isinstance(FauxStockage(), StockageProgrammes)


def test_regle_de_publication():
    assert est_publiable(proposition("x-1"))                                               # exacte
    assert not est_publiable(proposition("x-2", statut=StatutCitation.APPROCHANTE))        # à vérifier
    assert est_publiable(
        proposition("x-3", statut=StatutCitation.APPROCHANTE, revue=StatutRevue.VALIDEE)   # vérifiée par un humain
    )
    assert not est_publiable(proposition("x-4", revue=StatutRevue.REJETEE))                # rejetée


def test_identifiant_anonyme_stable_et_opaque():
    identifiant = identifiant_anonyme(proposition("candidat-a-1"))

    assert identifiant == identifiant_anonyme(proposition("candidat-a-1"))  # toujours le même
    assert len(identifiant) == 12
    assert "candidat" not in identifiant


# ---------------------------------------------------------------------------
# ConstruireQuestionnaire
# ---------------------------------------------------------------------------


def test_seules_les_propositions_publiables_deviennent_des_cartes():
    cartes = ConstruireQuestionnaire(FauxStockage(PROGRAMME_A, PROGRAMME_B)).executer()
    assert len(cartes) == 3  # a-1, a-2, b-1


def test_aucune_carte_ne_revele_le_candidat():
    cartes = ConstruireQuestionnaire(FauxStockage(PROGRAMME_A, PROGRAMME_B)).executer()

    for carte in cartes:
        contenu = carte.model_dump_json()
        for indice in ("candidat-a", "candidat-b", "Alice", "Bruno", "Parti de test"):
            assert indice not in contenu


def test_melange_reproductible_avec_la_meme_graine():
    stockage = FauxStockage(PROGRAMME_A, PROGRAMME_B)

    premier = ConstruireQuestionnaire(stockage, aleatoire=random.Random(7)).executer()
    second = ConstruireQuestionnaire(stockage, aleatoire=random.Random(7)).executer()

    assert [c.id for c in premier] == [c.id for c in second]


def test_nombre_de_cartes_limite_par_candidat():
    beaucoup = programme("candidat-c", "Chris Exemple", *[proposition(f"candidat-c-{i}") for i in range(1, 11)])
    stockage = FauxStockage(PROGRAMME_A, beaucoup)

    cartes = ConstruireQuestionnaire(stockage, aleatoire=random.Random(1), par_candidat=2).executer()

    assert len(cartes) == 4  # 2 pour A (qui en a 2), 2 pour C (tirées au sort parmi 10)


# ---------------------------------------------------------------------------
# CalculerResultats
# ---------------------------------------------------------------------------


def test_resultats_avec_le_candidat_et_l_explication():
    stockage = FauxStockage(PROGRAMME_A, PROGRAMME_B)
    cartes = ConstruireQuestionnaire(stockage).executer()
    reponses = {
        carte_de("candidat-a-1", cartes).id: Reponse.D_ACCORD,
        carte_de("candidat-a-2", cartes).id: Reponse.PAS_D_ACCORD,
        carte_de("candidat-b-1", cartes).id: Reponse.D_ACCORD,
    }

    resultats = CalculerResultats(stockage).executer(reponses)

    assert [r.candidat.nom for r in resultats] == ["Bruno Exemple", "Alice Exemple"]  # 100 % puis 50 %
    alice = resultats[1]
    assert alice.score == 0.5
    assert [c.resume for c in alice.accords] == ["Mesure A1"]
    assert [c.resume for c in alice.desaccords] == ["Mesure A2"]


def test_reponse_a_une_carte_inconnue():
    with pytest.raises(ReponsesInvalides, match="zzz"):
        CalculerResultats(FauxStockage(PROGRAMME_A)).executer({"zzz": Reponse.D_ACCORD})


def test_reponse_a_une_carte_non_publiee():
    # La proposition approchante non validée n'a pas de carte : on ne peut pas y répondre.
    carte_cachee = identifiant_anonyme(proposition("candidat-a-3"))

    with pytest.raises(ReponsesInvalides):
        CalculerResultats(FauxStockage(PROGRAMME_A)).executer({carte_cachee: Reponse.D_ACCORD})