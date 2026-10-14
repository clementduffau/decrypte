"""Tests de l'adaptateur de stockage JSON, sur le disque (dans un dossier temporaire)."""

from datetime import datetime, timezone

import pytest

from decrypte.adaptateurs.stockage_json import StockageJson
from decrypte.domaine.erreurs import ProgrammeIntrouvable
from decrypte.domaine.modeles import (
    Candidat,
    ProgrammeExtrait,
    Proposition,
    PropositionRejetee,
    StatutCitation,
    Theme,
    Verification,
)
from decrypte.ports.stockage import StockageProgrammes
from tests.conftest import PAGES_PROGRAMME_FICTIF, creer_document


@pytest.fixture
def programme() -> ProgrammeExtrait:
    """Un programme extrait complet : 1 proposition gardée, 1 rejetée."""
    return ProgrammeExtrait(
        candidat=Candidat(id="camille-exemple", nom="Camille Exemple", election="presidentielle-2027"),
        source=creer_document(*PAGES_PROGRAMME_FICTIF).source,
        extrait_le=datetime(2026, 10, 14, 20, 0, tzinfo=timezone.utc),
        modele_llm="ministral-14b-2512",
        propositions=[
            Proposition(
                id="camille-exemple-001",
                candidat_id="camille-exemple",
                citation="Nous proposons de créer 500 nouvelles maisons de santé d'ici 2030",
                resume_neutre="Créer 500 maisons de santé d'ici 2030",
                theme=Theme.SANTE,
                chiffres=["500", "2030"],
                verification=Verification(
                    statut=StatutCitation.EXACTE,
                    score=1.0,
                    page=1,
                    extrait_source="Nous proposons de créer 500 nouvelles maisons de santé d'ici 2030",
                ),
            )
        ],
        rejetees=[
            PropositionRejetee(
                citation="Nous supprimerons l'impôt sur le revenu pour tous les Français",
                resume_neutre="Supprimer l'impôt sur le revenu",
                raison="citation introuvable dans le programme (ressemblance 0.26)",
            )
        ],
    )


def test_respecte_le_contrat(tmp_path):
    assert isinstance(StockageJson(tmp_path), StockageProgrammes)


def test_enregistrer_puis_charger_redonne_le_meme_programme(tmp_path, programme):
    stockage = StockageJson(tmp_path)

    stockage.enregistrer(programme)
    relu = stockage.charger("camille-exemple")

    assert relu == programme  # dates, thèmes, statuts… tout est identique


def test_un_fichier_par_candidat(tmp_path, programme):
    emplacement = StockageJson(tmp_path).enregistrer(programme)

    assert emplacement == str(tmp_path / "camille-exemple.json")
    assert (tmp_path / "camille-exemple.json").is_file()


def test_dossier_cree_s_il_n_existe_pas(tmp_path, programme):
    dossier = tmp_path / "data" / "extraits"  # n'existe pas encore

    StockageJson(dossier).enregistrer(programme)

    assert (dossier / "camille-exemple.json").is_file()


def test_json_lisible_par_un_humain(tmp_path, programme):
    StockageJson(tmp_path).enregistrer(programme)

    contenu = (tmp_path / "camille-exemple.json").read_text(encoding="utf-8")

    assert "maisons de santé" in contenu  # les accents ne sont pas transformés en \u00e9
    assert '\n  "candidat"' in contenu    # indenté : une information par ligne


def test_reenregistrer_remplace_l_ancien_fichier(tmp_path, programme):
    stockage = StockageJson(tmp_path)
    stockage.enregistrer(programme)

    stockage.enregistrer(programme.model_copy(update={"modele_llm": "autre-modele"}))

    assert stockage.charger("camille-exemple").modele_llm == "autre-modele"
    assert [f.name for f in tmp_path.iterdir()] == ["camille-exemple.json"]  # aucun .tmp oublié


def test_programme_absent(tmp_path):
    with pytest.raises(ProgrammeIntrouvable, match="inconnu"):
        StockageJson(tmp_path).charger("inconnu")


def test_identifiant_dangereux_refuse(tmp_path):
    with pytest.raises(ProgrammeIntrouvable, match="invalide"):
        StockageJson(tmp_path).charger("../../secret")