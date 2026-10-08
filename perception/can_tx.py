#!/usr/bin/env python3
"""
can_tx.py — Émission CAN pour l'ECU Perception.

Responsabilité unique :
    - Charger le DBC (shared/dbc/adas.dbc)
    - Encoder une trame PERC_OBJECT à partir d'une Detection + DistanceEstimate
    - Envoyer la trame sur l'interface SocketCAN (vcan0)

Ne fait PAS :
    - Détection          (voir detector.py)
    - Estimation distance (voir distance.py)
    - Décision           (voir ECU Décision en C++)

Références : REQ-PER-004, REQ-CAN-001 à 004
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import can
import cantools
from cantools.database.can import Database, Message, Signal

from .detector import Detection
from .distance import DistanceEstimate


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

DEFAULT_DBC_PATH = (
    Path(__file__).parent.parent / "shared" / "dbc" / "adas.dbc"
)
DEFAULT_CHANNEL = "vcan0"
DEFAULT_BITRATE = 500_000  # ignoré sur vcan, mais requis par python-can

# Identifiant du message dans le DBC
PERC_OBJECT_MSG_NAME = "PERC_OBJECT"

# Période d'émission cible (REQ-PER-004 : 20 Hz)
TX_PERIOD_S = 0.050

# Encodage des valeurs scalaires (facteurs définis dans le DBC)
DIST_FACTOR = 0.01        # m → centimètres
SPEED_FACTOR = 0.01       # m/s → centièmes
SPEED_OFFSET = -100.0     # offset défini dans le DBC
TTC_FACTOR = 0.01         # s → centisecondes

# Encodeur "valid" : 1 si objet valide, 0 sinon
VALID_YES = 1
VALID_NO = 0


# ---------------------------------------------------------------------------
# Structure interne
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PerceivedObject:
    """Un objet perçu, prêt à être émis sur le bus CAN."""
    obj_id: int
    distance_m: float
    rel_speed_mps: float
    ttc_s: float
    valid: int

    def __str__(self) -> str:
        return (
            f"id={self.obj_id:3d} "
            f"d={self.distance_m:6.2f}m "
            f"v_rel={self.rel_speed_mps:+6.2f}m/s "
            f"ttc={self.ttc_s:5.2f}s "
            f"valid={self.valid}"
        )


# ---------------------------------------------------------------------------
# Émetteur CAN
# ---------------------------------------------------------------------------

class PerceptionCanTx:
    """Émetteur de trames PERC_OBJECT sur SocketCAN."""

    def __init__(
        self,
        dbc_path: Path = DEFAULT_DBC_PATH,
        channel: str = DEFAULT_CHANNEL,
        bitrate: int = DEFAULT_BITRATE,
    ) -> None:
        """
        Args:
            dbc_path: chemin du DBC
            channel: interface SocketCAN (ex: 'vcan0')
            bitrate: bitrate (ignoré pour vcan)
        """
        if not dbc_path.exists():
            raise FileNotFoundError(f"DBC introuvable : {dbc_path}")

        logger.info("Chargement DBC : %s", dbc_path)
        self.db: Database = cantools.database.load_file(str(dbc_path))

        self.msg: Message = self.db.get_message_by_name(PERC_OBJECT_MSG_NAME)
        logger.info(
            "Message '%s' chargé : id=0x%X dlc=%d, %d signal(aux)",
            PERC_OBJECT_MSG_NAME,
            self.msg.frame_id,
            self.msg.length,
            len(self.msg.signals),
        )

        # Ouverture du bus CAN
        logger.info("Ouverture bus CAN sur '%s'", channel)
        try:
            self.bus = can.interface.Bus(
                channel=channel,
                interface="socketcan",
                bitrate=bitrate,
            )
        except OSError as exc:
            raise RuntimeError(
                f"Impossible d'ouvrir '{channel}'. "
                f"Avez-vous lancé 'scripts/setup_vcan.sh' ? "
                f"Détail : {exc}"
            ) from exc

        self._tx_count = 0
        self._last_tx_ts: Optional[float] = None

    # ------------------------------------------------------------------
    # Encodage
    # ------------------------------------------------------------------

    def encode(self, obj: PerceivedObject) -> bytes:
        """
        Encode un PerceivedObject en payload CAN (bytes) selon le DBC.

        Raises:
            ValueError si une valeur sort de la plage autorisée.
        """
        data = {
            "obj_id": obj.obj_id,
            "dist_m": obj.distance_m,
            "rel_speed_mps": obj.rel_speed_mps,
            "ttc_s": obj.ttc_s,
            "valid": obj.valid,
        }
        try:
            return self.msg.encode(data, strict=True)
        except Exception as exc:
            raise ValueError(
                f"Encodage impossible pour {obj} : {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Émission
    # ------------------------------------------------------------------

    def send(self, obj: PerceivedObject) -> None:
        """Encode et envoie une trame PERC_OBJECT."""
        payload = self.encode(obj)
        frame = can.Message(
            arbitration_id=self.msg.frame_id,
            data=payload,
            is_extended_id=False,
        )
        try:
            self.bus.send(frame)
            self._tx_count += 1
            self._last_tx_ts = time.monotonic()
            logger.debug("TX #%d : %s", self._tx_count, obj)
        except can.CanError as exc:
            logger.error("Erreur d'émission CAN : %s", exc)

    def send_batch(self, objs: list[PerceivedObject]) -> None:
        """Envoie plusieurs objets (utile si on veut en émettre plusieurs)."""
        for obj in objs:
            self.send(obj)

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Ferme proprement le bus CAN."""
        try:
            self.bus.shutdown()
            logger.info("Bus CAN fermé (%d trames émises)", self._tx_count)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Erreur à la fermeture du bus : %s", exc)

    # ------------------------------------------------------------------
    # Contexte (with-statement)
    # ------------------------------------------------------------------

    def __enter__(self) -> "PerceptionCanTx":
        return self

    def __exit__(self, *exc_info) -> None:
        self.shutdown()


# ---------------------------------------------------------------------------
# Conversions depuis Detection + DistanceEstimate
# ---------------------------------------------------------------------------

def build_perceived_object(
    detection: Detection,
    estimate: DistanceEstimate,
    rel_speed_mps: float = 0.0,
    ttc_s: float = 0.0,
    obj_id: int = 1,
) -> PerceivedObject:
    """
    Construit un PerceivedObject à partir d'une détection + estimation.

    Note : la vitesse relative et le TTC sont ici passés en paramètre.
    Ils seront calculés proprement dans main.py à partir de l'historique
    temporel des détections (Phase 2.7). Pour l'instant, valeurs par défaut.
    """
    return PerceivedObject(
        obj_id=obj_id,
        distance_m=estimate.distance_m,
        rel_speed_mps=rel_speed_mps,
        ttc_s=ttc_s,
        valid=VALID_YES,
    )


# ---------------------------------------------------------------------------
# CLI de test
# ---------------------------------------------------------------------------

def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Test d'émission CAN (PERC_OBJECT) sur vcan0",
    )
    parser.add_argument(
        "--channel",
        default=DEFAULT_CHANNEL,
        help=f"Interface SocketCAN (défaut : {DEFAULT_CHANNEL})",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Nombre de trames de test à émettre",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Objet de test
    test_obj = PerceivedObject(
        obj_id=1,
        distance_m=25.0,
        rel_speed_mps=-5.0,   # on se rapproche
        ttc_s=5.0,
        valid=VALID_YES,
    )

    with PerceptionCanTx(channel=args.channel) as tx:
        for i in range(args.count):
            tx.send(test_obj)
            print(f"[{i+1:3d}/{args.count}] {test_obj}")
            time.sleep(0.1)  # 10 Hz pour le test CLI

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())
