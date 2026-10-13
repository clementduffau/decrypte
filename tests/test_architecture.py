

import ast
import sys
from pathlib import Path

# Le dossier src/decrypte, retrouvé à partir de l'emplacement de ce fichier de test.
SOURCES = Path(__file__).resolve().parents[1] / "src" / "decrypte"

# Pour chaque couche : les couches du projet qu'elle a le droit d'importer.
COUCHES_AUTORISEES = {
    "domaine": {"domaine"},
    "ports": {"domaine", "ports"},
    "application": {"domaine", "ports", "application"},
    "adaptateurs": {"domaine", "ports", "adaptateurs"},
    "points_entree": {"domaine", "application", "assemblage", "points_entree"},
}

# Le cœur de l'hexagone n'a droit qu'à la bibliothèque standard et à ces bibliothèques-là.
COEUR = {"domaine", "ports", "application"}
BIBLIOTHEQUES_AUTORISEES_AU_COEUR = {"pydantic"}


# ---------------------------------------------------------------------------
# Les outils du garde-fou
# ---------------------------------------------------------------------------


def imports_du_fichier(fichier: Path) -> list[tuple[int, str]]:
    """Renvoie (numéro de ligne, module importé) pour chaque import du fichier, sans l'exécuter."""
    arbre = ast.parse(fichier.read_text(encoding="utf-8"))
    imports = []
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Import):  # import pypdf
            for alias in noeud.names:
                imports.append((noeud.lineno, alias.name))
        elif isinstance(noeud, ast.ImportFrom):  # from pypdf import PdfReader
            # level compte les points d'un import relatif : « from . import x » a level = 1
            imports.append((noeud.lineno, "." * noeud.level + (noeud.module or "")))
    return imports


def problemes_du_fichier(fichier: Path, couche: str) -> list[str]:
    """Liste les imports du fichier qui cassent les règles de sa couche."""
    problemes = []
    for ligne, module in imports_du_fichier(fichier):
        racine = module.split(".")[0]  # "decrypte.domaine.modeles" → "decrypte"

        if module.startswith("."):
            problemes.append(f"ligne {ligne} : import relatif « {module} », écris l'import complet (decrypte.…)")

        elif racine == "decrypte":
            couche_importee = module.split(".")[1] if "." in module else module
            if couche_importee not in COUCHES_AUTORISEES[couche]:
                problemes.append(f"ligne {ligne} : importe {module}, or {couche} n'a pas le droit de dépendre de {couche_importee}")

        elif couche in COEUR:
            if racine not in sys.stdlib_module_names and racine not in BIBLIOTHEQUES_AUTORISEES_AU_COEUR:
                problemes.append(f"ligne {ligne} : importe la bibliothèque {racine}, à utiliser seulement dans un adaptateur")

    return problemes


def problemes_de_la_couche(couche: str) -> list[str]:
    """Vérifie tous les fichiers .py d'une couche (sous-dossiers compris)."""
    problemes = []
    for fichier in sorted((SOURCES / couche).rglob("*.py")):
        chemin = fichier.relative_to(SOURCES)
        problemes += [f"{chemin}, {probleme}" for probleme in problemes_du_fichier(fichier, couche)]
    return problemes


# ---------------------------------------------------------------------------
# Les règles appliquées au vrai projet
# ---------------------------------------------------------------------------


def test_toutes_les_couches_ont_des_regles():
    # Si tu crées un nouveau dossier dans src/decrypte, ce test t'oblige à décider de ses règles.
    dossiers = {d.name for d in SOURCES.iterdir() if (d / "__init__.py").exists()}
    assert dossiers == set(COUCHES_AUTORISEES)


def test_domaine_ne_depend_de_rien():
    problemes = problemes_de_la_couche("domaine")
    assert not problemes, "\n".join(problemes)


def test_ports_ne_dependent_que_du_domaine():
    problemes = problemes_de_la_couche("ports")
    assert not problemes, "\n".join(problemes)


def test_application_ne_connait_pas_les_adaptateurs():
    problemes = problemes_de_la_couche("application")
    assert not problemes, "\n".join(problemes)


def test_adaptateurs_ne_connaissent_pas_l_application():
    problemes = problemes_de_la_couche("adaptateurs")
    assert not problemes, "\n".join(problemes)


def test_points_entree_passent_par_l_assemblage():
    problemes = problemes_de_la_couche("points_entree")
    assert not problemes, "\n".join(problemes)


# ---------------------------------------------------------------------------
# On vérifie aussi que le garde-fou lui-même fonctionne
# ---------------------------------------------------------------------------


def test_garde_fou_repere_les_imports_interdits(tmp_path):
    fichier = tmp_path / "mauvais.py"
    fichier.write_text(
        "import pypdf\n"
        "from decrypte.adaptateurs.lecteurs.pdf import LecteurPdf\n"
        "from . import modeles\n",
        encoding="utf-8",
    )

    problemes = problemes_du_fichier(fichier, "domaine")

    assert len(problemes) == 3
    assert "bibliothèque pypdf" in problemes[0]
    assert "adaptateurs" in problemes[1]
    assert "import relatif" in problemes[2]


def test_garde_fou_accepte_un_fichier_correct(tmp_path):
    fichier = tmp_path / "correct.py"
    fichier.write_text(
        "import hashlib\n"
        "from pathlib import Path\n"
        "from pydantic import BaseModel\n"
        "from decrypte.domaine.modeles import Page\n",
        encoding="utf-8",
    )

    assert problemes_du_fichier(fichier, "domaine") == []


def test_adaptateurs_ont_droit_aux_bibliotheques(tmp_path):
    fichier = tmp_path / "adaptateur.py"
    fichier.write_text("import pypdf\nfrom bs4 import BeautifulSoup\n", encoding="utf-8")

    assert problemes_du_fichier(fichier, "adaptateurs") == []