

class ErreurDecrypte(Exception):
    """Classe mère de toutes les erreurs du projet."""


class FormatNonGere(ErreurDecrypte):
    """Aucun lecteur ne sait lire ce type de fichier."""


class DocumentIllisible(ErreurDecrypte):
    """Le document a été ouvert, mais il ne contient presque pas de texte."""
    
    
class FichierIntrouvable(ErreurDecrypte):
    """Le fichier demandé n'existe pas (ou c'est un dossier)."""


class ExtractionImpossible(ErreurDecrypte):
    """Le modèle d'IA n'a pas pu extraire les propositions (panne réseau, quota, réponse illisible…)."""
    

class ProgrammeIntrouvable(ErreurDecrypte):
    """Aucun programme extrait n'a été enregistré pour ce candidat."""
    

class ReponsesInvalides(ErreurDecrypte):
    """Les réponses envoyées par l'utilisateur ne correspondent pas aux propositions connues."""