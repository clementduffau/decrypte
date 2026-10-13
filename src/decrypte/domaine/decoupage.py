from pydantic import BaseModel, Field

from decrypte.domaine.modeles import Document

TAILLE_MAX = 12000

SEPARATEUR = "\n\n"

class Morceau(BaseModel):
    numero : int = Field(ge=1)
    pages : list[int] = Field(min_length=1)
    texte : str = Field(min_length = 1)
    
    
def couper_ligne(ligne : str, taille_max : int) -> list[str]:
    morceaux = []
    while len(ligne) > taille_max:
        coupe = ligne.rfind(" ", 0, taille_max) + 1
        if coupe == 0:
            coupe = taille_max
        morceaux.append(ligne[:coupe])
        ligne = ligne[coupe:]
    if ligne:
        morceaux.append(ligne)
    return morceaux


def couper_texte(texte : str, taille_max : int) -> list[str]:
    if taille_max < 1:
        raise ValueError(f"taille_max doit etre au moins 1, pas {taille_max}")
    
    blocs = []
    en_cours = ""
    for ligne in texte.splitlines(keepends = True):
        for morceau_de_ligne in couper_ligne(ligne, taille_max):
            if en_cours and len(en_cours) + len(morceau_de_ligne) > taille_max:
                blocs.append(en_cours)
                en_cours = ""
            en_cours += morceau_de_ligne
            
    if en_cours:
        blocs.append(en_cours)
        
    return blocs


def decouper(document : Document, taille_max : int = TAILLE_MAX) -> list[Morceau]:
    
    blocs = [
        (page.numero, bloc)
        for page in document.pages
        if page.texte.strip()
        for bloc in couper_texte(page.texte, taille_max)
    ]
    
    groupes: list[list[tuple[int, str]]] = []
    taille = 0

    for numero_page, bloc in blocs:
        if groupes and taille + len(SEPARATEUR) + len(bloc) <= taille_max:
            groupes[-1].append((numero_page, bloc))  # le bloc tient dans le groupe en cours
            taille += len(SEPARATEUR) + len(bloc)
        else:
            groupes.append([(numero_page, bloc)])  # sinon, on commence un nouveau groupe
            taille = len(bloc)

    return [
        Morceau(
            numero=numero,
            pages=sorted({numero_page for numero_page, _ in groupe}),
            texte=SEPARATEUR.join(bloc for _, bloc in groupe),
        )
        for numero, groupe in enumerate(groupes, start=1)
    ]
            