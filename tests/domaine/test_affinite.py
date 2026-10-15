"""Tests du domaine : le calcul de l'affinité avec les candidats."""

import pytest

from decrypte.domaine.affinite import Reponse, calculer_affinites
from decrypte.domaine.erreurs import ReponsesInvalides
from decrypte.domaine.modeles import Proposition, StatutCitation, Theme, Verification

OUI, NON, BOF = Reponse.D_ACCORD, Reponse.PAS_D_ACCORD, Reponse.SANS_AVIS


def proposition(identifiant: str, candidat_id: str, theme: Theme = Theme.AUTRE) -> Proposition:
    """Fabrique une proposition de test : seuls l'identifiant, le candidat et le thème comptent ici."""
    return Proposition(
        id=identifiant,
        candidat_id=candidat_id,
        citation="Une citation de test suffisamment longue pour être valide.",
        resume_neutre="Résumé de test",
        theme=theme,
        verification=Verification(statut=StatutCitation.EXACTE, score=1.0),
    )


# Deux candidats fictifs, avec 3 propositions chacun.
PROPOSITIONS = [
    proposition("a-1", "candidat-a", Theme.SANTE),
    proposition("a-2", "candidat-a", Theme.SANTE),
    proposition("a-3", "candidat-a", Theme.FISCALITE),
    proposition("b-1", "candidat-b", Theme.SANTE),
    proposition("b-2", "candidat-b", Theme.EDUCATION),
    proposition("b-3", "candidat-b", Theme.FISCALITE),
]


def affinite_de(candidat_id, affinites):
    return next(a for a in affinites if a.candidat_id == candidat_id)


# ---------------------------------------------------------------------------
# Le score
# ---------------------------------------------------------------------------


def test_score_d_un_candidat():
    affinites = calculer_affinites(PROPOSITIONS, {"a-1": OUI, "a-2": OUI, "a-3": NON})

    a = affinite_de("candidat-a", affinites)
    assert a.score == 2 / 3
    assert a.nb_reponses == 3


def test_sans_avis_ne_compte_pas():
    affinites = calculer_affinites(PROPOSITIONS, {"a-1": OUI, "a-2": BOF, "a-3": BOF})

    a = affinite_de("candidat-a", affinites)
    assert a.score == 1.0      # 1 accord sur 1 réponse qui compte
    assert a.nb_reponses == 1


def test_les_propositions_sans_reponse_ne_comptent_pas():
    affinites = calculer_affinites(PROPOSITIONS, {"a-1": NON})
    assert affinite_de("candidat-a", affinites).score == 0.0


def test_candidat_sans_reponse():
    affinites = calculer_affinites(PROPOSITIONS, {"a-1": OUI})

    b = affinite_de("candidat-b", affinites)
    assert b.score is None
    assert b.nb_reponses == 0


# ---------------------------------------------------------------------------
# L'ordre des candidats
# ---------------------------------------------------------------------------


def test_candidats_tries_du_meilleur_score_au_plus_bas():
    reponses = {"a-1": NON, "a-2": NON, "a-3": OUI, "b-1": OUI, "b-2": OUI, "b-3": NON}

    affinites = calculer_affinites(PROPOSITIONS, reponses)

    assert [a.candidat_id for a in affinites] == ["candidat-b", "candidat-a"]  # 2/3 avant 1/3


def test_candidat_sans_reponse_classe_en_dernier():
    affinites = calculer_affinites(PROPOSITIONS, {"b-1": NON})  # B : 0 %, A : aucune réponse

    assert [a.candidat_id for a in affinites] == ["candidat-b", "candidat-a"]


def test_egalite_departagee_par_ordre_alphabetique():
    # Ni l'ordre des propositions ni celui des réponses ne doit favoriser un candidat.
    affinites = calculer_affinites(list(reversed(PROPOSITIONS)), {"b-1": OUI, "a-1": OUI})

    assert [a.candidat_id for a in affinites] == ["candidat-a", "candidat-b"]


# ---------------------------------------------------------------------------
# L'explication
# ---------------------------------------------------------------------------


def test_listes_des_accords_et_desaccords():
    affinites = calculer_affinites(PROPOSITIONS, {"a-1": OUI, "a-2": NON, "a-3": OUI})

    a = affinite_de("candidat-a", affinites)
    assert a.accords == ["a-1", "a-3"]
    assert a.desaccords == ["a-2"]


def test_detail_par_theme():
    affinites = calculer_affinites(PROPOSITIONS, {"a-1": OUI, "a-2": OUI, "a-3": NON})

    detail = {d.theme: (d.accords, d.desaccords) for d in affinite_de("candidat-a", affinites).par_theme}
    assert detail == {Theme.SANTE: (2, 0), Theme.FISCALITE: (0, 1)}  # les thèmes sans réponse sont absents


def test_score_peu_fiable_avec_peu_de_reponses():
    affinites = calculer_affinites(PROPOSITIONS, {"a-1": OUI, "a-2": OUI, "b-1": OUI, "b-2": OUI, "b-3": NON})

    assert not affinite_de("candidat-a", affinites).fiable  # 2 réponses
    assert affinite_de("candidat-b", affinites).fiable      # 3 réponses


# ---------------------------------------------------------------------------
# Réponses invalides
# ---------------------------------------------------------------------------


def test_reponse_a_une_proposition_inconnue():
    with pytest.raises(ReponsesInvalides, match="z-9"):
        calculer_affinites(PROPOSITIONS, {"a-1": OUI, "z-9": OUI})