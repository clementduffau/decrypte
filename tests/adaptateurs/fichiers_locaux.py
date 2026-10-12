"""Tests de l'adaptateur FichiersLocaux."""

import pytest

from decrypte.adaptateurs.fichiers_locaux import FichiersLocaux
from decrypte.adaptateurs.lecteurs.pdf import LecteurPdf
from decrypte.domaine.erreurs import FichierIntrouvable
from decrypte.ports.lecture import SourceFichiers
from tests.conftest import aplatir


def test_respecte_le_contrat_du_port():
    assert isinstance(FichiersLocaux(), SourceFichiers)


def test_lit_les_octets_sans_les_modifier(tmp_path):
    fichier = tmp_path / "programme.bin"
    contenu = b"\x00\xffcontenu brut\n\xe9"  # des octets quelconques, même non lisibles en texte
    fichier.write_bytes(contenu)

    assert FichiersLocaux().lire_octets(fichier) == contenu


def test_accepte_un_chemin_ecrit_en_texte(tmp_path):
    fichier = tmp_path / "programme.txt"
    fichier.write_bytes(b"contenu")

    assert FichiersLocaux().lire_octets(str(fichier)) == b"contenu"


def test_fichier_absent_refuse(tmp_path):
    with pytest.raises(FichierIntrouvable, match="absent.pdf"):
        FichiersLocaux().lire_octets(tmp_path / "absent.pdf")


def test_dossier_refuse(tmp_path):
    with pytest.raises(FichierIntrouvable):
        FichiersLocaux().lire_octets(tmp_path)  # tmp_path est un dossier, pas un fichier


def test_s_enchaine_avec_un_lecteur(programme_pdf):
    # Aperçu du cas d'usage : la source donne les octets, le lecteur les transforme en pages.
    octets = FichiersLocaux().lire_octets(programme_pdf)
    pages = LecteurPdf().lire(octets)

    assert len(pages) == 2
    assert "maisons de santé" in aplatir(pages[0].texte)