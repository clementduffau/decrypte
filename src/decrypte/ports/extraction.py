


from typing import Protocol, runtime_checkable

from decrypte.domaine.modeles import PropositionExtraite


@runtime_checkable
class ExtracteurPropositions(Protocol):
 
    nom_modele: str  # ex. "mistral-small-latest" : enregistré avec les résultats

    def extraire(self, texte: str) -> list[PropositionExtraite]:
        ...