#!/usr/bin/env python3
"""
receiver.py — Réception CAN + gestion d'état pour le Dashboard.

Responsabilité unique :
    - Ouvrir un socket CAN sur vcan0
    - Recevoir les trames DEC_ALERT (0x200) et DEC_HB (0x201)
    - Décoder via DashboardDecoder
    - Maintenir un état agrégé (dernière alerte, dernier HB, stats)
    - Détecter les timeouts de communication

Ne fait PAS :
    - L'affichage (voir main.py)

Références : REQ-DEC-006, REQ-DEC-007, REQ-E2E-003
"""

from __future__ import annotations

import logging
import socket
import struct
import time
from dataclasses import dataclass, field
from typing import Optional

from .decoder import (
    Alert,
    DashboardDecoder,
    Heartbeat,
    CAN_ID_DEC_ALERT,
    CAN_ID_DEC_HB,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

DEFAULT_CHANNEL = "vcan0"

# Timeout : au-delà, on considère la communication perdue
COMM_TIMEOUT_S = 0.300

# Timeout E2E heartbeat (REQ-E2E-004)
HB_TIMEOUT_S = 0.500


# ---------------------------------------------------------------------------
# État agrégé
# ---------------------------------------------------------------------------

@dataclass
class DashboardState:
    """État courant du dashboard, mis à jour à chaque trame."""
    # Dernières valeurs décodées
    last_alert: Optional[Alert] = None
    last_hb: Optional[Heartbeat] = None

    # Timestamps (monotonic)
    last_alert_ts: float = 0.0
    last_hb_ts: float = 0.0
    started_ts: float = field(default_factory=time.monotonic)

    # Statistiques
    frames_total: int = 0
    frames_alert: int = 0
    frames_hb: int = 0
    frames_decode_errors: int = 0
    frames_unknown_id: int = 0

    # Détection E2E
    last_counter: int = -1
    counter_jumps: int = 0          # sauts anormaux
    crc_errors: int = 0             # (à faire : recalcul CRC)

    # Timeouts détectés
    alert_timeout: bool = False
    hb_timeout: bool = False

    # ----- Méthodes -----

    def uptime_s(self) -> float:
        return time.monotonic() - self.started_ts

    def time_since_last_alert_s(self) -> float:
        if self.last_alert_ts == 0.0:
            return float("inf")
        return time.monotonic() - self.last_alert_ts

    def time_since_last_hb_s(self) -> float:
        if self.last_hb_ts == 0.0:
            return float("inf")
        return time.monotonic() - self.last_hb_ts

    def update_timeouts(self) -> None:
        """Recalcule les flags de timeout selon les timestamps."""
        self.alert_timeout = self.time_since_last_alert_s() > COMM_TIMEOUT_S
        self.hb_timeout = self.time_since_last_hb_s() > HB_TIMEOUT_S


# ---------------------------------------------------------------------------
# Récepteur CAN
# ---------------------------------------------------------------------------

class CanReceiver:
    """Récepteur SocketCAN pour le dashboard."""

    def __init__(
        self,
        channel: str = DEFAULT_CHANNEL,
        decoder: Optional[DashboardDecoder] = None,
    ) -> None:
        self.channel = channel
        self.decoder = decoder or DashboardDecoder()
        self.state = DashboardState()

        # Ouvrir le socket CAN
        try:
            self.sock = socket.socket(
                socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW
            )
            self.sock.bind((channel,))
            self.sock.settimeout(0.1)  # non bloquant pour la boucle
            logger.info("Socket CAN ouvert sur '%s'", channel)
        except OSError as exc:
            raise RuntimeError(
                f"Impossible d'ouvrir '{channel}'. "
                f"Avez-vous lancé scripts/setup_vcan.sh ? "
                f"Détail : {exc}"
            ) from exc

    def close(self) -> None:
        try:
            self.sock.close()
            logger.info("Socket CAN fermé")
        except OSError:
            pass

    # ------------------------------------------------------------------

    def process_one_frame(self) -> bool:
        """
        Tente de recevoir et traiter UNE trame.

        Returns:
            True si une trame a été traitée, False sinon (timeout).
        """
        try:
            raw = self.sock.recv(16)
        except socket.timeout:
            return False
        except OSError as exc:
            logger.error("Erreur de réception : %s", exc)
            return False

        # Format d'une trame CAN : can_id (4 octets LE) + dlc (1 octet) + data (8 octets)
        # Pour plus de détails : <linux/can.h>
        if len(raw) < 8:
            logger.warning("Trame CAN trop courte (%d octets)", len(raw))
            return False

        can_id, can_dlc = struct.unpack("<IB3x", raw[:8])[:2]
        data = raw[8 : 8 + can_dlc]

        self.state.frames_total += 1

        if can_id == CAN_ID_DEC_ALERT:
            self._handle_alert(data)
        elif can_id == CAN_ID_DEC_HB:
            self._handle_hb(data)
        else:
            self.state.frames_unknown_id += 1

        return True

    # ------------------------------------------------------------------

    def _handle_alert(self, data: bytes) -> None:
        alert = self.decoder.decode_alert(data)
        if alert is None:
            self.state.frames_decode_errors += 1
            return

        # Détection E2E : saut de compteur
        if self.state.last_counter >= 0:
            expected = (self.state.last_counter + 1) % 16
            if alert.counter != expected:
                self.state.counter_jumps += 1
                logger.warning(
                    "Compteur E2E sauté : attendu=%d, reçu=%d",
                    expected, alert.counter,
                )

        self.state.last_counter = alert.counter
        self.state.last_alert = alert
        self.state.last_alert_ts = time.monotonic()
        self.state.frames_alert += 1

    def _handle_hb(self, data: bytes) -> None:
        hb = self.decoder.decode_hb(data)
        if hb is None:
            self.state.frames_decode_errors += 1
            return

        self.state.last_hb = hb
        self.state.last_hb_ts = time.monotonic()
        self.state.frames_hb += 1


# ---------------------------------------------------------------------------
# CLI de test
# ---------------------------------------------------------------------------

def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Test de réception CAN (mode texte, sans affichage riche)",
    )
    parser.add_argument(
        "--channel", default=DEFAULT_CHANNEL,
        help=f"Interface CAN (défaut : {DEFAULT_CHANNEL})",
    )
    parser.add_argument(
        "--duration", type=float, default=10.0,
        help="Durée d'écoute en secondes (défaut : 10)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    receiver = CanReceiver(channel=args.channel)

    print(f"Écoute sur {args.channel} pendant {args.duration:.1f} s...")
    print("Ctrl+C pour arrêter.\n")

    try:
        t0 = time.monotonic()
        while time.monotonic() - t0 < args.duration:
            got = receiver.process_one_frame()
            receiver.state.update_timeouts()

            if got:
                alert = receiver.state.last_alert
                hb = receiver.state.last_hb
                if alert:
                    print(
                        f"[ALERT] level={alert.level_name:8s} "
                        f"ttc={alert.ttc_s:5.2f}s "
                        f"counter={alert.counter:2d}"
                    )
                if hb:
                    print(f"[HB   ] alive={hb.alive_ctr:3d} state={hb.state}")

    except KeyboardInterrupt:
        print("\nArrêt demandé.")

    finally:
        receiver.close()
        st = receiver.state
        print()
        print("=== Statistiques ===")
        print(f"Total trames      : {st.frames_total}")
        print(f"  DEC_ALERT       : {st.frames_alert}")
        print(f"  DEC_HB          : {st.frames_hb}")
        print(f"  ID inconnus     : {st.frames_unknown_id}")
        print(f"  Erreurs décodage: {st.frames_decode_errors}")
        print(f"Sauts compteur    : {st.counter_jumps}")
        print(f"Uptime            : {st.uptime_s():.2f} s")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())

