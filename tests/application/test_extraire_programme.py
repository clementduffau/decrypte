"""Tests de l'application : le cas d'usage « extraire les propositions ».

Tout est testé avec un FAUX extracteur : on choisit exactement ce que
« l'IA » répond (une citation exacte, une approchante, une inventée…) et on
vérifie que chaque réponse finit au bon endroit. Aucun appel réseau, aucun coût.
"""

from datetime import datetime, timezone

import pytest

from decrypte.application.extraire_programme import ALERTE_APPROCHANTE, ExtraireProgramme
from decrypte.domaine.decoupage import decouper
from decrypte.domaine.erreurs import ExtractionImpossible
from decrypte.domaine.modeles import Candidat, PropositionExtraite, StatutCitation, StatutRevue, Theme
from decrypte.ports.extraction import ExtracteurPropositions
from tests.conftest import PAGES_PROGRAMME_FICTIF, creer_document

HEURE_FIXE = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)

CANDIDAT = Candidat(
    id="camille-exemple",
    nom="Camille Exemple",
    parti="Mouvement Fictif pour les Tests",
    election="presidentielle-2027",
)

# Des réponses possibles de « l'IA », sur le programme fictif.
EXACTE = PropositionExtraite(
    citation="Nous proposons de créer 500 nouvelles maisons de santé d'ici 2030",
    resume_neutre="Créer 500 maisons de santé d'ici 2030",
    theme=Theme.SANTE,
    chiffres=["500", "2030"],
)
EXACTE_PAGE_2 = PropositionExtraite(
    citation="nous planterons 10 millions d'arbres en cinq ans",
    resume_neutre="Planter 10 millions d'arbres en cinq ans",
    theme=Theme.ENVIRONNEMENT_ENERGIE,
)
AUTRE_EXACTE_PAGE_2 = PropositionExtraite(
    citation="Nous simplifierons la déclaration de revenus grâce à un formulaire unique",
    resume_neutre="Un formulaire unique pour la déclaration de revenus",
    theme=Theme.FISCALITE,
)
APPROCHANTE = PropositionExtraite(  # « six mois » au lieu de « trois mois »
    citation="Nous instaurerons un service civique de six mois, ouvert à tous les jeunes",
    resume_neutre="Un service civique de six mois pour les jeunes",
    theme=Theme.EDUCATION,
)
INVENTEE = PropositionExtraite(
    citation="Nous supprimerons l'impôt sur le revenu pour tous les Français",
    resume_neutre="Supprimer l'impôt sur le revenu",
    theme=Theme.FISCALITE,
)


class FauxExtracteur:
    """Faux extracteur : renvoie les réponses prévues, une liste par appel, et note les textes reçus."""

    nom_modele = "faux-modele-v1"

    def __init__(self, *reponses: list[PropositionExtraite]) -> None:
        self._reponses = list(reponses)
        self.textes_recus: list[str] = []

    def extraire(self, texte: str) -> list[PropositionExtraite]:
        self.textes_recus.append(texte)
        return self._reponses.pop(0) if self._reponses else []


class ExtracteurEnPanne:
    nom_modele = "modele-en-panne"

    def extraire(self, texte: str) -> list[PropositionExtraite]:
        raise ExtractionImpossible("Le service d'IA ne répond pas.")


def extraire(extracteur, taille_morceau: int = 12_000, candidat: Candidat = CANDIDAT):
    """Lance le cas d'usage sur le programme fictif, avec une heure fixe."""
    document = creer_document(*PAGES_PROGRAMME_FICTIF)
    cas_usage = ExtraireProgramme(extracteur, horloge=lambda: HEURE_FIXE, taille_morceau=taille_morceau)
    return cas_usage.executer(document, candidat)


# ---------------------------------------------------------------------------
# Les trois verdicts
# ---------------------------------------------------------------------------


def test_le_faux_respecte_le_contrat():
    assert isinstance(FauxExtracteur(), ExtracteurPropositions)


def test_chaque_verdict_finit_au_bon_endroit():
    resultat = extraire(FauxExtracteur([EXACTE, APPROCHANTE, INVENTEE]))

    assert [p.citation for p in resultat.propositions] == [EXACTE.citation, APPROCHANTE.citation]
    assert [r.citation for r in resultat.rejetees] == [INVENTEE.citation]
    assert "introuvable" in resultat.rejetees[0].raison


def test_proposition_exacte_complete():
    proposition = extraire(FauxExtracteur([EXACTE])).propositions[0]

    assert proposition.id == "camille-exemple-001"
    assert proposition.candidat_id == "camille-exemple"
    assert proposition.verification.statut == StatutCitation.EXACTE
    assert proposition.verification.page == 1
    assert proposition.theme == Theme.SANTE        # recopié depuis la réponse de l'IA
    assert proposition.chiffres == ["500", "2030"]
    assert proposition.alertes == []
    assert proposition.revue == StatutRevue.A_VALIDER  # rien n'est publié sans relecture


def test_approchante_gardee_avec_une_alerte():
    proposition = extraire(FauxExtracteur([APPROCHANTE])).propositions[0]

    assert proposition.verification.statut == StatutCitation.APPROCHANTE
    assert proposition.alertes == [ALERTE_APPROCHANTE]
    assert "trois mois" in proposition.verification.extrait_source  # le relecteur voit le vrai texte


# ---------------------------------------------------------------------------
# Les informations du résultat
# ---------------------------------------------------------------------------


def test_informations_du_programme_extrait():
    document = creer_document(*PAGES_PROGRAMME_FICTIF)
    cas_usage = ExtraireProgramme(FauxExtracteur([EXACTE]), horloge=lambda: HEURE_FIXE)

    resultat = cas_usage.executer(document, CANDIDAT)

    assert resultat.candidat == CANDIDAT
    assert resultat.source == document.source
    assert resultat.extrait_le == HEURE_FIXE
    assert resultat.modele_llm == "faux-modele-v1"


def test_aucune_proposition_trouvee():
    resultat = extraire(FauxExtracteur([]))

    assert resultat.propositions == []
    assert resultat.rejetees == []


# ---------------------------------------------------------------------------
# Les morceaux envoyés à l'IA
# ---------------------------------------------------------------------------


def test_un_appel_par_morceau_avec_le_texte_intact():
    extracteur = FauxExtracteur()
    document = creer_document(*PAGES_PROGRAMME_FICTIF)

    extraire(extracteur, taille_morceau=300)  # chaque page fait ~250 caractères → 2 morceaux

    assert extracteur.textes_recus == [m.texte for m in decouper(document, 300)]
    assert len(extracteur.textes_recus) == 2


def test_le_nom_du_candidat_n_est_jamais_envoye():
    extracteur = FauxExtracteur()
    autre_candidat = Candidat(id="dominique-temoin", nom="Dominique Témoin", parti="Parti Témoin", election="test")

    extraire(extracteur, candidat=autre_candidat)

    for texte in extracteur.textes_recus:
        assert "Dominique Témoin" not in texte
        assert "Parti Témoin" not in texte


def test_numerotation_dans_l_ordre_sur_plusieurs_morceaux():
    extracteur = FauxExtracteur([EXACTE], [EXACTE_PAGE_2, AUTRE_EXACTE_PAGE_2])

    resultat = extraire(extracteur, taille_morceau=300)

    assert [p.id for p in resultat.propositions] == [
        "camille-exemple-001",
        "camille-exemple-002",
        "camille-exemple-003",
    ]
    assert [p.verification.page for p in resultat.propositions] == [1, 2, 2]


def test_doublons_ecartes():
    # L'IA renvoie la même proposition dans deux morceaux différents.
    resultat = extraire(FauxExtracteur([EXACTE], [EXACTE]), taille_morceau=300)

    assert len(resultat.propositions) == 1
    assert len(resultat.rejetees) == 1
    assert "doublon" in resultat.rejetees[0].raison


# ---------------------------------------------------------------------------
# Les pannes
# ---------------------------------------------------------------------------


def test_panne_de_l_ia_remonte():
    with pytest.raises(ExtractionImpossible, match="ne répond pas"):
        extraire(ExtracteurEnPanne())