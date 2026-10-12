

from bs4 import BeautifulSoup

from decrypte.domaine.modeles import Page

# Balises dont le contenu n'est jamais le programme du candidat.
BALISES_A_RETIRER = ["script", "style", "noscript", "nav", "header", "footer"]


class LecteurHtml:
    type_document = "html"
    extensions = (".html", ".htm")

    def lire(self, octets: bytes) -> list[Page]:

        soup = BeautifulSoup(octets, "html.parser")

        for balise in soup(BALISES_A_RETIRER):
            balise.decompose()  

        texte = soup.get_text("\n")  # un saut de ligne entre chaque bloc de texte
        return [Page(numero=1, texte=texte)]