from datetime import datetime
from enum import Enum
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, field_validator

MOTS_MAX_RESUME = 25

TypeDocument = Literal["pdf", "html", "texte"]

class Theme(str, Enum):
    """ les themes autorisés, le llm ne peut pas en inventer d'autres"""
    ECONOMIE = "economie"
    TRAVAIL = "travail"
    FISCALITE = "fiscalite"
    SANTE = "sante"
    EDUCATION = "education"
    ENVIRONNEMENT_ENERGIE = "environnement_energie"
    SECURITE_JUSTICE = "securite_justice"
    IMMIGRATION = "immigration"
    INSTITUTIONS = "institutions"
    EUROPE_INTERNATIONAL = "europe_international"
    DEFENSE = "defense"
    SOCIAL_LOGEMENT = "social_logement"
    CULTURE_NUMERIQUE = "culture_numerique"
    AGRICULTURE_TERRITOIRES = "agriculture_territoires"
    AUTRE = "autre"
    
    
class StatutCitation(str, Enum):
    """resultats de la verification de la citation"""
    
    EXACTE = "exacte"
    APPROCHANTE = "approchante"
    INTROUVABLE = "introuvable"
    
    
class StatutRevue(str, Enum):
    """ou en est la validation humaine d'une proposition"""
    A_VALIDER ="a_valider"
    VALIDEE = "validee"
    REJETEE = "rejetee"
    
    
class Candidat(BaseModel):
    id : str = Field(pattern=r"^[a-z0-9-]+$")
    nom: str = Field(min_length=2)
    parti: str | None = None
    election: str  # ex. "presidentielle-2022"
    
    
class SourceDocument(BaseModel):
    chemin: str
    url: str | None = None
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")  # empreinte : 64 caractères hexadécimaux
    recupere_le: datetime | None = None
    nb_pages: int = Field(ge=1)
    type: TypeDocument  # ← NOUVEAU (avant : Literal["pdf", "html", "texte"])
    
    
class Page(BaseModel):
    numero: int = Field(ge=1)  # les pages commencent à 1, comme dans un vrai document
    texte: str
    
    
class Document(BaseModel):
    """Un programme lu : sa carte d'identité et le texte de chaque page."""

    source: SourceDocument
    pages: list[Page]
    
    
    
    
class PropositionExtraite(BaseModel):
    """Ce que le LLM doit renvoyer pour chaque proposition (étape 4)."""

    citation: str = Field(min_length=25)      # passage exact du programme
    resume_neutre: str = Field(min_length=5)  # texte affiché sur la carte
    theme: Theme
    chiffres: list[str] = Field(default_factory=list)  # montants, dates… cités dans le passage

    @field_validator("resume_neutre")
    @classmethod
    def resume_pas_trop_long(cls, v: str) -> str:
        nb_mots = len(v.split())
        if nb_mots > MOTS_MAX_RESUME:
            raise ValueError(f"résumé trop long : {nb_mots} mots (maximum {MOTS_MAX_RESUME})")
        return v.strip()
    
    
class Verification(BaseModel):
    statut : StatutCitation
    score : float = Field(ge=0, le=1)
    page : int | None = None
    extrait_source: str |None = None
    
    
    
class Proposition(PropositionExtraite):
    id : str
    candidat_id : str
    verification : Verification
    alertes: list[str] = Field(default_factory=list)  # ex. « mot de jugement dans le résumé »
    revue: StatutRevue = StatutRevue.A_VALIDER

    
class PropositionRejetee(BaseModel):
    citation : str
    resume_neutre : str
    raison : str
    
    
class ProgrammeExtrait(BaseModel):
    candidat : Candidat
    source : SourceDocument
    extrait_le : datetime
    modele_llm : str
    propositions : list[Proposition] = Field(default_factory = list)
    rejetees : list[PropositionRejetee] = Field(default_factory = list)