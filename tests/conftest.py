"""Outils partagés par tous les tests.

pytest lit ce fichier automatiquement. Une fonction marquée @pytest.fixture
peut être demandée par n'importe quel test : il suffit d'écrire son nom
dans les paramètres du test, et pytest l'appelle pour nous.
"""

import textwrap
from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from decrypte.domaine.modeles import Document, Page, SourceDocument

# Le programme fictif utilisé dans les tests (un élément de la liste = une page).
PAGES_PROGRAMME_FICTIF = [
    "Programme de Camille Exemple, Mouvement Fictif pour les Tests. "
    "Notre pays mérite mieux. Nous proposons de créer 500 nouvelles maisons de santé "
    "d'ici 2030 dans les communes de moins de 10 000 habitants. "
    "Nous ouvrirons les bibliothèques municipales le dimanche.",
    "Pour l'environnement, nous planterons 10 millions d'arbres en cinq ans. "
    "Nous instaurerons un service civique de trois mois, ouvert à tous les jeunes "
    "de 18 à 25 ans. Nous simplifierons la déclaration de revenus grâce à un formulaire unique.",
]


def ecrire_pdf(chemin: Path, pages: list[str]) -> Path:
    """Crée un PDF avec une page par texte de la liste (une page blanche si le texte est vide)."""
    pdf = canvas.Canvas(str(chemin), pagesize=A4)
    for texte in pages:
        y = 800  # on écrit en partant du haut de la page
        for ligne in textwrap.wrap(texte, width=85):  # coupe le texte en lignes de 85 caractères
            pdf.drawString(50, y, ligne)
            y -= 16
        pdf.showPage()  # termine la page en cours
    pdf.save()
    return chemin


def aplatir(texte: str) -> str:
    """Remplace les retours à la ligne et les espaces multiples par un seul espace.

    Un PDF coupe les phrases en lignes : sans cette fonction, « maisons de santé »
    pourrait être lu « maisons de\\nsanté » et un test échouerait pour rien.
    """
    return " ".join(texte.split())


def creer_document(*textes: str) -> Document:
    """Fabrique un Document en mémoire, avec une page par texte donné (sans passer par un fichier)."""
    source = SourceDocument(chemin="essai.txt", sha256="0" * 64, nb_pages=len(textes), type="texte")
    pages = [Page(numero=i, texte=texte) for i, texte in enumerate(textes, start=1)]
    return Document(source=source, pages=pages)


@pytest.fixture
def programme_pdf(tmp_path: Path) -> Path:
    """Le programme fictif, en PDF de 2 pages, dans un dossier temporaire."""
    return ecrire_pdf(tmp_path / "programme_fictif.pdf", PAGES_PROGRAMME_FICTIF)