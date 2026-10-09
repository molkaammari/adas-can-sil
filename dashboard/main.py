#!/usr/bin/env python3
"""
main.py — Dashboard temps réel ADAS FCW.

Interface console (rich) qui affiche en direct l'état du système ADAS :
    - Niveau d'alerte (STANDBY / WARNING / BRAKE / FAULT)
    - TTC courant
    - État E2E (compteur, CRC)
    - Statistiques (trames, erreurs, uptime)

Usage :
    python -m dashboard.main [--channel vcan0]

Références : REQ-DEC-006, REQ-DEC-007, REQ-E2E-003
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .receiver import CanReceiver, COMM_TIMEOUT_S, HB_TIMEOUT_S


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

REFRESH_HZ = 10
REFRESH_S = 1.0 / REFRESH_HZ

# Couleurs par niveau d'alerte
LEVEL_COLORS = {
    "OFF":     "bright_black",
    "STANDBY": "green",
    "WARNING": "yellow",
    "BRAKE":   "bold red",
    "FAULT":   "magenta",
    "UNKNOWN": "white",
}


# ---------------------------------------------------------------------------
# Helpers d'affichage
# ---------------------------------------------------------------------------

def _format_ttc(ttc_s: float) -> str:
    """Formate un TTC lisible."""
    if ttc_s <= 0.0 or ttc_s > 100.0:
        return "∞"
    return f"{ttc_s:.2f} s"


def _format_time(seconds: float) -> str:
    """Formate un temps en mm:ss."""
    if seconds == float("inf"):
        return "—"
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


# ---------------------------------------------------------------------------
# Construction de l'affichage
# ---------------------------------------------------------------------------

def build_header() -> Panel:
    """Bandeau supérieur."""
    title = Text()
    title.append("ADAS Forward Collision Warning", style="bold cyan")
    title.append("  |  ")
    title.append("Dashboard v0.1.0", style="dim")

    return Panel(
        Align.center(title),
        border_style="cyan",
        padding=(0, 1),
    )


def build_main_panel(receiver: CanReceiver) -> Panel:
    """Panel principal : état d'alerte."""
    st = receiver.state
    alert = st.last_alert

    if alert is None:
        content = Text("En attente de trames...", style="dim italic")
        border = "grey50"
        return Panel(
            Align.center(content),
            title="[bold]Etat[/bold]",
            border_style=border,
            padding=(1, 2),
        )

    color = LEVEL_COLORS.get(alert.level_name, "white")
    level_text = Text(alert.level_name, style=f"bold {color}")

    # Construction du contenu principal
    lines = []

    # Ligne 1 : état
    state_line = Text()
    state_line.append("  ÉTAT     :  ", style="bold")
    state_line.append_text(level_text)
    lines.append(state_line)

    # Ligne 2 : TTC
    ttc_line = Text()
    ttc_line.append("  TTC      :  ", style="bold")
    ttc_line.append(_format_ttc(alert.ttc_s), style=color)
    lines.append(ttc_line)

    # Ligne 3 : niveau numérique
    lvl_line = Text()
    lvl_line.append("  Level    :  ", style="bold")
    lvl_line.append(f"{alert.alert_level} / 4", style="dim")
    lines.append(lvl_line)

    # Séparateur
    lines.append(Text(""))

    # Ligne 4 : âge de la trame
    age_s = st.time_since_last_alert_s()
    age_line = Text()
    age_line.append("  Dernière trame  :  ", style="bold")
    if age_s < COMM_TIMEOUT_S:
        age_line.append(f"{int(age_s * 1000):4d} ms", style="green")
    else:
        age_line.append(f"{int(age_s * 1000):4d} ms  [TIMEOUT]", style="bold red")
    lines.append(age_line)

    content = Group(*lines)

    return Panel(
        content,
        title=f"[bold]Etat courant[/bold]",
        border_style=color,
        padding=(1, 1),
    )


def build_e2e_panel(receiver: CanReceiver) -> Panel:
    """Panel E2E : compteur, CRC, heartbeat."""
    st = receiver.state

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold", no_wrap=True)
    table.add_column(no_wrap=True)

    # Compteur E2E
    counter = st.last_counter if st.last_counter >= 0 else "—"
    counter_style = "green" if st.counter_jumps == 0 else "yellow"
    table.add_row("Compteur E2E", f"[{counter_style}]{counter} / 15[/{counter_style}]")

    # Sauts détectés
    jumps_style = "green" if st.counter_jumps == 0 else "bold red"
    table.add_row("Sauts compteur", f"[{jumps_style}]{st.counter_jumps}[/{jumps_style}]")

    # Heartbeat
    if st.last_hb is not None:
        hb_age = st.time_since_last_hb_s()
        hb_style = "green" if hb_age < HB_TIMEOUT_S else "bold red"
        table.add_row(
            "Heartbeat",
            f"[{hb_style}]alive={st.last_hb.alive_ctr}, age={int(hb_age*1000)} ms[/{hb_style}]",
        )
    else:
        table.add_row("Heartbeat", "[dim]—[/dim]")

    return Panel(
        table,
        title="[bold]Vérification E2E[/bold]",
        border_style="blue",
        padding=(1, 2),
    )


def build_stats_panel(receiver: CanReceiver) -> Panel:
    """Panel statistiques."""
    st = receiver.state

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold", no_wrap=True)
    table.add_column(justify="right", no_wrap=True)

    table.add_row("Total trames", f"{st.frames_total}")
    table.add_row("  DEC_ALERT (0x200)", f"{st.frames_alert}")
    table.add_row("  DEC_HB    (0x201)", f"{st.frames_hb}")
    table.add_row("  ID inconnus", f"{st.frames_unknown_id}")
    table.add_row("  Erreurs décodage", f"{st.frames_decode_errors}")
    table.add_row("", "")
    table.add_row("Uptime", _format_time(st.uptime_s()))

    return Panel(
        table,
        title="[bold]Statistiques[/bold]",
        border_style="magenta",
        padding=(1, 2),
    )


def build_footer() -> Text:
    """Pied de page."""
    txt = Text()
    txt.append("Ctrl+C", style="bold yellow")
    txt.append(" pour quitter   ", style="dim")
    txt.append("|", style="dim")
    txt.append("   Fréquence rafraîchissement : ", style="dim")
    txt.append(f"{REFRESH_HZ} Hz", style="cyan")
    return Align.center(txt)


def build_dashboard(receiver: CanReceiver) -> Group:
    """Assemble le dashboard complet."""
    return Group(
        build_header(),
        build_main_panel(receiver),
        build_e2e_panel(receiver),
        build_stats_panel(receiver),
        build_footer(),
    )


# ---------------------------------------------------------------------------
# Boucle principale
# ---------------------------------------------------------------------------

def run_dashboard(receiver: CanReceiver) -> None:
    """Lance la boucle d'affichage live."""
    console = Console()

    with Live(
        build_dashboard(receiver),
        console=console,
        refresh_per_second=REFRESH_HZ,
        screen=True,
    ) as live:
        try:
            while True:
                # Traiter plusieurs trames par cycle pour ne pas rater
                for _ in range(20):
                    receiver.process_one_frame()

                receiver.state.update_timeouts()
                live.update(build_dashboard(receiver))

                time.sleep(REFRESH_S)

        except KeyboardInterrupt:
            pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dashboard ADAS FCW — affichage temps réel",
    )
    parser.add_argument(
        "--channel", default="vcan0",
        help="Interface SocketCAN (défaut : vcan0)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Logs détaillés",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    try:
        receiver = CanReceiver(channel=args.channel)
    except RuntimeError as exc:
        print(f"[ERREUR] {exc}", file=sys.stderr)
        return 1

    try:
        run_dashboard(receiver)
    finally:
        receiver.close()

    # Affichage final des stats (après Ctrl+C)
    console = Console()
    st = receiver.state
    console.print()
    console.print("[bold cyan]Session terminée[/bold cyan]")
    console.print(f"  Total trames : {st.frames_total}")
    console.print(f"  Uptime       : {st.uptime_s():.2f} s")

    return 0


if __name__ == "__main__":
    sys.exit(main())

