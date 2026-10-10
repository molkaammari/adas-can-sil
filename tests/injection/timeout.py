#!/usr/bin/env python3
"""
timeout.py — Injection : perte de trames PERC_OBJECT.

Objectif :
    Simuler une panne de communication de l'ECU Perception en envoyant
    quelques trames valides, puis en s'arrêtant brutalement.

Vérifie que :
    - L'ECU Décision détecte le timeout (> 100 ms sans trame)
    - La FSM passe en FAULT
    - Le Dashboard affiche le timeout

Stratégie :
    1. Envoyer 3 trames PERC_OBJECT valides à 200 ms d'intervalle
    2. S'arrêter brutalement (timeout > 100 ms)
    3. Attendre 1 seconde (l'ECU Décision passe en FAULT)
    4. Envoyer 3 nouvelles trames (récupération → STANDBY)
    5. Répéter 3 fois ce cycle

Usage :
    python -m tests.injection.timeout
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from .common import InjectionBus, make_object, sleep_ms


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def run(cycles: int, burst_size: int, gap_ms: int, channel: str) -> int:
    """
    Alterne : burst de trames → silence → burst → silence.

    Args:
        cycles: nombre de cycles burst/silence
        burst_size: nombre de trames par burst
        gap_ms: durée du silence (ms) — doit être > timeout ECU (100 ms)
    """
    with InjectionBus(channel=channel) as inj:
        print(f"Timeouts : {cycles} cycles de {burst_size} trames + {gap_ms} ms de silence\n")

        for cycle in range(1, cycles + 1):
            # ----- Burst -----
            print(f"[Cycle {cycle}/{cycles}] Burst de {burst_size} trames")
            for i in range(burst_size):
                obj = make_object(
                    distance_m=25.0 - i * 0.5,
                    rel_speed_mps=-5.0,
                    obj_id=1,
                )
                inj.send_perc_object(obj)
                sleep_ms(100)

            # ----- Silence (timeout) -----
            print(f"[Cycle {cycle}/{cycles}] Silence de {gap_ms} ms (timeout attendu)")
            sleep_ms(gap_ms)

        print("\nFin d'injection.")
        return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Injection : perte de trames (timeout)",
    )
    parser.add_argument("--cycles", type=int, default=3,
                        help="Nombre de cycles burst/silence (défaut : 3)")
    parser.add_argument("--burst-size", type=int, default=3,
                        help="Trames par burst (défaut : 3)")
    parser.add_argument("--gap-ms", type=int, default=500,
                        help="Durée du silence en ms (défaut : 500, > timeout 100 ms)")
    parser.add_argument("--channel", default="vcan0",
                        help="Interface CAN (défaut : vcan0)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    return run(args.cycles, args.burst_size, args.gap_ms, args.channel)


if __name__ == "__main__":
    sys.exit(main())

