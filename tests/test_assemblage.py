

import pytest

from decrypte.application.charger_programme import ChargerProgramme
from decrypte.assemblage import creer_charger_programme
from decrypte.domaine.erreurs import FichierIntrouvable, FormatNonGere
from tests.conftest import PAGES_PROGRAMME_FICTIF, aplatir

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