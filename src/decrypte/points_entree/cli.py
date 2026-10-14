
import argparse
import logging
import re
import sys

from dotenv import find_dotenv, load_dotenv

from decrypte.assemblage import DOSSIER_EXTRAITS, creer_charger_programme, creer_extraire_programme, creer_stockage
from decrypte.domaine.decoupage import Morceau
from decrypte.domaine.erreurs import ErreurDecrypte
from decrypte.domaine.modeles import Candidat, ProgrammeExtrait, StatutCitation

# Nombre de caractères affichés au maximum pour chaque page.
APERCU_CARACTERES = 600


# ---------------------------------------------------------------------------
# Commande « apercu »
# ---------------------------------------------------------------------------


def commande_apercu(arguments: argparse.Namespace) -> None:
    """Lit un programme et affiche un aperçu de ce qui a été lu."""
    document = creer_charger_programme().executer(arguments.fichier)
    total = sum(len(page.texte) for page in document.pages)

    print(f"Fichier  : {arguments.fichier}")
    print(f"Type     : {document.source.type}")
    print(f"Pages    : {document.source.nb_pages}")
    print(f"Texte    : {total} caractères")
    print(f"SHA-256  : {document.source.sha256}")

    for page in document.pages[: arguments.pages]:
        print(f"\n--- Page {page.numero} ({len(page.texte)} caractères) ---")
        extrait = page.texte[:APERCU_CARACTERES]
        if len(page.texte) > APERCU_CARACTERES:
            extrait += " […]"
        print(extrait)


# ---------------------------------------------------------------------------
# Commande « extraire »
# ---------------------------------------------------------------------------


def commande_extraire(arguments: argparse.Namespace) -> None:
    """Lit un programme, en extrait les propositions avec l'IA, et enregistre le résultat."""
    document = creer_charger_programme().executer(arguments.fichier, url=arguments.url)
    print(f"Programme lu : {document.source.nb_pages} pages.")

    candidat = Candidat(
        id=arguments.candidat_id,
        nom=arguments.nom,
        parti=arguments.parti,
        election=arguments.election,
    )
    print("Extraction des propositions (cela peut prendre plusieurs minutes)…")
    programme = creer_extraire_programme().executer(document, candidat, suivi=afficher_progression)

    emplacement = creer_stockage(arguments.sortie).enregistrer(programme)
    afficher_bilan(programme, emplacement)


def afficher_progression(morceau: Morceau, total: int) -> None:
    premiere, derniere = morceau.pages[0], morceau.pages[-1]
    pages = f"page {premiere}" if premiere == derniere else f"pages {premiere} à {derniere}"
    print(f"  Morceau {morceau.numero}/{total} ({pages})…", flush=True)


def afficher_bilan(programme: ProgrammeExtrait, emplacement: str) -> None:
    exactes = sum(p.verification.statut == StatutCitation.EXACTE for p in programme.propositions)
    approchantes = len(programme.propositions) - exactes
    doublons = sum(r.raison.startswith("doublon") for r in programme.rejetees)
    introuvables = len(programme.rejetees) - doublons

    print(f"\nBilan pour {programme.candidat.nom} (modèle : {programme.modele_llm})")
    print(f"  Propositions gardées  : {len(programme.propositions)} ({exactes} exacte(s), {approchantes} approchante(s) à vérifier)")
    print(f"  Propositions rejetées : {len(programme.rejetees)} ({introuvables} introuvable(s), {doublons} doublon(s))")
    print(f"\nRésultat enregistré dans {emplacement}")


def identifiant(valeur: str) -> str:
    """Vérifie un identifiant de candidat tapé dans le terminal (même règle que Candidat.id)."""
    if not re.fullmatch(r"[a-z0-9-]+", valeur):
        raise argparse.ArgumentTypeError(
            f"identifiant invalide {valeur!r} : minuscules, chiffres et tirets seulement (ex. camille-exemple)"
        )
    return valeur


# ---------------------------------------------------------------------------
# Le programme principal
# ---------------------------------------------------------------------------


def creer_parser() -> argparse.ArgumentParser:
    """Décrit les commandes et les options acceptées par le programme."""
    parser = argparse.ArgumentParser(
        prog="decrypte",
        description="Extraire, expliquer et comparer les propositions des candidats.",
    )
    sous_commandes = parser.add_subparsers(dest="commande", required=True)

    apercu = sous_commandes.add_parser("apercu", help="Lire un programme et afficher un aperçu.")
    apercu.add_argument("fichier", help="Chemin du programme (.pdf, .html, .htm, .txt, .md)")
    apercu.add_argument("--pages", type=int, default=2, help="Nombre de pages à afficher (2 par défaut)")
    apercu.set_defaults(fonction=commande_apercu)

    extraire = sous_commandes.add_parser("extraire", help="Extraire les propositions d'un programme avec l'IA.")
    extraire.add_argument("fichier", help="Chemin du programme (.pdf, .html, .htm, .txt, .md)")
    extraire.add_argument("--candidat-id", required=True, type=identifiant, help="Identifiant, ex. camille-exemple")
    extraire.add_argument("--nom", required=True, help='Nom du candidat, ex. "Camille Exemple"')
    extraire.add_argument("--parti", default=None, help="Parti ou mouvement (facultatif)")
    extraire.add_argument("--election", default="presidentielle-2027", help="Élection (presidentielle-2027 par défaut)")
    extraire.add_argument("--url", default=None, help="Adresse officielle du programme (facultatif, recommandé)")
    extraire.add_argument("--sortie", default=DOSSIER_EXTRAITS, help=f"Dossier du résultat ({DOSSIER_EXTRAITS} par défaut)")
    extraire.set_defaults(fonction=commande_extraire)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Lance le programme. Renvoie 0 si tout va bien, 1 en cas d'erreur."""
    load_dotenv(find_dotenv(usecwd=True))  # lit le fichier .env du dossier courant (clé Mistral…)
    logging.basicConfig(level=logging.WARNING, format="  ! %(message)s")  # affiche les nouveaux essais
    arguments = creer_parser().parse_args(argv)

    try:
        arguments.fonction(arguments)
    except ErreurDecrypte as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())