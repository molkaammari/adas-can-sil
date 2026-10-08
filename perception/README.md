# ECU Perception

Détection de véhicules + estimation de distance monoculaire + émission CAN.

## Structure

| Fichier | Rôle |
|---|---|
| `detector.py` | Détection YOLOv8n (classes car/bus/truck) |
| `distance.py` | Estimation de distance par hauteur de bbox |
| `can_tx.py` | Encodage DBC + émission SocketCAN |
| `main.py` | Orchestrateur (image → détection → distance → CAN) |
| `models/` | Modèle YOLOv8n (`yolov8n.pt`) — non versionné |
| `data/samples/` | Images de test |

## Usage

### Prérequis

```bash
# Activer le venv
cd ~/adas-can
source .venv/bin/activate

# Charger vcan0
bash scripts/setup_vcan.sh
