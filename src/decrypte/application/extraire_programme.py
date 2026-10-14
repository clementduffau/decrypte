

from collections.abc import Callable
from datetime import datetime, timezone

from decrypte.domaine.decoupage import TAILLE_MAX, decouper
from decrypte.domaine.modeles import (
    Candidat,
    Document,
    ProgrammeExtrait,
    Proposition,
    PropositionRejetee,
    StatutCitation,
)
from decrypte.domaine.verification import VerificateurCitations
from decrypte.ports.extraction import ExtracteurPropositions

ALERTE_APPROCHANTE = "citation approchante : à comparer avec l'extrait du programme avant publication"


def maintenant() -> datetime:
    """L'heure actuelle, en temps universel (UTC)."""
    return datetime.now(timezone.utc)


class ExtraireProgramme:
    def __init__(
        self,
        extracteur: ExtracteurPropositions,
        horloge: Callable[[], datetime] = maintenant,
        taille_morceau: int = TAILLE_MAX,
    ) -> None:
        self._extracteur = extracteur
        self._horloge = horloge
        self._taille_morceau = taille_morceau

    def executer(self, document: Document, candidat: Candidat) -> ProgrammeExtrait:
        verificateur = VerificateurCitations(document)  # le document est préparé une seule fois
        propositions: list[Proposition] = []
        rejetees: list[PropositionRejetee] = []
        passages_deja_vus: set[tuple] = set()  # les (page, extrait) déjà utilisés

        for morceau in decouper(document, self._taille_morceau):
            for extraite in self._extracteur.extraire(morceau.texte):
                verification = verificateur.verifier(extraite.citation)

                if verification.statut == StatutCitation.INTROUVABLE:
                    rejetees.append(
                        PropositionRejetee(
                            citation=extraite.citation,
                            resume_neutre=extraite.resume_neutre,
                            raison=f"citation introuvable dans le programme (ressemblance {verification.score:.2f})",
                        )
                    )
                    continue

                passage = (verification.page, verification.extrait_source)
                if passage in passages_deja_vus:
                    rejetees.append(
                        PropositionRejetee(
                            citation=extraite.citation,
                            resume_neutre=extraite.resume_neutre,
                            raison="doublon : ce passage du programme a déjà donné une proposition",
                        )
                    )
                    continue
                passages_deja_vus.add(passage)

                alertes = []
                if verification.statut == StatutCitation.APPROCHANTE:
                    alertes.append(ALERTE_APPROCHANTE)

                propositions.append(
                    Proposition(
                        **extraite.model_dump(),  # citation, resume_neutre, theme, chiffres
                        id=f"{candidat.id}-{len(propositions) + 1:03d}", 
                        candidat_id=candidat.id,
                        verification=verification,
                        alertes=alertes,
                    )
                )

        return ProgrammeExtrait(
            candidat=candidat,
            source=document.source,
            extrait_le=self._horloge(),
            modele_llm=self._extracteur.nom_modele,
            propositions=propositions,
            rejetees=rejetees,
        )