#!/usr/bin/env python3
"""
distance.py — Estimation de distance monoculaire pour l'ECU Perception.

Méthode : relation de similitude (pinhole camera model).

    Z = (f_y * H_real) / h_bbox

Avec :
    - Z       : distance estimée en mètres
    - f_y     : focale verticale en pixels (issue de la calibration caméra)
    - H_real  : hauteur réelle de l'objet en mètres (dépend de la classe)
    - h_bbox  : hauteur de la bounding box en pixels

Limites assumées (voir docs/requirements.md §10) :
    - Erreur typique ~15 % sur 10–50 m
    - Suppose l'objet vu de face (pas de biais)
    - Suppose une hauteur réelle connue par classe

Référence : REQ-PER-002
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .detector import Detection


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Paramètres de calibration par défaut
# ---------------------------------------------------------------------------

# Dataset KITTI — caméra gauche (image_2)
# Résolution native : 1242 x 375 px
# Focale issue de la matrice P (projection matrix) :
#   f_x = 721.5377 px
#   f_y = 721.5377 px (approximée, KITTI ne donne pas f_y séparément)
KITTI_IMG_WIDTH = 1242
KITTI_IMG_HEIGHT = 375
KITTI_FOCAL_Y_PX = 721.5377

# Hauteurs réelles typiques (en mètres) par classe COCO
# Sources : dimensions moyennes constructeurs + standards FCW
REAL_HEIGHTS_M = {
    "car": 1.50,       # berline moyenne
    "truck": 3.50,     # poids lourd
    "bus": 3.20,       # bus urbain
    "person": 1.70,    # piéton adulte
}


# ---------------------------------------------------------------------------
# Structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DistanceEstimate:
    """Estimation de distance pour une détection."""
    class_name: str
    bbox_height_px: int
    real_height_m: float
    focal_y_px: float
    distance_m: float

    def __str__(self) -> str:
        return (
            f"{self.class_name:6s} "
            f"d={self.distance_m:6.2f} m "
            f"(h_bbox={self.bbox_height_px}px, H_real={self.real_height_m}m)"
        )


# ---------------------------------------------------------------------------
# Estimateur
# ---------------------------------------------------------------------------

class MonocularDistanceEstimator:
    """
    Estime la distance d'un objet détecté à partir de la hauteur de sa bbox.

    Suppose une caméra unique calibrée (focale connue). Les hauteurs réelles
    par classe sont paramétrables.
    """

    def __init__(
        self,
        focal_y_px: float = KITTI_FOCAL_Y_PX,
        real_heights_m: dict[str, float] | None = None,
        min_bbox_height_px: int = 20,
    ) -> None:
        """
        Args:
            focal_y_px: focale verticale en pixels (calibration caméra)
            real_heights_m: hauteurs réelles par classe (override des défauts)
            min_bbox_height_px: seuil minimum de hauteur de bbox pour
                considérer l'estimation valide (évite les divisions par ~0)
        """
        self.focal_y_px = focal_y_px
        self.real_heights_m = real_heights_m or REAL_HEIGHTS_M
        self.min_bbox_height_px = min_bbox_height_px

        logger.info(
            "Estimateur distance : focale_y=%.2f px, seuil bbox_min=%d px",
            self.focal_y_px,
            self.min_bbox_height_px,
        )

    def estimate(self, detection: Detection) -> DistanceEstimate | None:
        """
        Estime la distance pour une détection donnée.

        Returns:
            DistanceEstimate si la détection est valide, sinon None.
        """
        h_bbox = detection.height

        if h_bbox < self.min_bbox_height_px:
            logger.debug(
                "Bbox trop petite (%d px < %d px), estimation ignorée",
                h_bbox, self.min_bbox_height_px,
            )
            return None

        real_h = self.real_heights_m.get(detection.class_name)
        if real_h is None:
            logger.debug(
                "Classe '%s' sans hauteur réelle définie, estimation ignorée",
                detection.class_name,
            )
            return None

        distance_m = (self.focal_y_px * real_h) / h_bbox

        return DistanceEstimate(
            class_name=detection.class_name,
            bbox_height_px=h_bbox,
            real_height_m=real_h,
            focal_y_px=self.focal_y_px,
            distance_m=distance_m,
        )

    def estimate_all(self, detections: list[Detection]) -> list[DistanceEstimate]:
        """Estime la distance pour toutes les détections valides."""
        estimates: list[DistanceEstimate] = []
        for det in detections:
            est = self.estimate(det)
            if est is not None:
                estimates.append(est)
        # Tri par distance croissante (plus proche en premier)
        estimates.sort(key=lambda e: e.distance_m)
        return estimates


# ---------------------------------------------------------------------------
# CLI de test
# ---------------------------------------------------------------------------

def _main() -> int:
    import argparse
    from .detector import VehicleDetector

    parser = argparse.ArgumentParser(
        description="Test : détection YOLO + estimation distance monoculaire",
    )
    parser.add_argument("image", type=Path)
    parser.add_argument(
        "--model",
        type=Path,
        default=Path(__file__).parent / "models" / "yolov8n.pt",
    )
    parser.add_argument("--conf", type=float, default=0.35)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    detector = VehicleDetector(model_path=args.model, conf_threshold=args.conf)
    estimator = MonocularDistanceEstimator()

    detections = detector.detect(args.image)
    estimates = estimator.estimate_all(detections)

    print(f"\n{len(detections)} objet(s) détecté(s), {len(estimates)} estimé(s)\n")
    for est in estimates:
        print(f"  - {est}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())
