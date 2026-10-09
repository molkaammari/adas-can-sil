#!/usr/bin/env python3
"""
decoder.py — Décodage des trames DEC_ALERT et DEC_HB du Dashboard.

Responsabilité unique :
    - Charger le DBC (shared/dbc/adas.dbc)
    - Décoder une trame DEC_ALERT (0x200) en structure Alert
    - Décoder une trame DEC_HB (0x201) en structure Heartbeat

Ne fait PAS :
    - La réception CAN   (voir receiver.py)
    - L'affichage        (voir main.py)

Références : REQ-DEC-006, REQ-DEC-007
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cantools
from cantools.database.can import Database, Message


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

DEFAULT_DBC_PATH = (
    Path(__file__).parent.parent / "shared" / "dbc" / "adas.dbc"
)

CAN_ID_DEC_ALERT = 0x200
CAN_ID_DEC_HB = 0x201

# Niveaux d'alerte (correspondent au DBC)
ALERT_LEVELS = {
    0: ("OFF",     "grey"),
    1: ("STANDBY", "green"),
    2: ("WARNING", "yellow"),
    3: ("BRAKE",   "red"),
    4: ("FAULT",   "magenta"),
}


# ---------------------------------------------------------------------------
# Structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Alert:
    """Trame DEC_ALERT décodée (0x200)."""
    alert_level: int      # 0..4
    level_name: str       # "STANDBY", "WARNING", etc.
    level_color: str      # "green", "yellow", etc.
    ttc_s: float
    counter: int          # 0..15
    crc: int              # 0..255

    def __str__(self) -> str:
        return (
            f"Alert(level={self.alert_level}/{self.level_name} "
            f"ttc={self.ttc_s:.2f}s counter={self.counter} crc=0x{self.crc:02X})"
        )


@dataclass(frozen=True)
class Heartbeat:
    """Trame DEC_HB décodée (0x201)."""
    alive_ctr: int        # 0..255
    state: int            # 0..4

    def __str__(self) -> str:
        return f"Heartbeat(alive_ctr={self.alive_ctr} state={self.state})"


# ---------------------------------------------------------------------------
# Décodeur
# ---------------------------------------------------------------------------

class DashboardDecoder:
    """Décodeur des trames reçues par le Dashboard."""

    def __init__(self, dbc_path: Path = DEFAULT_DBC_PATH) -> None:
        if not dbc_path.exists():
            raise FileNotFoundError(f"DBC introuvable : {dbc_path}")

        logger.info("Chargement DBC : %s", dbc_path)
        self.db: Database = cantools.database.load_file(str(dbc_path))

        self.msg_dec_alert: Message = self.db.get_message_by_name("DEC_ALERT")
        self.msg_dec_hb: Message = self.db.get_message_by_name("DEC_HB")

        logger.info(
            "Messages chargés : DEC_ALERT (id=0x%X, dlc=%d), DEC_HB (id=0x%X, dlc=%d)",
            self.msg_dec_alert.frame_id, self.msg_dec_alert.length,
            self.msg_dec_hb.frame_id, self.msg_dec_hb.length,
        )

    # ------------------------------------------------------------------
    # Décodage DEC_ALERT
    # ------------------------------------------------------------------

    def decode_alert(self, data: bytes) -> Optional[Alert]:
        """
        Décode un payload DEC_ALERT (4 octets).

        Returns:
            Alert si le décodage réussit, None sinon.
        """
        
        try:
            decoded = self.msg_dec_alert.decode(data)

            # cantools renvoie un NamedSignalValue si une table VAL_ est définie
            # (contient à la fois .value (numérique) et .name (str))
            raw_level = decoded["alert_level"]
            level = self._to_int(raw_level)

            level_name, level_color = ALERT_LEVELS.get(
                level, ("UNKNOWN", "white")
            )

            return Alert(
                alert_level=level,
                level_name=level_name,
                level_color=level_color,
                ttc_s=float(decoded["ttc_s"]),
                counter=int(decoded["counter"]),
                crc=int(decoded["crc"]),
            )

        except Exception as exc:  # noqa: BLE001
            logger.warning("Échec décodage DEC_ALERT : %s", exc)
            return None

    # ------------------------------------------------------------------
    # Décodage DEC_HB
    # ------------------------------------------------------------------

    def decode_hb(self, data: bytes) -> Optional[Heartbeat]:
        """
        Décode un payload DEC_HB (2 octets).

        Returns:
            Heartbeat si le décodage réussit, None sinon.
        """
        try:
            decoded = self.msg_dec_hb.decode(data)

            
            
            raw_state = decoded["state"]
            state = self._to_int(raw_state)
            

            return Heartbeat(
                alive_ctr=int(decoded["alive_ctr"]),
                state=state,
            )

        except Exception as exc:  # noqa: BLE001
            logger.warning("Échec décodage DEC_HB : %s", exc)
            return None

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    @staticmethod
    def _label_to_level(label: str) -> int:
        """Convertit un label FSM ('STANDBY') en niveau (1)."""
        for value, (name, _) in ALERT_LEVELS.items():
            if name == label:
                return value
        return -1  # inconnu
        
        
        
        
    @staticmethod
    def _to_int(value) -> int:
        """
        Convertit une valeur cantools (int, str ou NamedSignalValue) en int.
        """
        # NamedSignalValue a un attribut .value (numérique)
        if hasattr(value, "value"):
            return int(value.value)
        # str : peut être un label ("WARNING") ou un nombre ("2")
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                # C'est un label → on cherche sa valeur
                for k, (name, _) in ALERT_LEVELS.items():
                    if name == value:
                        return k
                return -1
        return int(value)


# ---------------------------------------------------------------------------
# CLI de test
# ---------------------------------------------------------------------------

def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Test du décodeur DEC_ALERT / DEC_HB",
    )
    parser.add_argument(
        "--hex-alert",
        default="02B90020",
        help="Payload DEC_ALERT en hex (défaut : 02B90020)",
    )
    parser.add_argument(
        "--hex-hb",
        default="2A02",
        help="Payload DEC_HB en hex (défaut : 2A02)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    decoder = DashboardDecoder()

    alert_bytes = bytes.fromhex(args.hex_alert)
    alert = decoder.decode_alert(alert_bytes)
    print(f"DEC_ALERT[{args.hex_alert}] → {alert}")

    hb_bytes = bytes.fromhex(args.hex_hb)
    hb = decoder.decode_hb(hb_bytes)
    print(f"DEC_HB   [{args.hex_hb}] → {hb}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())

