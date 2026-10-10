#!/usr/bin/env python3
"""
frozen_counter.py — Injection de trames DEC_ALERT avec compteur figé.

Objectif :
    Vérifier que le Dashboard Python détecte un compteur E2E qui n'incrémente pas.
    Normalement, le compteur doit s'incrémenter de 1 mod 16 à chaque trame.
    Ici, on le force à rester constant.

Stratégie :
    - On envoie des trames DEC_ALERT valides (bon format, bon CRC calculé)
    - Mais le compteur reste à 0 (au lieu de 0,1,2,3...)
    - Le Dashboard doit détecter les sauts et comptabiliser les erreurs

Note :
    L'ECU Décision C++ ne lit pas DEC_ALERT, il l'émet.
    Ce test ne perturbe donc PAS l'ECU Décision, seulement le Dashboard.

Usage :
    python -m tests.injection.frozen_counter --count 10
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

import can
import cantools

from perception.can_tx import DEFAULT_DBC_PATH


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

CAN_ID_DEC_ALERT = 0x200
CAN_ID_DEC_HB = 0x201
DEFAULT_CHANNEL = "vcan0"


# ---------------------------------------------------------------------------
# Encodage
# ---------------------------------------------------------------------------

def crc8(data: bytes) -> int:
    """CRC8 poly 0x1D (identique au C++)."""
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x1D) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc ^ 0xFF


def build_dec_alert(
    level: int,
    ttc_s: float,
    counter: int,
    db: cantools.database.can.Database,
) -> bytes:
    """
    Construit un payload DEC_ALERT (4 octets) avec CRC E2E correct.

    Layout :
        octet 0 : level (bits 0-3) | ttc bits bas (bits 4-7)
        octet 1 : ttc bits hauts (8 bits)
        octet 2 : counter (bits 0-3) | 0 (bits 4-7)
        octet 3 : crc (sur les 3 premiers octets)
    """
    # ttc en centisecondes
    ttc_raw = int(round(ttc_s / 0.01))
    ttc_raw &= 0x0FFF  # 12 bits max

    b0 = (level & 0x0F) | ((ttc_raw & 0x0F) << 4)
    b1 = (ttc_raw >> 4) & 0xFF
    b2 = counter & 0x0F
    b3 = 0  # sera remplacé par le CRC

    payload_no_crc = bytes([b0, b1, b2, b3])
    crc = crc8(payload_no_crc[:3])
    return bytes([b0, b1, b2, crc])


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def run(count: int, period_ms: int, channel: str) -> int:
    """Envoie `count` trames avec compteur figé à 0."""
    db = cantools.database.load_file(str(DEFAULT_DBC_PATH))

    try:
        bus = can.interface.Bus(channel=channel, interface="socketcan")
    except OSError as exc:
        raise RuntimeError(f"Ouverture '{channel}' impossible : {exc}") from exc

    print(f"Envoi de {count} trames DEC_ALERT avec compteur FIGÉ à 0")
    print(f"Période : {period_ms} ms\n")

    try:
        for i in range(count):
            payload = build_dec_alert(
                level=1,       # STANDBY
                ttc_s=5.0,
                counter=0,     # ← FIGÉ
                db=db,
            )

            frame = can.Message(
                arbitration_id=CAN_ID_DEC_ALERT,
                data=payload,
                is_extended_id=False,
            )
            bus.send(frame)

            if (i + 1) % 5 == 0:
                print(f"  [{i+1:3d}/{count}] compteur=0 (figé)")

            time.sleep(period_ms / 1000.0)

    except KeyboardInterrupt:
        print("\nArrêt demandé.")

    finally:
        bus.shutdown()
        print("\nFin d'injection.")

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Injection : compteur E2E figé",
    )
    parser.add_argument("--count", type=int, default=20,
                        help="Nombre de trames (défaut : 20)")
    parser.add_argument("--period-ms", type=int, default=200,
                        help="Période (défaut : 200 ms)")
    parser.add_argument("--channel", default=DEFAULT_CHANNEL,
                        help="Interface CAN (défaut : vcan0)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    return run(args.count, args.period_ms, args.channel)


if __name__ == "__main__":
    sys.exit(main())

