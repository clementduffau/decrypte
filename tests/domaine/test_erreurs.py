"""Tests du domaine : la famille d'erreurs du projet."""

import pytest

from decrypte.domaine.erreurs import (
    DocumentIllisible,
    ErreurDecrypte,
    FichierIntrouvable,
    FormatNonGere,
)


def test_nos_erreurs_appartiennent_a_la_meme_famille():
    assert issubclass(FichierIntrouvable, ErreurDecrypte)
    assert issubclass(FormatNonGere, ErreurDecrypte)
    assert issubclass(DocumentIllisible, ErreurDecrypte)


def test_un_seul_except_attrape_toutes_nos_erreurs():
    for erreur in (FichierIntrouvable("absent"), FormatNonGere("format"), DocumentIllisible("vide")):
        with pytest.raises(ErreurDecrypte):
            raise erreur


def test_le_message_est_conserve():
    with pytest.raises(FormatNonGere, match="Format non géré : .docx"):
        raise FormatNonGere("Format non géré : .docx")