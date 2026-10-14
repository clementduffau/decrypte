

import os
from collections.abc import Mapping
from pathlib import Path

from decrypte.adaptateurs.fichiers_locaux import FichiersLocaux
from decrypte.adaptateurs.ia.mistral import MODELE_PAR_DEFAUT, ExtracteurMistral
from decrypte.adaptateurs.lecteurs.html import LecteurHtml
from decrypte.adaptateurs.lecteurs.pdf import LecteurPdf
from decrypte.adaptateurs.lecteurs.texte import LecteurTexte
from decrypte.adaptateurs.stockage_json import StockageJson
from decrypte.application.charger_programme import ChargerProgramme
from decrypte.application.extraire_programme import ExtraireProgramme

DOSSIER_EXTRAITS = Path("data/extraits")


def creer_charger_programme() -> ChargerProgramme:
    """Renvoie le cas d'usage « charger un programme », branché sur le disque et les 3 lecteurs."""
    return ChargerProgramme(
        source=FichiersLocaux(),
        lecteurs=[LecteurPdf(), LecteurHtml(), LecteurTexte()],
    )


def creer_extraire_programme(environ: Mapping[str, str] = os.environ) -> ExtraireProgramme:
    """Renvoie le cas d'usage « extraire les propositions », branché sur Mistral.

    La clé et le modèle sont lus dans les variables d'environnement (remplies par le fichier .env).
    """
    extracteur = ExtracteurMistral(
        cle_api=environ.get("MISTRAL_API_KEY", ""),
        nom_modele=environ.get("MISTRAL_MODELE", MODELE_PAR_DEFAUT),
    )
    return ExtraireProgramme(extracteur)


def creer_stockage(dossier: str | Path = DOSSIER_EXTRAITS) -> StockageJson:
    """Renvoie le stockage des programmes extraits, en fichiers JSON."""
    return StockageJson(dossier)