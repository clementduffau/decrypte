from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from decrypte.domaine.erreurs import DocumentIllisible
from decrypte.domaine.modeles import Page


class LecteurPdf:
    type_document = "pdf"
    extensions = (".pdf",)
    
    def lire(self, octets: bytes) ->list[Page]:
        try :
            reader = PdfReader(BytesIO(octets))
        except PdfReadError as erreur: 
            raise DocumentIllisible("Le fichier n'est pas un PDF valide, ou il est endommagé.") from erreur
        
        pages = []
        for numero, page in enumerate(reader.pages, start = 1):
           texte = page.extract_text() or ""
           pages.append(Page(numero = numero, texte = texte))
        return pages             