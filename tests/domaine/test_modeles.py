"""Tests du domaine : les moules refusent bien les données incorrectes."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from decrypte.domaine.modeles import (
    Candidat,
    ProgrammeExtrait,
    Proposition,
    PropositionExtraite,
    SourceDocument,
    StatutCitation,
    Theme,
    Verification,
)

CITATION_VALIDE = "Nous proposons de créer 500 nouvelles maisons de santé d'ici 2030."


def test_proposition_valide_acceptee():
    proposition = PropositionExtraite(
        citation=CITATION_VALIDE,
        resume_neutre="Créer 500 maisons de santé d'ici 2030.",
        theme="sante",  # le texte "sante" est converti en Theme.SANTE
        chiffres=["500", "2030"],
    )
    assert proposition.theme == Theme.SANTE
    assert proposition.chiffres == ["500", "2030"]


def test_chiffres_vides_par_defaut():
    proposition = PropositionExtraite(
        citation=CITATION_VALIDE,
        resume_neutre="Créer des maisons de santé.",
        theme="sante",
    )
    assert proposition.chiffres == []


def test_citation_trop_courte_refusee():
    with pytest.raises(ValidationError):
        PropositionExtraite(citation="Trop court", resume_neutre="Créer quelque chose.", theme="sante")


def test_resume_de_plus_de_25_mots_refuse():
    resume_trop_long = " ".join(["mot"] * 26)
    with pytest.raises(ValidationError, match="résumé trop long"):
        PropositionExtraite(citation=CITATION_VALIDE, resume_neutre=resume_trop_long, theme="sante")


def test_theme_inexistant_refuse():
    with pytest.raises(ValidationError):
        PropositionExtraite(citation=CITATION_VALIDE, resume_neutre="Créer des stades.", theme="sport")


def test_proposition_finale_herite_des_regles():
    # Proposition hérite de PropositionExtraite : la règle des 25 mots s'applique aussi.
    with pytest.raises(ValidationError):
        Proposition(
            id="p1",
            candidat_id="camille-exemple",
            citation=CITATION_VALIDE,
            resume_neutre=" ".join(["mot"] * 30),
            theme="sante",
            verification=Verification(statut="exacte", score=1.0, page=1),
        )


def test_type_de_document_inconnu_refuse():
    # TypeDocument n'accepte que "pdf", "html" ou "texte".
    with pytest.raises(ValidationError):
        SourceDocument(chemin="programme.docx", sha256="a" * 64, nb_pages=1, type="docx")


def test_empreinte_mal_formee_refusee():
    # Une empreinte doit faire exactement 64 caractères hexadécimaux.
    with pytest.raises(ValidationError):
        SourceDocument(chemin="programme.pdf", sha256="pas-une-empreinte", nb_pages=1, type="pdf")


def test_programme_extrait_aller_retour_json():
    programme = ProgrammeExtrait(
        candidat=Candidat(
            id="camille-exemple",
            nom="Camille Exemple",
            parti="Mouvement Fictif pour les Tests",
            election="exemple-fictif",
        ),
        source=SourceDocument(chemin="programme.pdf", sha256="a" * 64, nb_pages=2, type="pdf"),
        extrait_le=datetime(2026, 10, 12, 18, 0),
        modele_llm="faux-modele",
        propositions=[
            Proposition(
                id="p1",
                candidat_id="camille-exemple",
                citation=CITATION_VALIDE,
                resume_neutre="Créer 500 maisons de santé d'ici 2030.",
                theme="sante",
                verification=Verification(statut=StatutCitation.EXACTE, score=1.0, page=1),
            )
        ],
    )

    texte_json = programme.model_dump_json()                 # objet → texte JSON
    relu = ProgrammeExtrait.model_validate_json(texte_json)  # texte JSON → objet

    assert relu == programme