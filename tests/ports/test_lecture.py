

import pytest

from decrypte.domaine.modeles import Page
from decrypte.ports.lecture import LecteurDocument, SourceFichiers


# --- Des classes inventées pour les tests -----------------------------------


class LecteurValide:
    """Respecte le contrat LecteurDocument : les 2 attributs et la méthode lire."""

    type_document = "texte"
    extensions = (".txt",)

    def lire(self, octets: bytes) -> list[Page]:
        return [Page(numero=1, texte=octets.decode())]


class LecteurSansMethodeLire:
    """Incomplet : il lui manque la méthode lire."""

    type_document = "texte"
    extensions = (".txt",)


class SourceValide:
    """Respecte le contrat SourceFichiers : la méthode lire_octets."""

    def lire_octets(self, chemin) -> bytes:
        return b"contenu brut"


# --- Les tests ---------------------------------------------------------------


def test_un_port_ne_s_utilise_pas_tel_quel():
    # Un contrat n'a pas d'implémentation : Python refuse d'en créer un objet.
    with pytest.raises(TypeError):
        LecteurDocument()


def test_une_classe_qui_respecte_le_contrat_est_reconnue():
    assert isinstance(LecteurValide(), LecteurDocument)
    assert isinstance(SourceValide(), SourceFichiers)


def test_une_classe_incomplete_est_refusee():
    assert not isinstance(LecteurSansMethodeLire(), LecteurDocument)  # pas de lire()
    assert not isinstance(LecteurValide(), SourceFichiers)            # pas de lire_octets()


def test_un_lecteur_branche_sur_le_contrat_fonctionne():
    lecteur: LecteurDocument = LecteurValide()

    pages = lecteur.lire("Créer 500 maisons de santé".encode())

    assert pages == [Page(numero=1, texte="Créer 500 maisons de santé")]