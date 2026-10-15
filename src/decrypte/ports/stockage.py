from typing import Protocol, runtime_checkable

from decrypte.domaine.modeles import ProgrammeExtrait


@runtime_checkable
class StockageProgrammes(Protocol):
    def enregistrer(self, programme: ProgrammeExtrait) -> None:
        """Enregistre un programme"""
        ...
        
    def charger(self, candidat_id: str) -> ProgrammeExtrait:
        """ Charger un programme a partir de son identifiant"""
        ...
        
    def lister_candidats(self) -> list[str]:
        """Les identifiants des candidats dont un programme est enregistré, par ordre alphabétique."""
        ...