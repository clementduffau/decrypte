"""Tests du domaine : la vérification des citations renvoyées par l'IA.

Le document de test est le programme fictif du conftest. On vérifie les
trois verdicts possibles (exacte, approchante, introuvable), puis les
différences d'écriture qui ne doivent PAS empêcher de trouver une citation.
"""

import pytest

from decrypte.domaine.modeles import StatutCitation
from decrypte.domaine.verification import VerificateurCitations, decouper_en_mots
from tests.conftest import PAGES_PROGRAMME_FICTIF, creer_document


@pytest.fixture
def verificateur() -> VerificateurCitations:
    """Un vérificateur préparé sur le programme fictif (2 pages)."""
    return VerificateurCitations(creer_document(*PAGES_PROGRAMME_FICTIF))


# ---------------------------------------------------------------------------
# Les mots
# ---------------------------------------------------------------------------


def test_decouper_en_mots_ignore_ponctuation_majuscules_et_ligatures():
    formes = [mot.forme for mot in decouper_en_mots("L’État, d'ici 2030 ! ﬁnancer")]
    assert formes == ["l", "état", "d", "ici", "2030", "financer"]


def test_decouper_en_mots_garde_la_position_d_origine():
    texte = "Créer 500 maisons"
    mots = decouper_en_mots(texte, page=3)

    assert mots[1].page == 3
    assert texte[mots[1].debut : mots[1].fin] == "500"


# ---------------------------------------------------------------------------
# Citation EXACTE
# ---------------------------------------------------------------------------


def test_citation_exacte(verificateur):
    verification = verificateur.verifier("Nous ouvrirons les bibliothèques municipales le dimanche")

    assert verification.statut == StatutCitation.EXACTE
    assert verification.score == 1.0
    assert verification.page == 1
    assert verification.extrait_source == "Nous ouvrirons les bibliothèques municipales le dimanche"


def test_citation_trouvee_sur_la_bonne_page(verificateur):
    verification = verificateur.verifier("nous planterons 10 millions d'arbres en cinq ans")

    assert verification.statut == StatutCitation.EXACTE
    assert verification.page == 2


def test_differences_sans_importance_ignorees(verificateur):
    # Majuscules, apostrophe typographique ’, espaces en trop, guillemets, point final.
    citation = "« NOUS PROPOSONS   de créer 500 nouvelles maisons de santé d’ici 2030. »"

    verification = verificateur.verifier(citation)

    assert verification.statut == StatutCitation.EXACTE
    # L'extrait renvoyé est celui du programme, pas celui de l'IA.
    assert verification.extrait_source == "Nous proposons de créer 500 nouvelles maisons de santé d'ici 2030"


def test_texte_pdf_avec_retours_a_la_ligne_espaces_insecables_et_ligatures():
    # Ce que pypdf renvoie souvent : retours à la ligne, espace insécable (\u00a0), ligature « ﬁ ».
    page = "Nous voulons\nﬁnancer 10\u00a0000 places\nde crèche d’ici 2027."
    verificateur = VerificateurCitations(creer_document(page))

    verification = verificateur.verifier("Nous voulons financer 10 000 places de crèche d'ici 2027")

    assert verification.statut == StatutCitation.EXACTE
    assert verification.extrait_source == "Nous voulons\nﬁnancer 10\u00a0000 places\nde crèche d’ici 2027"


def test_citation_a_cheval_sur_deux_pages():
    document = creer_document("Fin de la page un : nous créerons", "un service public de la petite enfance. Suite.")
    verificateur = VerificateurCitations(document)

    verification = verificateur.verifier("nous créerons un service public de la petite enfance")

    assert verification.statut == StatutCitation.EXACTE
    assert verification.page == 1  # la page où la citation commence
    assert verification.extrait_source == "nous créerons\nun service public de la petite enfance"


# ---------------------------------------------------------------------------
# Citation APPROCHANTE : un humain devra trancher
# ---------------------------------------------------------------------------


def test_un_mot_change_donne_une_citation_approchante(verificateur):
    # L'IA a écrit « six mois » au lieu de « trois mois » : grave pour l'utilisateur !
    verification = verificateur.verifier("Nous instaurerons un service civique de six mois, ouvert à tous les jeunes")

    assert verification.statut == StatutCitation.APPROCHANTE
    assert 0.85 <= verification.score < 1
    assert verification.page == 2
    # Le relecteur voit ce que dit VRAIMENT le programme.
    assert "trois mois" in verification.extrait_source


def test_mots_remplaces_donnent_une_citation_approchante(verificateur):
    citation = (
        "Nous proposons de créer 500 nouvelles maisons médicales d'ici 2030 "
        "dans les communes de moins de 10 000 habitants"
    )

    verification = verificateur.verifier(citation)

    assert verification.statut == StatutCitation.APPROCHANTE
    assert verification.extrait_source.startswith("Nous proposons de créer 500 nouvelles maisons de santé")


def test_deux_phrases_recollees_donnent_une_citation_approchante(verificateur):
    # Erreur typique d'une IA : coller deux phrases éloignées avec « et ».
    citation = "Nous ouvrirons les bibliothèques municipales le dimanche et nous planterons 10 millions d'arbres"

    verification = verificateur.verifier(citation)

    assert verification.statut == StatutCitation.APPROCHANTE


# ---------------------------------------------------------------------------
# Citation INTROUVABLE : la proposition sera rejetée
# ---------------------------------------------------------------------------


def test_citation_inventee_introuvable(verificateur):
    verification = verificateur.verifier("Nous supprimerons l'impôt sur le revenu pour tous les Français")

    assert verification.statut == StatutCitation.INTROUVABLE
    assert verification.score < 0.85
    assert verification.page is None
    assert verification.extrait_source is None


def test_paraphrase_introuvable(verificateur):
    # Une reformulation n'est pas une citation, même si le sens est proche.
    verification = verificateur.verifier("Le candidat veut créer des maisons de santé dans les petites communes")

    assert verification.statut == StatutCitation.INTROUVABLE


def test_citation_sans_aucun_mot(verificateur):
    verification = verificateur.verifier("… !")

    assert verification.statut == StatutCitation.INTROUVABLE
    assert verification.score == 0


# ---------------------------------------------------------------------------
# Réglages et réutilisation
# ---------------------------------------------------------------------------


def test_seuil_reglable():
    strict = VerificateurCitations(creer_document(*PAGES_PROGRAMME_FICTIF), seuil=0.95)

    verification = strict.verifier("Nous instaurerons un service civique de six mois, ouvert à tous les jeunes")

    assert verification.statut == StatutCitation.INTROUVABLE  # 0.92 < 0.95


def test_un_meme_verificateur_pour_plusieurs_citations(verificateur):
    citations = [
        "Nous ouvrirons les bibliothèques municipales le dimanche",
        "Nous supprimerons l'impôt sur le revenu pour tous les Français",
        "Nous instaurerons un service civique de six mois, ouvert à tous les jeunes",
        "nous planterons 10 millions d'arbres en cinq ans",
    ]

    statuts = [verificateur.verifier(citation).statut for citation in citations]

    assert statuts == [
        StatutCitation.EXACTE,
        StatutCitation.INTROUVABLE,
        StatutCitation.APPROCHANTE,
        StatutCitation.EXACTE,
    ]