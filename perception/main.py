#!/usr/bin/env python3
"""
main.py — Orchestrateur de l'ECU Perception (ADAS FCW SIL).

Rôle :
    Enchaîne les 3 étapes du pipeline Perception :
        1. Détection YOLOv8n          (detector.py)
        2. Estimation distance        (distance.py)
        3. Émission CAN PERC_OBJECT   (can_tx.py)

Utilisation :
    # Une image
    python -m perception.main --image perception/data/samples/bus.jpg

    # Un dossier d'images
    python -m perception.main --folder perception/data/samples/

    # Sans émission CAN (dry-run)
    python -m perception.main --image bus.jpg --no-can

Références : REQ-PER-001 à 005, REQ-CAN-001 à 004
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Iterable, List, Optional

from .can_tx import PerceptionCanTx, PerceivedObject, build_perceived_object
from .detector import VehicleDetector
from .distance import MonocularDistanceEstimator


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = Path(__file__).parent / "models" / "yolov8n.pt"
DEFAULT_SAMPLES = Path(__file__).parent / "data" / "samples"
SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".bmp"}

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class PerceptionPipeline:
    """Pipeline complet : image → détection → distance → CAN."""

    def __init__(
        self,
        model_path: Path = DEFAULT_MODEL,
        conf_threshold: float = 0.35,
        can_channel: str = "vcan0",
        enable_can: bool = True,
    ) -> None:
        self.detector = VehicleDetector(
            model_path=model_path,
            conf_threshold=conf_threshold,
        )
        self.estimator = MonocularDistanceEstimator()

        self.can_tx: Optional[PerceptionCanTx] = None
        self.enable_can = enable_can
        if enable_can:
            self.can_tx = PerceptionCanTx(channel=can_channel)

        self._obj_id_counter = 0

    # ------------------------------------------------------------------

    def process_image(self, image_path: Path) -> List[PerceivedObject]:
        """Traite une image : détection + distance + (optionnel) émission CAN."""
        logger.info("Traitement : %s", image_path.name)

        detections = self.detector.detect(image_path)
        if not detections:
            logger.info("  → aucun véhicule détecté")
            return []

        estimates = self.estimator.estimate_all(detections)
        if not estimates:
            logger.info("  → aucune estimation de distance valide")
            return []

        perceived: List[PerceivedObject] = []
        for est in estimates:
            # Note : dans cette version, on n'a pas d'historique temporel,
            # donc rel_speed et ttc sont mis à 0 (valeurs par défaut).
            # Ils seront calculés en Phase 2.7+ à partir de plusieurs frames.
            self._obj_id_counter = (self._obj_id_counter + 1) % 256
            obj = build_perceived_object(
                detection=None,  # type: ignore[arg-type]
                estimate=est,
                rel_speed_mps=0.0,
                ttc_s=0.0,
                obj_id=self._obj_id_counter,
            )
            perceived.append(obj)

            if self.can_tx is not None:
                self.can_tx.send(obj)

        logger.info("  → %d objet(s) traité(s)", len(perceived))
        return perceived

    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        if self.can_tx is not None:
            self.can_tx.shutdown()

    def __enter__(self) -> "PerceptionPipeline":
        return self

    def __exit__(self, *exc_info) -> None:
        self.shutdown()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_images(path: Path) -> List[Path]:
    """Retourne la liste des images à traiter (fichier ou dossier)."""
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(
            p for p in path.iterdir()
            if p.suffix.lower() in SUPPORTED_EXT and not p.stem.endswith("_annotated")
        )
    raise FileNotFoundError(f"Chemin introuvable : {path}")


def _print_summary(objs: Iterable[PerceivedObject]) -> None:
    objs = list(objs)
    print(f"\n  {len(objs)} objet(s) émis :")
    for obj in objs:
        print(f"    {obj}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ECU Perception — pipeline complet (image → CAN)",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=Path, help="Image unique à traiter")
    group.add_argument("--folder", type=Path, help="Dossier d'images")

    parser.add_argument(
        "--model", type=Path, default=DEFAULT_MODEL,
        help=f"Chemin du modèle YOLO (défaut : {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--conf", type=float, default=0.35,
        help="Seuil de confiance YOLO (défaut : 0.35)",
    )
    parser.add_argument(
        "--channel", default="vcan0",
        help="Interface SocketCAN (défaut : vcan0)",
    )
    parser.add_argument(
        "--no-can", action="store_true",
        help="Désactive l'émission CAN (dry-run)",
    )
    parser.add_argument(
        "--fps", type=float, default=0.0,
        help="Pause entre images en secondes (0 = pas de pause)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Logs détaillés (DEBUG)",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    source = args.image or args.folder
    try:
        images = _collect_images(source)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2

    if not images:
        logger.warning("Aucune image trouvée dans %s", source)
        return 0

    logger.info("Pipeline démarrage : %d image(s) à traiter", len(images))

    total_objs: List[PerceivedObject] = []
    try:
        with PerceptionPipeline(
            model_path=args.model,
            conf_threshold=args.conf,
            can_channel=args.channel,
            enable_can=not args.no_can,
        ) as pipeline:
            t0 = time.monotonic()
            for img in images:
                objs = pipeline.process_image(img)
                total_objs.extend(objs)
                if args.fps > 0:
                    time.sleep(1.0 / args.fps)
            elapsed = time.monotonic() - t0
    except Exception as exc:  # noqa: BLE001 — CLI : catch global
        logger.exception("Erreur pendant le pipeline : %s", exc)
        return 1

    logger.info(
        "Pipeline terminé : %d image(s), %d objet(s) émis, %.2f s",
        len(images), len(total_objs), elapsed,
    )
    _print_summary(total_objs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
