"""Tests du point d'entrée : la ligne de commande, branchée sur les vrais adaptateurs.

Ces tests traversent tout l'hexagone : commande → assemblage → cas d'usage
→ lecteur → disque. On appelle main() avec une liste d'arguments, exactement
comme si on les avait tapés dans le terminal.

Pour la commande « extraire », Mistral est TOUJOURS remplacé par un faux
extracteur (fixture sans_mistral) : les tests ne font aucun appel réseau.

capsys est fourni par pytest : il capture ce que le programme affiche,
séparément pour la sortie normale (out) et la sortie d'erreur (err).
"""

import json

import pytest

from decrypte.application.extraire_programme import ExtraireProgramme
from decrypte.assemblage import creer_extraire_programme
from decrypte.domaine.empreinte import calculer_empreinte
from decrypte.domaine.modeles import PropositionExtraite, Theme
from decrypte.points_entree import cli
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


# ---------------------------------------------------------------------------
# Commande « extraire » (sans jamais appeler Mistral)
# ---------------------------------------------------------------------------


class FauxExtracteur:
    """Remplace Mistral : renvoie une proposition présente dans le programme et une inventée."""

    nom_modele = "faux-modele"

    def extraire(self, texte: str) -> list[PropositionExtraite]:
        return [
            PropositionExtraite(
                citation="Nous proposons de créer 500 nouvelles maisons de santé d'ici 2030",
                resume_neutre="Créer 500 maisons de santé d'ici 2030",
                theme=Theme.SANTE,
            ),
            PropositionExtraite(
                citation="Nous supprimerons l'impôt sur le revenu pour tous les Français",
                resume_neutre="Supprimer l'impôt sur le revenu",
                theme=Theme.FISCALITE,
            ),
        ]


@pytest.fixture
def sans_mistral(monkeypatch):
    """Le temps d'un test, la ligne de commande utilise le faux extracteur au lieu de Mistral."""
    monkeypatch.setattr(cli, "creer_extraire_programme", lambda: ExtraireProgramme(FauxExtracteur()))


def lancer_extraire(fichier, sortie, *options: str) -> int:
    """Lance « decrypte extraire » sur un fichier, avec le résultat rangé dans le dossier « sortie »."""
    arguments = ["extraire", str(fichier), "--candidat-id", "camille-exemple", "--nom", "Camille Exemple"]
    return main([*arguments, "--sortie", str(sortie), *options])


def test_extraire_enregistre_le_resultat(programme_pdf, tmp_path, sans_mistral):
    code_retour = lancer_extraire(programme_pdf, tmp_path / "extraits")

    fichier = tmp_path / "extraits" / "camille-exemple.json"
    resultat = json.loads(fichier.read_text(encoding="utf-8"))
    assert code_retour == 0
    assert resultat["candidat"]["nom"] == "Camille Exemple"
    assert resultat["modele_llm"] == "faux-modele"
    assert len(resultat["propositions"]) == 1  # la proposition présente dans le programme
    assert len(resultat["rejetees"]) == 1      # la proposition inventée


def test_extraire_affiche_la_progression_et_le_bilan(programme_pdf, tmp_path, sans_mistral, capsys):
    lancer_extraire(programme_pdf, tmp_path)

    sortie = aplatir(capsys.readouterr().out)
    assert "Programme lu : 2 pages" in sortie
    assert "Morceau 1/1 (pages 1 à 2)" in sortie
    assert "Propositions gardées : 1 (1 exacte(s), 0 approchante(s) à vérifier)" in sortie
    assert "Propositions rejetées : 1 (1 introuvable(s), 0 doublon(s))" in sortie
    assert "camille-exemple.json" in sortie


def test_extraire_options_facultatives(programme_pdf, tmp_path, sans_mistral):
    lancer_extraire(
        programme_pdf,
        tmp_path,
        "--parti", "Mouvement Fictif",
        "--election", "presidentielle-2022",
        "--url", "https://exemple.fr/programme.pdf",
    )

    resultat = json.loads((tmp_path / "camille-exemple.json").read_text(encoding="utf-8"))
    assert resultat["candidat"]["parti"] == "Mouvement Fictif"
    assert resultat["candidat"]["election"] == "presidentielle-2022"
    assert resultat["source"]["url"] == "https://exemple.fr/programme.pdf"


def test_extraire_identifiant_invalide(programme_pdf, tmp_path, sans_mistral, capsys):
    with pytest.raises(SystemExit) as info:
        main(["extraire", str(programme_pdf), "--candidat-id", "Camille Exemple", "--nom", "Camille Exemple"])

    assert info.value.code == 2
    assert "identifiant invalide" in capsys.readouterr().err


def test_extraire_cle_manquante(programme_pdf, tmp_path, monkeypatch, capsys):
    # Le vrai assemblage, mais avec des variables d'environnement vides : comme un .env oublié.
    monkeypatch.setattr(cli, "creer_extraire_programme", lambda: creer_extraire_programme(environ={}))

    code_retour = lancer_extraire(programme_pdf, tmp_path / "extraits")

    assert code_retour == 1
    assert "MISTRAL_API_KEY" in capsys.readouterr().err
    assert not (tmp_path / "extraits").exists()  # rien n'a été enregistré


def test_extraire_fichier_introuvable(tmp_path, sans_mistral, capsys):
    code_retour = lancer_extraire(tmp_path / "absent.pdf", tmp_path)

    assert code_retour == 1
    assert "introuvable" in capsys.readouterr().err