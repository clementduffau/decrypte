

from pathlib import Path

from decrypte.domaine.empreinte import calculer_empreinte
from decrypte.domaine.erreurs import DocumentIllisible, FormatNonGere
from decrypte.domaine.modeles import Document, SourceDocument
from decrypte.ports.lecture import LecteurDocument, SourceFichiers

CARACTERES_MIN = 200


class ChargerProgramme:
    def __init__(
        self,
        source: SourceFichiers,
        lecteurs: list[LecteurDocument],
        caracteres_min: int = CARACTERES_MIN,
    ) -> None:
        self._source = source
        self._lecteurs = {ext: lecteur for lecteur in lecteurs for ext in lecteur.extensions}
        self._caracteres_min = caracteres_min

    def executer(self, chemin: str | Path, url: str | None = None) -> Document:
        chemin = Path(chemin)

        extension = chemin.suffix.lower()
        lecteur = self._lecteurs.get(extension)
        if lecteur is None:
            formats = ", ".join(sorted(self._lecteurs))
            raise FormatNonGere(f"Format non géré : {extension} (formats acceptés : {formats})")

        octets = self._source.lire_octets(chemin)

        pages = lecteur.lire(octets)

        total = sum(len(page.texte) for page in pages)
        if total < self._caracteres_min:
            raise DocumentIllisible(
                f"Presque aucun texte lu dans {chemin.name} ({total} caractères). "
                "Si c'est un PDF scanné, il faudra un OCR."
            )

        source = SourceDocument(
            chemin=str(chemin),
            url=url,
            sha256=calculer_empreinte(octets),
            recupere_le=None,
            nb_pages=len(pages),
            type=lecteur.type_document,
        )
        return Document(source=source, pages=pages)