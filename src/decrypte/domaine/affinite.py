from enum import Enum

from pydantic import BaseModel

from decrypte.domaine.erreurs import ReponsesInvalides
from decrypte.domaine.modeles import Proposition, Theme

REPONSES_MIN_FIABLE = 3


class Reponse(str, Enum):
    D_ACCORD = "d_accord"
    PAS_D_ACCORD = "pas_d_accord"
    SANS_AVIS = "sans_avis"


class DetailTheme(BaseModel):
    theme : Theme
    accords : int
    desaccords: int    
    
    
class AffiniteCandidat(BaseModel):
    candidat_id : str
    accords : list[str]
    desaccords : list[str]
    par_theme : list[DetailTheme]
    
    @property
    def nb_reponses(self) -> int:
        return len(self.accords) + len(self.desaccords)
    
    @property
    def score(self) -> float | None:
        return len(self.accords) / self.nb_reponses if self.nb_reponses else None
    
    @property
    def fiable(self) -> bool:
        return self.nb_reponses >= REPONSES_MIN_FIABLE
    
    

def calculer_affinites(propositions : list[Proposition], reponses : dict[str, Reponse]) -> list[AffiniteCandidat]:
    connues = {proposition.id for proposition in propositions}
    inconnues = sorted(set(reponses) - connues)
    if inconnues:
        raise ReponsesInvalides(f"Réponses à des propositions inconnues : {', '.join(inconnues)}")

    par_candidat: dict[str, list[Proposition]] = {}
    for proposition in propositions:
        par_candidat.setdefault(proposition.candidat_id, []).append(proposition)
        
    
    affinites = [
        _affinite_d_un_candidat(candidat_id, ses_propositions, reponses)
        for candidat_id, ses_propositions in par_candidat.items()
    ]
    
    return sorted(affinites, key = lambda a: (a.score is None,  -(a.score or 0), a.candidat_id))

def _affinite_d_un_candidat(
    candidat_id: str, propositions : list[Proposition], reponses : dict[str, Reponse]
    ) -> AffiniteCandidat:
    
    accords = [p for p in propositions if reponses.get(p.id)==Reponse.D_ACCORD]
    desaccords = [p for p in propositions if reponses.get(p.id)== Reponse.PAS_D_ACCORD]
    
    par_theme = []
    for theme in Theme:
        nb_accords = sum(p.theme == theme for p in accords)
        nb_desaccords = sum(p.theme == theme for p in desaccords)
        if nb_accords or nb_desaccords:
            par_theme.append(DetailTheme(theme= theme, accords=nb_accords, desaccords=nb_desaccords))
            
    return AffiniteCandidat(candidat_id=candidat_id, accords=[p.id for p in accords], desaccords=[p.id for p in desaccords], par_theme=par_theme)
    