# ADAS Virtual ECU & CAN Bus Simulator (SIL)

Simulateur Software-in-the-Loop d'un système ADAS (Forward Collision Warning)
communicant sur bus CAN virtuel SocketCAN (`vcan0`).

## Architecture

| ECU | Langage | Rôle |
|---|---|---|
| Perception | Python | YOLOv8n + estimation distance monoculaire (KITTI) |
| Décision   | C++    | SocketCAN, calcul TTC, FSM, protection E2E |
| Dashboard  | Python | Affichage temps réel des alertes |

## Environnement de dev

- Ubuntu 22.04.5 LTS (VM VirtualBox), noyau 6.8.0
- Module noyau `vcan` + `can-utils` (2020.11.0-1)
- Python 3, C++17, CMake, g++, Git

## Roadmap

- [x] Phase 0.2 — `vcan0` + can-utils + loopback Python
- [ ] Phase 1 — Spécification (REQ, DBC, Architecture)
- [ ] Phase 2 — ECU Perception (KITTI, YOLOv8n, distance)
- [ ] Phase 3 — Encodage/Décodage DBC avec `cantools`
- [ ] Phase 4 — ECU Décision C++ (SocketCAN, TTC, FSM, E2E)
- [ ] Phase 5 — Dashboard IHM
- [ ] Phase 6 — Validation SIL + injection de défauts
- [ ] Phase 7 — Valorisation (README, pitch, LinkedIn)

## Démarrage rapide

```bash
# 1. Créer l'interface CAN virtuelle
bash scripts/setup_vcan.sh

# 2. Vérifier la communication
python3 tests/test_vcan_loopback.py

Auteur

Molka Ammari — Ingénieure junior génie électrique (ENIM 2026)
