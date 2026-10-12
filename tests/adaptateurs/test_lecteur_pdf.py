"""Tests de l'adaptateur LecteurPdf."""

import pytest

from decrypte.adaptateurs.lecteurs.pdf import LecteurPdf
from decrypte.domaine.erreurs import DocumentIllisible
from decrypte.ports.lecture import LecteurDocument
from tests.conftest import aplatir, ecrire_pdf


def test_respecte_le_contrat_du_port():
    assert isinstance(LecteurPdf(), LecteurDocument)


def test_formats_annonces():
    lecteur = LecteurPdf()
    assert lecteur.type_document == "pdf"
    assert lecteur.extensions == (".pdf",)


def test_deux_pages_dans_le_bon_ordre(programme_pdf):
    pages = LecteurPdf().lire(programme_pdf.read_bytes())

    assert [page.numero for page in pages] == [1, 2]
    assert "maisons de santé" in aplatir(pages[0].texte)
    assert "service civique" in aplatir(pages[1].texte)


def test_chiffres_et_accents_conserves(programme_pdf):
    texte = aplatir(LecteurPdf().lire(programme_pdf.read_bytes())[0].texte)

    assert "500 nouvelles maisons de santé d'ici 2030" in texte


def test_pages_blanches_lues_sans_erreur(tmp_path):

    pdf_blanc = ecrire_pdf(tmp_path / "blanc.pdf", ["", ""])

    pages = LecteurPdf().lire(pdf_blanc.read_bytes())

    assert [page.numero for page in pages] == [1, 2]
    assert all(page.texte.strip() == "" for page in pages)


def test_fichier_qui_n_est_pas_un_pdf_refuse():
    with pytest.raises(DocumentIllisible, match="PDF valide"):
        LecteurPdf().lire(b"ceci n'est pas un PDF")