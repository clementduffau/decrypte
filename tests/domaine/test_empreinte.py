"""Tests du domaine : l'empreinte d'un document."""

from decrypte.domaine.empreinte import calculer_empreinte


def test_empreinte_de_64_caracteres():
    assert len(calculer_empreinte(b"Programme")) == 64


def test_meme_contenu_meme_empreinte():
    assert calculer_empreinte(b"Version 1") == calculer_empreinte(b"Version 1")


def test_un_caractere_change_tout():
    assert calculer_empreinte(b"Version 1") != calculer_empreinte(b"Version 2")