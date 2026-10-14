"""Tests du domaine : la famille d'erreurs du projet."""

import pytest

from decrypte.domaine.erreurs import (
    DocumentIllisible,
    ErreurDecrypte,
    ExtractionImpossible,
    FichierIntrouvable,
    FormatNonGere,
    ProgrammeIntrouvable,
)

TOUTES_NOS_ERREURS = (
    FichierIntrouvable,
    FormatNonGere,
    DocumentIllisible,
    ExtractionImpossible,
    ProgrammeIntrouvable,
)


def test_nos_erreurs_appartiennent_a_la_meme_famille():
    for classe in TOUTES_NOS_ERREURS:
        assert issubclass(classe, ErreurDecrypte)


def test_un_seul_except_attrape_toutes_nos_erreurs():
    for classe in TOUTES_NOS_ERREURS:
        with pytest.raises(ErreurDecrypte):
            raise classe("un message")


def test_le_message_est_conserve():
    with pytest.raises(FormatNonGere, match="Format non géré : .docx"):
        raise FormatNonGere("Format non géré : .docx")