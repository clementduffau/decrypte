"""Tests de l'adaptateur LecteurTexte."""

import pytest

from decrypte.adaptateurs.lecteurs.texte import LecteurTexte
from decrypte.domaine.erreurs import DocumentIllisible
from decrypte.domaine.modeles import Page
from decrypte.ports.lecture import LecteurDocument


def test_respecte_le_contrat_du_port():
    assert isinstance(LecteurTexte(), LecteurDocument)


def test_formats_annonces():
    lecteur = LecteurTexte()
    assert lecteur.type_document == "texte"
    assert lecteur.extensions == (".txt", ".md")


def test_texte_sans_saut_de_page_donne_une_page():
    pages = LecteurTexte().lire("Créer 500 maisons de santé.".encode("utf-8"))

    assert pages == [Page(numero=1, texte="Créer 500 maisons de santé.")]


def test_saut_de_page_separe_les_pages():
    pages = LecteurTexte().lire("Page un\fPage deux\fPage trois".encode("utf-8"))

    assert [page.numero for page in pages] == [1, 2, 3]
    assert [page.texte for page in pages] == ["Page un", "Page deux", "Page trois"]


def test_texte_jamais_modifie():
    # Les espaces, retours à la ligne et accents doivent rester tels quels :
    # les citations du LLM seront comparées à ce texte à l'étape 5.
    texte = "  Nous créerons\n500 maisons   de santé, d’ici 2030 !  "

    pages = LecteurTexte().lire(texte.encode("utf-8"))

    assert pages[0].texte == texte


def test_marqueur_bom_retire():
    pages = LecteurTexte().lire("\ufeffProgramme".encode("utf-8"))

    assert pages[0].texte == "Programme"


def test_encodage_autre_que_utf8_refuse():
    texte_latin1 = "Créer des maisons de santé".encode("latin-1")  # « é » encodé autrement

    with pytest.raises(DocumentIllisible, match="UTF-8"):
        LecteurTexte().lire(texte_latin1)