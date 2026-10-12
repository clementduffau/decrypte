
from pathlib import Path

from decrypte.domaine.erreurs import FichierIntrouvable


class FichiersLocaux:
    def lire_octets(self, chemin: Path) -> bytes:
        chemin = Path(chemin)  # accepte aussi un simple texte comme "data/brut/programme.pdf"

        # is_file() est faux si le chemin n'existe pas OU si c'est un dossier.
        if not chemin.is_file():
            raise FichierIntrouvable(f"Fichier introuvable : {chemin}")

        return chemin.read_bytes()