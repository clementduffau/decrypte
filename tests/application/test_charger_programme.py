"""Tests de l'application : le cas d'usage « charger un programme ».

C'est ici que l'architecture hexagonale montre son intérêt : on teste toute
la logique du cas d'usage avec de FAUX adaptateurs, écrits en quelques lignes.
Pas de vrai PDF, pas de disque : les tests sont rapides et ne testent que la
logique de l'application.

Le dernier test, lui, branche les VRAIS adaptateurs, pour vérifier que toutes
les pièces fonctionnent ensemble.
"""

from pathlib import Path

import pytest

from decrypte.adaptateurs.fichiers_locaux import FichiersLocaux
from decrypte.adaptateurs.lecteurs.html import LecteurHtml
from decrypte.adaptateurs.lecteurs.pdf import LecteurPdf
from decrypte.adaptateurs.lecteurs.texte import LecteurTexte
from decrypte.application.charger_programme import ChargerProgramme
from decrypte.domaine.empreinte import calculer_empreinte
from decrypte.domaine.erreurs import DocumentIllisible, FichierIntrouvable, FormatNonGere
from decrypte.domaine.modeles import Page
from decrypte.ports.lecture import LecteurDocument, SourceFichiers
from tests.conftest import aplatir

# Un texte assez long (plus de 200 caractères) pour ne pas être jugé « presque vide ».
TEXTE_LONG = "Nous proposons de créer 500 nouvelles maisons de santé d'ici 2030. " * 5


# ---------------------------------------------------------------------------
# Les faux adaptateurs
# ---------------------------------------------------------------------------


class FausseSource:
    """Faux disque : renvoie des octets gardés en mémoire et note les fichiers lus."""

    def __init__(self, fichiers: dict[str, bytes]) -> None:
        self.fichiers = fichiers
        self.lus: list[str] = []  # la liste des chemins qu'on nous a demandé de lire

    def lire_octets(self, chemin: Path) -> bytes:
        self.lus.append(str(chemin))
        if str(chemin) not in self.fichiers:
            # Même comportement que le vrai adaptateur FichiersLocaux
            raise FichierIntrouvable(f"Fichier introuvable : {chemin}")
        return self.fichiers[str(chemin)]


class FauxLecteur:
    """Faux lecteur : découpe le texte en pages au caractère « | »."""

    type_document = "texte"
    extensions = (".faux",)

    def lire(self, octets: bytes) -> list[Page]:
        morceaux = octets.decode().split("|")
        return [Page(numero=i, texte=m) for i, m in enumerate(morceaux, start=1)]


class AutreFauxLecteur:
    """Un deuxième faux lecteur, pour vérifier que le cas d'usage choisit le bon."""

    type_document = "html"
    extensions = (".autre",)

    def lire(self, octets: bytes) -> list[Page]:
        return [Page(numero=1, texte="LU PAR L'AUTRE LECTEUR " + octets.decode())]


def creer_cas_usage(fichiers: dict[str, bytes]) -> tuple[ChargerProgramme, FausseSource]:
    """Fabrique le cas d'usage avec les faux adaptateurs (et renvoie la fausse source pour l'inspecter)."""
    source = FausseSource(fichiers)
    return ChargerProgramme(source=source, lecteurs=[FauxLecteur()]), source


# ---------------------------------------------------------------------------
# Les faux respectent bien les contrats (sinon les tests ne prouveraient rien)
# ---------------------------------------------------------------------------


def test_les_faux_respectent_les_contrats():
    assert isinstance(FausseSource({}), SourceFichiers)
    assert isinstance(FauxLecteur(), LecteurDocument)
    assert isinstance(AutreFauxLecteur(), LecteurDocument)


# ---------------------------------------------------------------------------
# Le cas qui marche
# ---------------------------------------------------------------------------


def test_document_assemble():
    contenu = f"{TEXTE_LONG}|Page deux".encode()
    cas_usage, _ = creer_cas_usage({"programme.faux": contenu})

    document = cas_usage.executer("programme.faux", url="https://exemple.fr/programme")

    assert document.source.chemin == "programme.faux"
    assert document.source.nb_pages == 2
    assert document.source.type == "texte"
    assert document.source.sha256 == calculer_empreinte(contenu)
    assert document.source.url == "https://exemple.fr/programme"
    assert [page.numero for page in document.pages] == [1, 2]
    assert document.pages[1].texte == "Page deux"


def test_url_facultative():
    cas_usage, _ = creer_cas_usage({"programme.faux": TEXTE_LONG.encode()})
    assert cas_usage.executer("programme.faux").source.url is None


def test_texte_jamais_modifie():
    texte = "  Créer   500 maisons\nde santé  " + TEXTE_LONG
    cas_usage, _ = creer_cas_usage({"programme.faux": texte.encode()})

    document = cas_usage.executer("programme.faux")

    assert document.pages[0].texte == texte  # espaces et retours à la ligne conservés


def test_extension_en_majuscules_acceptee():
    cas_usage, _ = creer_cas_usage({"PROGRAMME.FAUX": TEXTE_LONG.encode()})
    assert cas_usage.executer("PROGRAMME.FAUX").source.nb_pages == 1


def test_choisit_le_lecteur_selon_l_extension():
    source = FausseSource({"a.faux": TEXTE_LONG.encode(), "b.autre": TEXTE_LONG.encode()})
    cas_usage = ChargerProgramme(source=source, lecteurs=[FauxLecteur(), AutreFauxLecteur()])

    assert cas_usage.executer("a.faux").source.type == "texte"
    document_b = cas_usage.executer("b.autre")
    assert document_b.source.type == "html"
    assert document_b.pages[0].texte.startswith("LU PAR L'AUTRE LECTEUR")


# ---------------------------------------------------------------------------
# Les cas d'erreur
# ---------------------------------------------------------------------------


def test_format_non_gere_sans_lire_le_fichier():
    cas_usage, source = creer_cas_usage({})

    with pytest.raises(FormatNonGere, match=r"\.docx"):
        cas_usage.executer("programme.docx")

    assert source.lus == []  # on refuse avant même d'ouvrir le fichier


def test_message_format_non_gere_liste_les_formats_acceptes():
    cas_usage, _ = creer_cas_usage({})
    with pytest.raises(FormatNonGere, match=r"formats acceptés : \.faux"):
        cas_usage.executer("programme.docx")


def test_fichier_introuvable_remonte_tel_quel():
    cas_usage, _ = creer_cas_usage({})  # la fausse source ne contient aucun fichier
    with pytest.raises(FichierIntrouvable):
        cas_usage.executer("absent.faux")


def test_document_presque_vide_refuse():
    cas_usage, _ = creer_cas_usage({"scanne.faux": b"|"})  # deux pages vides
    with pytest.raises(DocumentIllisible, match="OCR"):
        cas_usage.executer("scanne.faux")


def test_seuil_de_caracteres_reglable():
    source = FausseSource({"court.faux": b"Texte court"})  # 11 caractères
    cas_usage = ChargerProgramme(source=source, lecteurs=[FauxLecteur()], caracteres_min=5)

    assert cas_usage.executer("court.faux").pages[0].texte == "Texte court"


# ---------------------------------------------------------------------------
# Avec les VRAIS adaptateurs : toutes les pièces ensemble
# ---------------------------------------------------------------------------


def test_avec_les_vrais_adaptateurs(programme_pdf):
    cas_usage = ChargerProgramme(
        source=FichiersLocaux(),
        lecteurs=[LecteurPdf(), LecteurHtml(), LecteurTexte()],
    )

    document = cas_usage.executer(programme_pdf)

    assert document.source.type == "pdf"
    assert document.source.nb_pages == 2
    assert document.source.sha256 == calculer_empreinte(programme_pdf.read_bytes())
    assert "maisons de santé" in aplatir(document.pages[0].texte)
    assert "service civique" in aplatir(document.pages[1].texte)