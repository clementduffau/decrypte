from decrypte.adaptateurs.fichiers_locaux import FichiersLocaux
from decrypte.adaptateurs.lecteurs.html import LecteurHtml
from decrypte.adaptateurs.lecteurs.pdf import LecteurPdf
from decrypte.adaptateurs.lecteurs.texte import LecteurTexte
from decrypte.application.charger_programme import ChargerProgramme


def creer_charger_programme() -> ChargerProgramme:
    return ChargerProgramme(
        source = FichiersLocaux(),
        lecteurs = [
            LecteurPdf(), LecteurHtml(), LecteurTexte()
        ]
    )