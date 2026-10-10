#!/usr/bin/env python3
"""
common.py — Helpers partagés pour les scripts d'injection de défauts.

Fournit :
    - InjectionBus   : classe pour envoyer des trames PERC_OBJECT
    - corrupt_crc    : corrompt le CRC d'une trame DEC_ALERT
    - make_object    : construit un PerceivedObject de test
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import can
import cantools

from perception.can_tx import (
    DEFAULT_DBC_PATH,
    PerceptionCanTx,
    PerceivedObject,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

DEFAULT_CHANNEL = "vcan0"

# IDs
CAN_ID_PERC_OBJECT = 0x100
CAN_ID_DEC_ALERT = 0x200
CAN_ID_DEC_HB = 0x201


# ---------------------------------------------------------------------------
# Injection sur le bus
# ---------------------------------------------------------------------------

class InjectionBus:
    """
    Wrapper simplifié pour envoyer des trames PERC_OBJECT (0x100)
    sur le bus vcan0.

    Utilise directement python-can (plus bas niveau que perception.can_tx),
    ce qui permet d'envoyer des trames corrompues brutes.
    """

    def __init__(self, channel: str = DEFAULT_CHANNEL) -> None:
        self.channel = channel
        self.db = cantools.database.load_file(str(DEFAULT_DBC_PATH))
        self.msg_perc = self.db.get_message_by_name("PERC_OBJECT")

        logger.info("Chargement DBC : %s", DEFAULT_DBC_PATH)
        logger.info(
            "Message PERC_OBJECT : id=0x%X, dlc=%d",
            self.msg_perc.frame_id, self.msg_perc.length,
        )

        try:
            self.bus = can.interface.Bus(channel=channel, interface="socketcan")
            logger.info("Bus CAN ouvert sur '%s'", channel)
        except OSError as exc:
            raise RuntimeError(
                f"Impossible d'ouvrir '{channel}'. "
                f"Avez-vous lancé scripts/setup_vcan.sh ? Détail : {exc}"
            ) from exc

    def close(self) -> None:
        try:
            self.bus.shutdown()
            logger.info("Bus CAN fermé")
        except Exception:  # noqa: BLE001
            pass

    def __enter__(self) -> "InjectionBus":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # ------------------------------------------------------------------

    def send_raw(self, arbitration_id: int, payload: bytes) -> None:
        """Envoie une trame CAN brute (peut être corrompue)."""
        frame = can.Message(
            arbitration_id=arbitration_id,
            data=payload,
            is_extended_id=False,
        )
        self.bus.send(frame)

    def send_perc_object(
        self,
        obj: PerceivedObject,
        *,
        corrupt: bool = False,
    ) -> None:
        """
        Encode et envoie une trame PERC_OBJECT.

        Args:
            obj: objet à envoyer
            corrupt: si True, corrompt volontairement 1 bit dans le payload
        """
        data = self.msg_perc.encode({
            "obj_id": obj.obj_id,
            "dist_m": obj.distance_m,
            "rel_speed_mps": obj.rel_speed_mps,
            "ttc_s": obj.ttc_s,
            "valid": obj.valid,
        })

        if corrupt and len(data) > 0:
                        # Flip complet de l'octet 1 (partie basse de la distance)
            # → change la distance de ~2.55 m (visible et testable)
            data = bytearray(data)
            data[1] ^= 0xFF
            data = bytes(data)

        self.send_raw(CAN_ID_PERC_OBJECT, data)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_object(
    distance_m: float = 25.0,
    rel_speed_mps: float = -5.0,
    ttc_s: Optional[float] = None,
    valid: bool = True,
    obj_id: int = 1,
) -> PerceivedObject:
    """Construit un PerceivedObject avec valeurs par défaut réalistes."""
    if ttc_s is None:
        ttc_s = distance_m / abs(rel_speed_mps) if rel_speed_mps != 0 else 999.0

    return PerceivedObject(
        obj_id=obj_id,
        distance_m=distance_m,
        rel_speed_mps=rel_speed_mps,
        ttc_s=ttc_s,
        valid=1 if valid else 0,
    )


def sleep_ms(ms: int) -> None:
    """Attend N millisecondes."""
    time.sleep(ms / 1000.0)


# ---------------------------------------------------------------------------
# CLI de test
# ---------------------------------------------------------------------------

def _main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    print("Test : envoi d'une trame PERC_OBJECT normale")
    with InjectionBus() as inj:
        obj = make_object(distance_m=25.0, rel_speed_mps=-5.0)
        print(f"  → {obj}")
        inj.send_perc_object(obj)

    print("OK")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())

