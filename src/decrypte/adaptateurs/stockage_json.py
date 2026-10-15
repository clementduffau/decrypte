import re
from pathlib import Path

from decrypte.domaine.modeles import ProgrammeExtrait
from decrypte.domaine.erreurs import ProgrammeIntrouvable


IDENTIFIANT_VALIDE = re.compile(r"[a-z0-9-]+")


class StockageJson:
    def __init__(self, dossier : str | Path) -> None:
        self._dossier = Path(dossier)
        
    def enregistrer(self, programme : ProgrammeExtrait) -> str:
        self._dossier.mkdir(parents = True, exist_ok=True)
        chemin = self._chemin(programme.candidat.id)
        
        temporaire = chemin.with_name(chemin.name + ".tmp")
        temporaire.write_text(programme.model_dump_json(indent=2), encoding = "utf-8")
        temporaire.replace(chemin)
        return str(chemin)
    
    def charger(self, candidat_id : str) -> ProgrammeExtrait:
        chemin = self._chemin(candidat_id)
        if not chemin.is_file():
            raise ProgrammeIntrouvable(f"Aucun programme extrait pour « {candidat_id} » ({chemin} n'existe pas).")
        return ProgrammeExtrait.model_validate_json(chemin.read_text(encoding="utf-8"))
    
    def lister_candidats(self) -> list[str]:
        if not self._dossier.is_dir():
            return []
        return sorted(f.stem for f in self._dossier.glob("*.json") if IDENTIFIANT_VALIDE.fullmatch(f.stem))
    
    def _chemin(self, candidat_id = str) -> Path:
        if not IDENTIFIANT_VALIDE.fullmatch(candidat_id):
            raise ProgrammeIntrouvable(f"Identifiant de candidat invalide : {candidat_id!r}")
        return self._dossier / f"{candidat_id}.json"
        
        