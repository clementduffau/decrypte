"""Tests de l'assemblage : les vrais adaptateurs sont-ils bien branchés ?

Ici, pas de faux : on vérifie que les cas d'usage fabriqués par l'assemblage
utilisent les bons adaptateurs (lecteurs, Mistral, stockage JSON).
Aucun appel à Mistral n'est fait : on vérifie le branchement, pas l'IA.
"""

import pytest

from decrypte.adaptateurs.ia.mistral import MODELE_PAR_DEFAUT, ExtracteurMistral
from decrypte.adaptateurs.stockage_json import StockageJson
from decrypte.application.charger_programme import ChargerProgramme
from decrypte.application.extraire_programme import ExtraireProgramme
from decrypte.assemblage import creer_charger_programme, creer_extraire_programme, creer_stockage
from decrypte.domaine.erreurs import ExtractionImpossible, FichierIntrouvable, FormatNonGere
from tests.conftest import PAGES_PROGRAMME_FICTIF, aplatir

# Le programme fictif en un seul texte (plus de 200 caractères).
TEXTE_COMPLET = " ".join(PAGES_PROGRAMME_FICTIF)


def test_renvoie_un_cas_d_usage_pret():
    assert isinstance(creer_charger_programme(), ChargerProgramme)


def test_lit_un_pdf(programme_pdf):
    document = creer_charger_programme().executer(programme_pdf)

    assert document.source.type == "pdf"
    assert document.source.nb_pages == 2
    assert "maisons de santé" in aplatir(document.pages[0].texte)


def test_lit_une_page_html(tmp_path):
    fichier = tmp_path / "programme.html"
    fichier.write_text(
        f"<html><body><nav>Menu du site</nav><p>{TEXTE_COMPLET}</p></body></html>",
        encoding="utf-8",
    )

    document = creer_charger_programme().executer(fichier)

    assert document.source.type == "html"
    assert "service civique" in document.pages[0].texte
    assert "Menu du site" not in document.pages[0].texte  # le vrai LecteurHtml a retiré le menu


def test_lit_un_fichier_texte(tmp_path):
    fichier = tmp_path / "programme.txt"
    fichier.write_text("\f".join(PAGES_PROGRAMME_FICTIF), encoding="utf-8")  # \f = saut de page

    document = creer_charger_programme().executer(fichier)

    assert document.source.type == "texte"
    assert document.source.nb_pages == 2


def test_lit_un_fichier_markdown(tmp_path):
    fichier = tmp_path / "programme.md"
    fichier.write_text(f"# Programme\n\n{TEXTE_COMPLET}", encoding="utf-8")

    assert creer_charger_programme().executer(fichier).source.type == "texte"


def test_refuse_un_format_inconnu_et_liste_les_formats(tmp_path):
    fichier = tmp_path / "programme.docx"
    fichier.write_bytes(b"contenu Word")

    # Les 5 extensions des 3 vrais lecteurs, triées par ordre alphabétique.
    with pytest.raises(FormatNonGere, match=r"formats acceptés : \.htm, \.html, \.md, \.pdf, \.txt"):
        creer_charger_programme().executer(fichier)


def test_branche_le_vrai_disque(tmp_path):
    with pytest.raises(FichierIntrouvable):
        creer_charger_programme().executer(tmp_path / "absent.pdf")


# ---------------------------------------------------------------------------
# Extraction et stockage
# ---------------------------------------------------------------------------


def test_extraction_branchee_sur_mistral_avec_le_modele_choisi():
    cas_usage = creer_extraire_programme({"MISTRAL_API_KEY": "cle-de-test", "MISTRAL_MODELE": "ministral-8b-2512"})

    assert isinstance(cas_usage, ExtraireProgramme)
    # Un test d'assemblage a le droit de regarder à l'intérieur : c'est le branchement qu'il vérifie.
    assert isinstance(cas_usage._extracteur, ExtracteurMistral)
    assert cas_usage._extracteur.nom_modele == "ministral-8b-2512"


def test_modele_par_defaut_si_absent_du_env():
    cas_usage = creer_extraire_programme({"MISTRAL_API_KEY": "cle-de-test"})
    assert cas_usage._extracteur.nom_modele == MODELE_PAR_DEFAUT


def test_cle_manquante_message_clair():
    with pytest.raises(ExtractionImpossible, match="MISTRAL_API_KEY"):
        creer_extraire_programme({})


def test_stockage_en_json(tmp_path):
    assert isinstance(creer_stockage(tmp_path), StockageJson)