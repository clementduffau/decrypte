"""Tests du domaine : le découpage d'un programme en morceaux pour l'IA."""

import pytest


from decrypte.domaine.decoupage import couper_texte, decouper
from tests.conftest import PAGES_PROGRAMME_FICTIF, creer_document




# ---------------------------------------------------------------------------
# decouper : regrouper les pages
# ---------------------------------------------------------------------------


def test_petit_programme_en_un_seul_morceau():
    morceaux = decouper(creer_document(*PAGES_PROGRAMME_FICTIF))

    assert len(morceaux) == 1
    assert morceaux[0].numero == 1
    assert morceaux[0].pages == [1, 2]
    assert morceaux[0].texte == PAGES_PROGRAMME_FICTIF[0] + "\n\n" + PAGES_PROGRAMME_FICTIF[1]


def test_pages_regroupees_sans_depasser_la_taille():
    document = creer_document(*["a" * 400] * 5)  # 5 pages de 400 caractères

    morceaux = decouper(document, taille_max=1000)

    assert [m.pages for m in morceaux] == [[1, 2], [3, 4], [5]]  # 400 + 2 + 400 = 802 ≤ 1000
    assert all(len(m.texte) <= 1000 for m in morceaux)
    assert [m.numero for m in morceaux] == [1, 2, 3]


def test_aucun_texte_perdu_ni_modifie():
    textes = [f"Page {i} : nous proposons la mesure numéro {i}.  " * 10 for i in range(1, 8)]

    morceaux = decouper(creer_document(*textes), taille_max=1000)

    assert "\n\n".join(m.texte for m in morceaux) == "\n\n".join(textes)


def test_pages_blanches_ignorees():
    document = creer_document("Première page de texte.", "   \n  ", "Troisième page de texte.")

    morceaux = decouper(document)

    assert morceaux[0].pages == [1, 3]  # la page 2 n'est envoyée nulle part
    assert "   \n  " not in morceaux[0].texte


def test_document_sans_texte():
    assert decouper(creer_document("", "  \n ")) == []


def test_page_trop_longue_coupee_en_plusieurs_morceaux():
    page_web = ("x" * 49 + "\n") * 50  # une seule page de 2 500 caractères, en lignes de 50

    morceaux = decouper(creer_document(page_web), taille_max=1000)

    assert len(morceaux) == 3
    assert all(m.pages == [1] for m in morceaux)  # tous viennent de la page 1
    assert "".join(m.texte for m in morceaux) == page_web  # rien de perdu


def test_page_longue_au_milieu_du_document():
    courte = "c" * 300
    longue = ("x" * 49 + "\n") * 50  # 2 500 caractères → 3 blocs de 1 000, 1 000 et 500

    morceaux = decouper(creer_document(courte, longue, courte), taille_max=1000)

    # La fin de la page 2 (500 caractères) a assez de place pour accueillir la page 3.
    assert [m.pages for m in morceaux] == [[1], [2], [2], [2, 3]]


# ---------------------------------------------------------------------------
# couper_texte : couper une page trop longue
# ---------------------------------------------------------------------------


def test_texte_court_non_coupe():
    assert couper_texte("Un texte court.", taille_max=1000) == ["Un texte court."]


def test_ligne_geante_coupee_entre_deux_mots():
    texte = "mot " * 600  # 2 400 caractères, sans aucun retour à la ligne

    blocs = couper_texte(texte, taille_max=1000)

    assert "".join(blocs) == texte  # aucun caractère perdu
    assert all(len(bloc) <= 1000 for bloc in blocs)
    assert all(bloc.endswith(" ") for bloc in blocs)  # jamais de mot coupé en deux


def test_mot_geant_coupe_net():
    blocs = couper_texte("a" * 2500, taille_max=1000)  # pas d'espace : impossible de faire mieux
    assert [len(bloc) for bloc in blocs] == [1000, 1000, 500]


def test_taille_invalide_refusee():
    with pytest.raises(ValueError, match="au moins 1"):
        couper_texte("du texte", taille_max=0)