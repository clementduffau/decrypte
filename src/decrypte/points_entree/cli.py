import argparse
import sys

from decrypte.assemblage import creer_charger_programme
from decrypte.domaine.erreurs import ErreurDecrypte

APERCU_CARACTERES = 600


def commande_apercu(arguments : argparse.Namespace) -> None:
    document = creer_charger_programme().executer(arguments.fichier)
    total = sum(len(page.texte) for page in document.pages)
    
    print(f"Fichier : {arguments.fichier}")
    print(f"Type : {document.source.type}")
    print(f"Pages : {document.source.nb_pages}")
    print(f"Texte : {total} caractères")
    print(f"SHA-256 : {document.source.sha256}")
    
    for page in document.pages[: arguments.pages]:
        print(f"\n--- Page {page.numero} ({len(page.texte)} caractères) ---")
        extrait = page.texte[:APERCU_CARACTERES]
        if len(page.texte) > APERCU_CARACTERES:
            extrait += " […]"
        print(extrait)
        

def creer_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog = "decrypte",
        description = "Extraire, expliquer et comparer le programme des candidats"
    )
    sous_commandes = parser.add_subparsers(dest="commande", required=True)
    apercu = sous_commandes.add_parser("apercu", help = "Lire un programme et afficher un apercu")
    apercu.add_argument("fichier", help="Chemin du programme a lire (pdf, html, txt, md)")
    apercu.add_argument("--pages", type=int, default=2, help="Nombre de pages à afficher (2 par défaut)")
    apercu.set_defaults(func=commande_apercu)
    
    return parser



def main(argv: list[str] | None = None) -> int:
    arguments = creer_parser().parse_args(argv)
    try:
        arguments.func(arguments)
    except ErreurDecrypte as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())