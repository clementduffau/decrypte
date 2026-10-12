

from pathlib import Path
from typing import Protocol, runtime_checkable

from decrypte.domaine.modeles import Page, TypeDocument


@runtime_checkable
class SourceFichiers(Protocol):
    """Donne accès au contenu brut d'un fichier.

    Aujourd'hui : le disque local. Demain : un téléchargement, un stockage en ligne…
    """

    def lire_octets(self, chemin: Path) -> bytes:
        ...


@runtime_checkable
class LecteurDocument(Protocol):
    """Transforme le contenu brut d'un format de fichier en pages de texte."""

    type_document: TypeDocument   # "pdf", "html" ou "texte"
    extensions: tuple[str, ...]   # ex. (".pdf",)

    def lire(self, octets: bytes) -> list[Page]:
        ...