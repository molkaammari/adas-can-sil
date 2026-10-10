#!/usr/bin/env python3
"""
crc_corruption.py — Injection de trames PERC_OBJECT corrompues.

Objectif :
    Envoyer des trames PERC_OBJECT dont 1 bit est corrompu, pour vérifier
    que l'ECU Décision détecte l'anomalie (bit flip → CRC différent).

Note :
    Le CRC E2E de DEC_ALERT est calculé côté C++, donc corrompre le payload
    d'entrée n'affecte pas directement le CRC de sortie.
    Mais ce test vérifie que l'ECU Décision **rejette** les trames invalides
    et que la FSM finit par passer en FAULT par manque de trames valides.

Usage :
    python -m tests.injection.crc_corruption [--count 20]
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from .common import InjectionBus, make_object, sleep_ms


logger = logging.getLogger(__name__)


def run(count: int, period_ms: int, channel: str) -> int:
    """Envoie `count` trames corrompues."""
    with InjectionBus(channel=channel) as inj:
        print(f"Envoi de {count} trames corrompues (période {period_ms} ms)\n")

        for i in range(count):
            obj = make_object(
                distance_m=25.0 - i * 0.5,
                rel_speed_mps=-5.0,
                obj_id=1,
            )
            inj.send_perc_object(obj, corrupt=True)

            if (i + 1) % 5 == 0:
                print(f"  [{i+1:3d}/{count}] corruption envoyée")

            sleep_ms(period_ms)

    print("\nFin d'injection.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Injection de trames PERC_OBJECT corrompues",
    )
    parser.add_argument("--count", type=int, default=20,
                        help="Nombre de trames corrompues (défaut : 20)")
    parser.add_argument("--period-ms", type=int, default=200,
                        help="Période entre trames en ms (défaut : 200)")
    parser.add_argument("--channel", default="vcan0",
                        help="Interface CAN (défaut : vcan0)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    try:
        return run(args.count, args.period_ms, args.channel)
    except KeyboardInterrupt:
        print("\nArrêt demandé.")
        return 0


if __name__ == "__main__":
    sys.exit(main())

