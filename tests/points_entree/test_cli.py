"""Tests du point d'entrée : la ligne de commande, branchée sur les vrais adaptateurs.

Ces tests traversent tout l'hexagone : commande → assemblage → cas d'usage
→ lecteur → disque. On appelle main() avec une liste d'arguments, exactement
comme si on les avait tapés dans le terminal.

capsys est fourni par pytest : il capture ce que le programme affiche,
séparément pour la sortie normale (out) et la sortie d'erreur (err).
"""

import pytest

from decrypte.domaine.empreinte import calculer_empreinte
from decrypte.points_entree.cli import main
from tests.conftest import aplatir

# ---------------------------------------------------------------------------
# Quand tout va bien
# ---------------------------------------------------------------------------


def test_apercu_d_un_pdf(programme_pdf, capsys):
    code_retour = main(["apercu", str(programme_pdf)])

    sortie = capsys.readouterr()
    texte = aplatir(sortie.out)  # "Type     : pdf" devient "Type : pdf"
    assert code_retour == 0
    assert "Type : pdf" in texte
    assert "Pages : 2" in texte
    assert "Camille Exemple" in texte
    assert sortie.err == ""  # aucune erreur affichée

def test_apercu_affiche_l_empreinte(programme_pdf, capsys):
    main(["apercu", str(programme_pdf)])

    empreinte = calculer_empreinte(programme_pdf.read_bytes())
    assert f"SHA-256 : {empreinte}" in aplatir(capsys.readouterr().out)

def test_option_pages_limite_l_affichage(programme_pdf, capsys):
    main(["apercu", str(programme_pdf), "--pages", "1"])

    sortie = capsys.readouterr().out
    assert "--- Page 1" in sortie
    assert "--- Page 2" not in sortie


def test_page_longue_coupee(tmp_path, capsys):
    fichier = tmp_path / "long.txt"
    fichier.write_text("Proposition. " * 100, encoding="utf-8")  # 1 300 caractères

    main(["apercu", str(fichier)])

    assert "[…]" in capsys.readouterr().out  # l'aperçu signale que la page est coupée


# ---------------------------------------------------------------------------
# Quand quelque chose ne va pas : message clair sur la sortie d'erreur, code 1
# ---------------------------------------------------------------------------


def test_format_non_gere(tmp_path, capsys):
    fichier = tmp_path / "programme.docx"
    fichier.write_bytes(b"contenu Word")

    code_retour = main(["apercu", str(fichier)])

    sortie = capsys.readouterr()
    assert code_retour == 1
    assert "Erreur : Format non géré" in sortie.err
    assert sortie.out == ""  # rien sur la sortie normale


def test_fichier_introuvable(tmp_path, capsys):
    code_retour = main(["apercu", str(tmp_path / "absent.pdf")])

    assert code_retour == 1
    assert "introuvable" in capsys.readouterr().err


def test_document_presque_vide(tmp_path, capsys):
    fichier = tmp_path / "vide.txt"
    fichier.write_text("Trop court.", encoding="utf-8")

    code_retour = main(["apercu", str(fichier)])

    assert code_retour == 1
    assert "OCR" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Les erreurs de saisie sont gérées par argparse
# ---------------------------------------------------------------------------


def test_aide(capsys):
    with pytest.raises(SystemExit) as info:
        main(["--help"])

    assert info.value.code == 0  # afficher l'aide n'est pas une erreur
    assert "apercu" in capsys.readouterr().out


def test_sans_commande(capsys):
    with pytest.raises(SystemExit) as info:
        main([])

    assert info.value.code == 2  # 2 = la commande a été mal tapée
    assert "usage" in capsys.readouterr().err