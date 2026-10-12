from decrypte.domaine.erreurs import DocumentIllisible
from decrypte.domaine.modeles import Page

class LecteurTexte:
    type_document = "texte"
    extensions = (".txt", ".md")
    
    def lire(self,octets : bytes) -> list[Page]:
        
        try:
            contenu = octets.decode("utf-8-sig")
            
        except UnicodeDecodeError as erreur:
            raise DocumentIllisible("le document n'est pas lisible en UTF-8") from erreur
        
        morceaux = contenu.split("\f")
        return [Page(numero = i, texte = morceau) for i, morceau in enumerate(morceaux, start = 1)]