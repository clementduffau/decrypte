from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from decrypte.application.questionnaire import Carte, ResultatCandidat
from decrypte.assemblage import DOSSIER_EXTRAITS, creer_calculer_resultats, creer_construire_questionnaire
from decrypte.domaine.affinite import Reponse
from decrypte.domaine.erreurs import ReponsesInvalides


CARTES_PAR_CANDIDAT = 5


class DemandeResultats(BaseModel):
    reponses : dict[str,Reponse]
    
    
def creer_application(
    dossier : str | Path = DOSSIER_EXTRAITS,
    par_candidat : int | None = CARTES_PAR_CANDIDAT,
) -> FastAPI:
    application = FastAPI(
        title = "Décrypte 2027",
        description="comparer ses idées aux propositions des candidats à l'éléction présidentielle de 2027"
    )

    @application.get("/api/cartes", response_model = list[Carte])
    def cartes() -> list[Carte]:
        return creer_construire_questionnaire(dossier, par_candidat).executer()
    
    @application.post("/api/resultats", response_model = list[ResultatCandidat])
    def resultats(demande : DemandeResultats) -> list[ResultatCandidat]:
        try :
            return creer_calculer_resultats(dossier).executer(demande.reponses)
        except ReponsesInvalides as erreur:
            raise HTTPException(status_code=442,detail=str(erreur)) from erreur

    return application


def main() -> None:
    uvicorn.run(creer_application(), host = "127.0.0.1", port = 8000)

