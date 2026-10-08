"""
conftest.py — Fixtures pytest partagées pour les tests ADAS FCW.

Ce fichier est automatiquement chargé par pytest avant tous les tests.
Il expose des fixtures réutilisables (DBC, chemins, données de test).
"""

from __future__ import annotations

from pathlib import Path

import cantools
import pytest
from cantools.database.can import Database


# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
DBC_PATH = PROJECT_ROOT / "shared" / "dbc" / "adas.dbc"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def dbc_path() -> Path:
    """Chemin vers le fichier DBC (fixture session = chargée une seule fois)."""
    assert DBC_PATH.exists(), f"DBC introuvable : {DBC_PATH}"
    return DBC_PATH


@pytest.fixture(scope="session")
def db(dbc_path: Path) -> Database:
    """
    Base de données CAN chargée depuis le DBC.

    scope='session' : chargé une seule fois pour toute la session pytest.
    """
    return cantools.database.load_file(str(dbc_path))


@pytest.fixture(scope="session")
def perc_object_msg(db: Database):
    """Message PERC_OBJECT (0x100) — émis par l'ECU Perception."""
    return db.get_message_by_name("PERC_OBJECT")


@pytest.fixture(scope="session")
def dec_alert_msg(db: Database):
    """Message DEC_ALERT (0x200) — émis par l'ECU Décision."""
    return db.get_message_by_name("DEC_ALERT")


@pytest.fixture(scope="session")
def dec_hb_msg(db: Database):
    """Message DEC_HB (0x201) — heartbeat de l'ECU Décision."""
    return db.get_message_by_name("DEC_HB")


# ---------------------------------------------------------------------------
# Données de test réutilisables
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_perc_data() -> dict:
    """Jeu de données nominal pour PERC_OBJECT."""
    return {
        "obj_id": 1,
        "dist_m": 25.0,
        "rel_speed_mps": -5.0,
        "ttc_s": 5.0,
        "valid": 1,
    }


@pytest.fixture
def valid_dec_alert_data() -> dict:
    """Jeu de données nominal pour DEC_ALERT."""
    return {
        "alert_level": 2,
        "ttc_s": 1.85,
        "counter": 5,
        "crc": 0xA5,
    }


@pytest.fixture
def valid_dec_hb_data() -> dict:
    """Jeu de données nominal pour DEC_HB."""
    return {
        "alive_ctr": 42,
        "state": 2,
    }
