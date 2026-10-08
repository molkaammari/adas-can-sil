#!/usr/bin/env python3
"""
detector.py — Détecteur d'objets pour l'ECU Perception (ADAS FCW SIL).

Responsabilité unique :
    Charger YOLOv8n, détecter les véhicules (car / truck / bus) sur une image,
    et retourner une liste d'objets structurés.

Ne fait PAS :
    - L'estimation de distance  (voir distance.py)
    - L'émission CAN            (voir can_tx.py)

Référence : REQ-PER-001, REQ-PER-005 (docs/requirements.md)
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import cv2
from ultralytics import YOLO


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Classes COCO pertinentes pour un FCW (Forward Collision Warning)
# 2 = car, 5 = bus, 7 = truck
RELEVANT_CLASSES = {2, 5, 7}

DEFAULT_MODEL_PATH = Path(__file__).parent / "models" / "yolov8n.pt"
DEFAULT_CONF_THRESHOLD = 0.35
DEFAULT_IMG_SIZE = 640

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structures de données
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Detection:
    """Un objet détecté dans une image."""
    class_id: int
    class_name: str
    confidence: float
    # Bounding box en pixels : (x1, y1) coin haut-gauche, (x2, y2) coin bas-droit
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2.0

    def __str__(self) -> str:
        return (
            f"{self.class_name:6s} conf={self.confidence:.2f} "
            f"bbox=({self.x1},{self.y1})-({self.x2},{self.y2}) "
            f"[{self.width}x{self.height}]"
        )


# ---------------------------------------------------------------------------
# Détecteur
# ---------------------------------------------------------------------------

class VehicleDetector:
    """Wrapper autour de YOLOv8n pour la détection de véhicules."""

    def __init__(
        self,
        model_path: Path = DEFAULT_MODEL_PATH,
        conf_threshold: float = DEFAULT_CONF_THRESHOLD,
        img_size: int = DEFAULT_IMG_SIZE,
    ) -> None:
        if not model_path.exists():
            raise FileNotFoundError(
                f"Modèle introuvable : {model_path}\n"
                f"Téléchargez-le avec : python -c \"from ultralytics import YOLO; YOLO('yolov8n.pt')\""
            )

        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.img_size = img_size

        logger.info("Chargement du modèle YOLO : %s", model_path)
        self.model = YOLO(str(model_path))
        logger.info("Modèle chargé. Classes COCO : %d", len(self.model.names))

    def detect(self, image_path: Path) -> List[Detection]:
        """
        Détecte les véhicules dans une image.

        Args:
            image_path: chemin vers l'image (jpg, png, etc.)

        Returns:
            Liste de Detection (uniquement car / bus / truck), triée
            par ordre décroissant de confiance.
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image introuvable : {image_path}")

        # Inférence YOLO
        results = self.model.predict(
            source=str(image_path),
            conf=self.conf_threshold,
            imgsz=self.img_size,
            verbose=False,
        )

        if not results:
            logger.warning("Aucun résultat YOLO pour %s", image_path)
            return []

        result = results[0]
        detections: List[Detection] = []

        for box in result.boxes:
            cls_id = int(box.cls[0])
            if cls_id not in RELEVANT_CLASSES:
                continue

            x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
            detections.append(
                Detection(
                    class_id=cls_id,
                    class_name=self.model.names[cls_id],
                    confidence=float(box.conf[0]),
                    x1=x1, y1=y1, x2=x2, y2=y2,
                )
            )

        # Tri par confiance décroissante
        detections.sort(key=lambda d: d.confidence, reverse=True)
        logger.info(
            "Image %s : %d véhicule(s) détecté(s) sur %d objet(s) total",
            image_path.name, len(detections), len(result.boxes),
        )
        return detections

    def annotate(self, image_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Sauvegarde une version annotée de l'image (bounding boxes dessinées).

        Args:
            image_path: image source
            output_path: chemin de sortie (par défaut : à côté, suffixe '_annotated')

        Returns:
            Chemin de l'image sauvegardée.
        """
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Impossible de lire l'image : {image_path}")

        detections = self.detect(image_path)

        for det in detections:
            color = (0, 255, 0)  # vert BGR
            cv2.rectangle(img, (det.x1, det.y1), (det.x2, det.y2), color, 2)
            label = f"{det.class_name} {det.confidence:.2f}"
            cv2.putText(
                img, label, (det.x1, det.y1 - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
            )

        if output_path is None:
            output_path = image_path.with_name(image_path.stem + "_annotated.jpg")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), img)
        logger.info("Image annotée sauvegardée : %s", output_path)
        return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Détecteur de véhicules YOLOv8n — ECU Perception ADAS FCW",
    )
    parser.add_argument(
        "image",
        type=Path,
        help="Chemin vers l'image à analyser",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help=f"Chemin du modèle YOLO (défaut : {DEFAULT_MODEL_PATH})",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=DEFAULT_CONF_THRESHOLD,
        help=f"Seuil de confiance (défaut : {DEFAULT_CONF_THRESHOLD})",
    )
    parser.add_argument(
        "--annotate",
        action="store_true",
        help="Sauvegarder une version annotée de l'image",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    try:
        detector = VehicleDetector(
            model_path=args.model,
            conf_threshold=args.conf,
        )
        detections = detector.detect(args.image)

        if not detections:
            print("Aucun véhicule détecté.")
        else:
            print(f"{len(detections)} véhicule(s) détecté(s) :")
            for det in detections:
                print(f"  - {det}")

        if args.annotate:
            detector.annotate(args.image)

        return 0

    except FileNotFoundError as exc:
        logger.error("Fichier manquant : %s", exc)
        return 2
    except Exception as exc:  # noqa: BLE001 — CLI : on veut tout attraper
        logger.exception("Erreur inattendue : %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())

