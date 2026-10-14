

import json
import logging
import time
from collections.abc import Callable

import httpx
from pydantic import ValidationError

from decrypte.adaptateurs.ia.consignes import CONSIGNES_SYSTEME, message_utilisateur
from decrypte.domaine.erreurs import ExtractionImpossible
from decrypte.domaine.modeles import PropositionExtraite

URL_MISTRAL = "https://api.mistral.ai/v1/chat/completions"
MODELE_PAR_DEFAUT = "ministral-14b-2512"
TENTATIVES_MAX = 4
ATTENTE_INITIALE = 5.0  # secondes ; l'attente double à chaque nouvel essai : 5, 10, 20…

journal = logging.getLogger(__name__)


class ExtracteurMistral:
    def __init__(
        self,
        cle_api: str,
        nom_modele: str = MODELE_PAR_DEFAUT,
        client: httpx.Client | None = None,
        attendre: Callable[[float], None] = time.sleep,
        tentatives_max: int = TENTATIVES_MAX,
    ) -> None:
        if not cle_api:
            raise ExtractionImpossible("Clé d'API Mistral manquante : ajoute MISTRAL_API_KEY dans le fichier .env.")
        self.nom_modele = nom_modele
        self._cle_api = cle_api
        self._client = client or httpx.Client(timeout=120)  # un morceau peut prendre du temps à analyser
        self._attendre = attendre
        self._tentatives_max = tentatives_max

    def extraire(self, texte: str) -> list[PropositionExtraite]:
        reponse = self._appeler_mistral(texte)
        return self._lire_propositions(reponse)

 
    def _appeler_mistral(self, texte: str) -> httpx.Response:
        corps = {
            "model": self.nom_modele,
            "messages": [
                {"role": "system", "content": CONSIGNES_SYSTEME},
                {"role": "user", "content": message_utilisateur(texte)},
            ],
            "response_format": {"type": "json_object"}, 
            "temperature": 0,  
        }
        en_tetes = {"Authorization": f"Bearer {self._cle_api}"}
        attente = ATTENTE_INITIALE

        for tentative in range(1, self._tentatives_max + 1):
            try:
                reponse = self._client.post(URL_MISTRAL, json=corps, headers=en_tetes)
            except httpx.TransportError as erreur:  # réseau coupé, délai dépassé…
                probleme = f"connexion impossible ({type(erreur).__name__})"
            else:
                if reponse.status_code == 200:
                    return reponse
                self._arreter_si_definitif(reponse)  
                probleme = f"code HTTP {reponse.status_code}"

            if tentative < self._tentatives_max:
                journal.warning(
                    "Mistral : %s, nouvel essai dans %.0f s (tentative %d sur %d)",
                    probleme, attente, tentative, self._tentatives_max,
                )
                self._attendre(attente)
                attente *= 2

        raise ExtractionImpossible(
            f"Mistral ne répond pas correctement ({probleme}) après {self._tentatives_max} tentatives. "
            "Réessaie dans quelques minutes."
        )

    def _arreter_si_definitif(self, reponse: httpx.Response) -> None:
        """Lève ExtractionImpossible si l'erreur ne disparaîtra pas en réessayant."""
        code = reponse.status_code
        if code == 401:
            raise ExtractionImpossible("Clé d'API refusée par Mistral (401) : vérifie MISTRAL_API_KEY dans le fichier .env.")
        if code == 429 and reponse.headers.get("x-ratelimit-limit-req-minute") == "0":
            raise ExtractionImpossible(
                f"Le modèle « {self.nom_modele} » a une limite de 0 requête par minute sur ton compte : "
                "choisis un autre modèle dans MISTRAL_MODELE."
            )
        if code != 429 and code < 500:
            raise ExtractionImpossible(f"Requête refusée par Mistral (code {code}) : {reponse.text[:200]}")
        # Sinon (429 temporaire, ou erreur 5xx du serveur) : on pourra réessayer.



    def _lire_propositions(self, reponse: httpx.Response) -> list[PropositionExtraite]:
        try:
            choix = reponse.json()["choices"][0]
            if choix.get("finish_reason") == "length":
                raise ExtractionImpossible(
                    "La réponse de Mistral a été coupée car trop longue : diminue la taille des morceaux."
                )
            elements = json.loads(choix["message"]["content"])["propositions"]
        except (ValueError, KeyError, IndexError, TypeError) as erreur:
            raise ExtractionImpossible("Réponse de Mistral illisible : le JSON attendu est absent ou mal formé.") from erreur

        if not isinstance(elements, list):
            raise ExtractionImpossible("Réponse de Mistral illisible : « propositions » n'est pas une liste.")

        propositions = []
        for element in elements:
            try:
                propositions.append(PropositionExtraite.model_validate(element))
            except ValidationError as erreur:
                journal.warning("Proposition ignorée car mal formée : %s", erreur.errors()[0]["msg"])
        return propositions