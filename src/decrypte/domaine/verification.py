import re
import unicodedata
from difflib import SequenceMatcher
from typing import NamedTuple


from decrypte.domaine.modeles import Document, StatutCitation, Verification


SEUIL_APPROCHANTE = 0.85


class Mot(NamedTuple):
    forme : str
    page : int
    debut : int
    fin : int
    
    
def simplifier(mot: str) -> str:
    return unicodedata.normalize("NFKC", mot).casefold()


def decouper_en_mots(texte: str, page : int = 0) -> list[Mot]:
    texte = unicodedata.normalize("NFC", texte)
    return [
        Mot(simplifier(trouve.group()), page, trouve.start(), trouve.end())
        for trouve in re.finditer(r"\w+", texte)
    ]
    

class VerificateurCitations:
    
    def __init__(self, document : Document, seuil : float = SEUIL_APPROCHANTE) -> None:
        
        self._seuil = seuil
        self._textes = {page.numero: unicodedata.normalize("NFC", page.texte) for page in document.pages}
        self._mots = [mot for numero, texte in self._textes.items() for mot in decouper_en_mots(texte, numero)]
        self._formes = [mot.forme for mot in self._mots]
        self._chaine = " " + " ".join(self._formes) + " "
        self._comparateur = SequenceMatcher(autojunk=False)
        self._comparateur.set_seq2(self._formes)
        
    def verifier(self, citation : str) -> Verification:
        formes = [mot.forme for mot in decouper_en_mots(citation)]
        if not formes:
            return Verification(statut = StatutCitation.INTROUVABLE, score = 0.0)
        
        position = self._chaine.find(" " + " ".join(formes) + " ")
        if position >= 0:
            premier_mot = self._chaine[:position].count(" ")  # nombre de mots avant la citation
            return self._resultat(StatutCitation.EXACTE, 1.0, premier_mot, len(formes))

        premier_mot, nb_mots, score = self._passage_le_plus_proche(formes)
        if score >= self._seuil:
            return self._resultat(StatutCitation.APPROCHANTE, score, premier_mot, nb_mots)

        return Verification(statut=StatutCitation.INTROUVABLE, score=round(score, 3))
    

    def _passage_le_plus_proche(self, formes: list[str]) -> tuple[int, int, float]:
        self._comparateur.set_seq1(formes)
        ancre = self._comparateur.find_longest_match(0, len(formes), 0, len(self._formes))
        if ancre.size == 0:
            return 0, 0, 0.0

        marge = len(formes) // 2
        debut_zone = max(0, ancre.b - ancre.a - marge)
        zone = self._formes[debut_zone : ancre.b - ancre.a + len(formes) + marge]

        blocs = SequenceMatcher(None, formes, zone, autojunk=False).get_matching_blocks()
        communs = [bloc for bloc in blocs if bloc.size > 0]
        premier_mot = debut_zone + communs[0].b
        nb_mots = communs[-1].b + communs[-1].size - communs[0].b
        passage = self._formes[premier_mot : premier_mot + nb_mots]

        score = SequenceMatcher(None, formes, passage, autojunk=False).ratio()
        return premier_mot, nb_mots, score

    def _resultat(self, statut: StatutCitation, score: float, premier_mot: int, nb_mots: int) -> Verification:
        premier = self._mots[premier_mot]
        dernier = self._mots[premier_mot + nb_mots - 1]

        parties = []
        for numero, texte in self._textes.items():
            if premier.page <= numero <= dernier.page:
                debut = premier.debut if numero == premier.page else 0
                fin = dernier.fin if numero == dernier.page else len(texte)
                parties.append(texte[debut:fin])

        return Verification(
            statut=statut,
            score=round(score, 3),
            page=premier.page,
            extrait_source="\n".join(parties),
        )