import hashlib
import random

from pydantic import BaseModel

from decrypte.domaine.affinite import DetailTheme, Reponse, calculer_affinites
from decrypte.domaine.erreurs import ReponsesInvalides
from decrypte.domaine.modeles import Candidat, ProgrammeExtrait, Proposition, StatutCitation, StatutRevue, Theme
from decrypte.ports.stockage import StockageProgrammes


class Carte(BaseModel):
    id : str
    resume : str
    theme : Theme
    citation : str
    page : int | None
    
    
class ResultatCandidat(BaseModel):
    candidat : Candidat
    score : float | None
    fiable : bool
    accords : list[Carte]
    desaccords : list[Carte]
    par_theme : list[DetailTheme]
    
    
def est_publiable(proposition : Proposition)-> bool:
    if proposition.revue == StatutRevue.REJETEE:
        return False
    return proposition.revue == StatutRevue.VALIDEE or proposition.verification.statut == StatutCitation.EXACTE


def identifiant_anonyme(proposition : Proposition)-> str:
    return hashlib.sha256(proposition.id.encode("utf-8")).hexdigest()[:12]


def vers_carte(proposition : Proposition)->Carte:
    return Carte(
        id = identifiant_anonyme(proposition),
        resume = proposition.resume_neutre,
        theme = proposition.theme,
        citation = proposition.citation,
        page = proposition.verification.page,
    )
    
    
def charger_programmes(stockage : StockageProgrammes)->list[ProgrammeExtrait]:
    return [stockage.charger(candidat_id) for candidat_id in stockage.lister_candidats()]


class ConstruireQuestionnaire:
    def __init__(
        self,
        stockage : StockageProgrammes,
        aleatoire : random.Random | None = None,
        par_candidat : int | None = None
    ) -> None:
        self._stockage = stockage
        self._aleatoire = aleatoire or random.Random()
        self._par_candidat = par_candidat
        
    def executer(self) -> list[Carte]:
        cartes : list[Carte] = []
        for programme in charger_programmes(self._stockage):
            publiables = [p for p in programme.propositions if est_publiable(p)]
            if self._par_candidat is not None and len(publiables) > self._par_candidat:
                publiables = self._aleatoire.sample(publiables, self._par_candidat)
                
            cartes += [vers_carte(p) for p in publiables]
            
        self._aleatoire.shuffle(cartes)
        return cartes
    
    
    
class CalculerResultats:
    def __init__(self, stockage : StockageProgrammes) -> None:
        self._stockage = stockage
        
    def executer(self, reponses : dict[str, Reponse]) -> list[ResultatCandidat]:
        programmes = charger_programmes(self._stockage) 
        propositions = [p for programme in programmes for p in programme.propositions if est_publiable(p)]
        
        par_carte = {identifiant_anonyme(p) : p for p in propositions}
        inconnues = sorted(set(reponses) - set(par_carte))
        if inconnues:
            raise ReponsesInvalides(f"Réponses à des cartes inconnues : {', '.join(inconnues)}")
        
        reponses_par_proposition = {par_carte[carte].id : reponse for carte, reponse in reponses.items()}
        
        affinites = calculer_affinites(propositions, reponses_par_proposition)
        
        candidats = {programme.candidat.id : programme.candidat for programme in programmes}
        par_id = {p.id : p for p in propositions}
        
        return [
            ResultatCandidat(
                candidat = candidats[affinite.candidat_id],
                score = affinite.score,
                fiable = affinite.fiable,
                accords = [vers_carte(par_id[i]) for i in affinite.accords],
                desaccords = [vers_carte(par_id[i]) for i in affinite.desaccords],
                par_theme = affinite.par_theme,
            ) 
            for affinite in affinites
        ]
        
        
    