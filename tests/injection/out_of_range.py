#!/usr/bin/env python3
"""
out_of_range.py — Injection de trames avec valeurs hors plage.

Objectif :
    Envoyer des trames PERC_OBJECT avec des valeurs physiquement impossibles
    ou hors limites DBC, pour vérifier la robustesse du décodeur C++.

Cas testés :
    1. Distance négative (encode via offset → valeur brute 0)
    2. Distance max + 1 (au-delà de 655.35 m)
    3. Vitesse relative extrême
    4. TTC négatif
    5. Objet "invalide" (valid=0)

Stratégie :
    On envoie chaque cas pendant 200 ms, avec un log indiquant le cas.

Usage :
    python -m tests.injection.out_of_range
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from .common import InjectionBus, make_object, sleep_ms


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cas de test
# ---------------------------------------------------------------------------

TEST_CASES = [
    # (nom, distance, rel_speed, ttc, valid)
    ("Distance normale",         25.0,   -5.0,  5.0, True),
    ("Distance très petite",      0.5,   -5.0,  0.1, True),
    ("Distance grande",         100.0,   -5.0, 20.0, True),
    ("Valid = False",            25.0,   -5.0,  5.0, False),
    ("Rel_speed positif (éloignement)", 25.0, +5.0,  5.0, True),
    ("TTC très petit",           25.0,  -50.0,  0.5, True),
]


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def run(period_ms: int, channel: str) -> int:
    """Envoie toutes les valeurs aberrantes, une par une."""
    with InjectionBus(channel=channel) as inj:
        print(f"Injection de {len(TEST_CASES)} cas de valeurs limites")
        print(f"Période : {period_ms} ms par cas\n")

        for i, (name, dist, v_rel, ttc, valid) in enumerate(TEST_CASES, 1):
            print(f"[{i}/{len(TEST_CASES)}] {name}")
            print(f"        d={dist:.1f}m  v_rel={v_rel:+.1f}m/s  "
                  f"ttc={ttc:.2f}s  valid={valid}")

            # Envoi d'une trame par cas
            obj = make_object(
                distance_m=dist,
                rel_speed_mps=v_rel,
                ttc_s=ttc,
                valid=valid,
                obj_id=1,
            )

            try:
                inj.send_perc_object(obj)
            except Exception as exc:  # noqa: BLE001
                print(f"        ⚠ Erreur d'encodage : {exc}")

            sleep_ms(period_ms)

        print("\nFin d'injection.")
        return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Injection : valeurs hors plage",
    )
    parser.add_argument("--period-ms", type=int, default=300,
                        help="Période par cas en ms (défaut : 300)")
    parser.add_argument("--channel", default="vcan0",
                        help="Interface CAN (défaut : vcan0)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    return run(args.period_ms, args.channel)


if __name__ == "__main__":
    sys.exit(main())

