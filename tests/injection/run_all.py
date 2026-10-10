#!/usr/bin/env python3
"""
run_all.py — Orchestrateur d'injection de défauts.

Lance tous les tests d'injection en séquence :
    1. CRC corrompu
    2. Compteur figé
    3. Timeout (perte de trame)
    4. Valeurs aberrantes

Produit un rapport final avec les métriques.

Usage :
    python -m tests.injection.run_all [--no-pause]

Prérequis :
    - vcan0 UP
    - Aucun autre émetteur PERC_OBJECT actif (sauf l'ECU Décision qui écoute)
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Callable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import crc_corruption, frozen_counter, out_of_range, timeout


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structure de rapport
# ---------------------------------------------------------------------------

@dataclass
class InjectionTest:
    """Description d'un test d'injection."""
    name: str
    description: str
    func: Callable[..., int]
    args: dict = field(default_factory=dict)


@dataclass
class TestResult:
    """Résultat d'un test."""
    name: str
    success: bool
    duration_s: float
    error: str = ""


# ---------------------------------------------------------------------------
# Définition des tests
# ---------------------------------------------------------------------------

TESTS: list[InjectionTest] = [
    InjectionTest(
        name="CRC corrompu",
        description="Envoie des trames PERC_OBJECT avec bit flip",
        func=crc_corruption.run,
        args={"count": 10, "period_ms": 200, "channel": "vcan0"},
    ),
    InjectionTest(
        name="Compteur figé",
        description="Envoie 20 trames DEC_ALERT avec counter=0",
        func=frozen_counter.run,
        args={"count": 20, "period_ms": 200, "channel": "vcan0"},
    ),
    InjectionTest(
        name="Timeout (perte de trame)",
        description="Alterne burst + silence > 100 ms",
        func=timeout.run,
        args={"cycles": 3, "burst_size": 3, "gap_ms": 500, "channel": "vcan0"},
    ),
    InjectionTest(
        name="Valeurs aberrantes",
        description="Envoie 6 cas limites (valid=False, distance courte, etc.)",
        func=out_of_range.run,
        args={"period_ms": 50, "channel": "vcan0"},
    ),
]


# ---------------------------------------------------------------------------
# Orchestrateur
# ---------------------------------------------------------------------------

def run_all(no_pause: bool) -> int:
    console = Console()
    console.clear()

    console.print(Panel.fit(
        "[bold cyan]ADAS FCW — Validation SIL[/bold cyan]\n"
        "[dim]Injection de défauts — Phase 6[/dim]",
        border_style="cyan",
    ))
    console.print()

    results: list[TestResult] = []

    for i, test in enumerate(TESTS, 1):
        console.rule(f"[bold]Test {i}/{len(TESTS)} — {test.name}[/bold]")
        console.print(f"[dim]{test.description}[/dim]")
        console.print()

        if not no_pause:
            console.print("[yellow]Appuie sur Entrée pour démarrer ce test...[/yellow]")
            input()

        t0 = time.monotonic()
        try:
            rc = test.func(**test.args)
            duration = time.monotonic() - t0
            success = (rc == 0)
            results.append(TestResult(
                name=test.name, success=success, duration_s=duration,
            ))
            console.print(f"[green]✓ Test '{test.name}' terminé en {duration:.1f} s[/green]")
        except Exception as exc:  # noqa: BLE001
            duration = time.monotonic() - t0
            results.append(TestResult(
                name=test.name, success=False,
                duration_s=duration, error=str(exc),
            ))
            console.print(f"[red]✗ Erreur : {exc}[/red]")

        console.print()
        if not no_pause and i < len(TESTS):
            console.print("[yellow]Appuie sur Entrée pour continuer...[/yellow]")
            input()

    # ----- Rapport final -----
    console.rule("[bold]Rapport final[/bold]")

    table = Table(title="Résultats d'injection", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Test", style="bold")
    table.add_column("Résultat", justify="center", width=10)
    table.add_column("Durée", justify="right", width=10)
    table.add_column("Erreur", style="red")

    total_success = 0
    total_time = 0.0
    for i, res in enumerate(results, 1):
        status = "[green]✓ OK[/green]" if res.success else "[red]✗ ÉCHEC[/red]"
        table.add_row(
            str(i), res.name, status,
            f"{res.duration_s:.2f} s",
            res.error[:50],
        )
        if res.success:
            total_success += 1
        total_time += res.duration_s

    console.print(table)
    console.print()
    console.print(f"[bold]Résumé :[/bold] {total_success}/{len(results)} tests réussis "
                  f"en {total_time:.1f} s")
    console.print()

    if total_success == len(results):
        console.print("[bold green]✓ Tous les tests passés[/bold green]")
        return 0
    else:
        console.print(f"[bold red]✗ {len(results) - total_success} test(s) en échec[/bold red]")
        return 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Orchestrateur d'injection de défauts (Phase 6)",
    )
    parser.add_argument("--no-pause", action="store_true",
                        help="Pas de pause entre les tests")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    try:
        return run_all(no_pause=args.no_pause)
    except KeyboardInterrupt:
        print("\nArrêt demandé.")
        return 130


if __name__ == "__main__":
    sys.exit(main())

