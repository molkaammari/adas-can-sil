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






















# 🚗 ADAS Forward Collision Warning — Simulateur SIL

> Système ADAS complet simulé en **Software-in-the-Loop** (100 % logiciel) : détection
> de véhicules, calcul du risque de collision, alertes en temps réel sur bus CAN virtuel.

[![Python](https://img.shields.io/badge/Python-3.10-blue)](https://python.org)
[![C++](https://img.shields.io/badge/C++-17-blue)](https://isocpp.org)
[![CMake](https://img.shields.io/badge/CMake-3.22-green)](https://cmake.org)
[![Tests](https://img.shields.io/badge/Tests-99%20passed-brightgreen)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)]()

---

## 📋 Table des matières

- [Présentation](#-présentation)
- [Architecture](#-architecture)
- [Workflow](#-workflow)
- [Prérequis](#-prérequis)
- [Installation](#-installation)
- [Utilisation](#-utilisation)
- [Tests](#-tests)
- [Structure du projet](#-structure-du-projet)
- [Limites assumées](#-limites-assumées)
- [Auteur](#-auteur)

---

## 🎯 Présentation

Ce projet simule **un système ADAS de type Forward Collision Warning (FCW)** :
quand un véhicule s'approche dangereusement d'un obstacle devant lui, le système
alerte le conducteur (ou déclenche un freinage d'urgence).

**Tout est logiciel** — aucun matériel physique n'est requis. C'est ce qu'on
appelle du **SIL (Software-in-the-Loop)** : la méthode utilisée par Bosch,
Continental ou Valeo avant d'embarquer un système sur un vrai véhicule.

### Ce que ça fait

- 📷 **Perception** : détection YOLOv8n + estimation de distance monoculaire
- 🧠 **Décision** : calcul du TTC + machine à états + protection E2E (CRC8)
- 📊 **Dashboard** : affichage temps réel de l'état du système
- 🚌 **Communication** : bus CAN virtuel (`vcan0`) via SocketCAN

---

## 🏗 Architecture

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│  ECU Perception  │       │  ECU Décision    │       │    Dashboard     │
│    (Python)      │──0x100│      (C++)       │──0x200│    (Python)      │
│                  │       │                  │──0x201│                  │
│  YOLOv8n + dist  │       │  FSM + TTC + E2E │       │  rich TUI        │
└──────────────────┘       └──────────────────┘       └──────────────────┘
        │                          │                          │
        └──────────────────────────┴──────────────────────────┘
                                   │
                          Bus CAN vcan0
                        (SocketCAN virtuel)
```

### Messages CAN

| Message | ID | DLC | Cycle | Émetteur |
|---|---|---|---|---|
| `PERC_OBJECT` | 0x100 | 8 | 20 Hz | Perception |
| `DEC_ALERT` | 0x200 | 4 | 20 Hz | Décision |
| `DEC_HB` | 0x201 | 2 | 10 Hz | Décision |

### Machine à états (ECU Décision)

```
         ┌──────────────────────────────────────┐
         ▼                                      │
     ┌───────┐   init   ┌──────────┐  trame  ┌──┴─────┐
     │  OFF  ├─────────►│ STANDBY  ├────────►│WARNING │
     └───────┘          └────┬─────┘  TTC<2s └──┬─────┘
                             │                  │ TTC<1.2s
                             │ timeout          ▼
                             ▼              ┌──────────┐
                        ┌──────────┐        │  BRAKE   │
                        │  FAULT   │◄───────└──────────┘
                        └──────────┘  erreur
```

---

## 🔄 Workflow

```
Image KITTI
    ↓
YOLOv8n (détection)  →  Distance monoculaire  →  Encodage DBC
    ↓
[PERC_OBJECT 0x100]  ────────────►  vcan0
    ↓
Décodage  →  Calcul TTC  →  FSM  →  CRC8 E2E
    ↓
[DEC_ALERT 0x200]  ────────────►  vcan0
    ↓
Dashboard (décodage + affichage temps réel)
```

> Diagrammes détaillés : [`docs/architecture_diagram.md`](docs/architecture_diagram.md) et [`docs/workflow.md`](docs/workflow.md).

---

## ⚙️ Prérequis

- **OS** : Linux (Ubuntu 22.04 recommandé)
- **Python** : 3.10+
- **C++** : g++ 11+, CMake 3.22+
- **Outils CAN** : `can-utils`, module noyau `vcan`
- **Tests** : pytest, GoogleTest (`libgtest-dev`)

### Installation des outils système

```bash
sudo apt update
sudo apt install -y build-essential cmake python3-pip python3-venv \
                    can-utils libgtest-dev
sudo modprobe vcan
```

---

## 🚀 Installation

### 1. Cloner le projet

```bash
git clone https://github.com/molkaammari/adas-can-sil.git
cd adas-can-sil
```

### 2. Créer le venv Python

```bash
python3 -m venv .venv
source .venv/bin/activate

# Installer torch CPU (⚠️ AVANT ultralytics)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### 3. Télécharger le modèle YOLO

```bash
mkdir -p perception/models
cd perception/models
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
cd ../..
```

### 4. Créer le bus CAN virtuel

```bash
bash scripts/setup_vcan.sh
```

### 5. Compiler l'ECU Décision

```bash
cd decision
mkdir -p build && cd build
cmake ..
make
cd ../..
```

---

## 🎮 Utilisation

Trois terminaux nécessaires (un par ECU) :

### Terminal 1 — Dashboard

```bash
cd ~/adas-can
source .venv/bin/activate
python -m dashboard.main
```

### Terminal 2 — ECU Décision (C++)

```bash
cd ~/adas-can/decision/build
./decision_main --duration 120
```

### Terminal 3 — ECU Perception (Python)

```bash
cd ~/adas-can
source .venv/bin/activate
python -m perception.main --image perception/data/samples/bus.jpg
```

**Résultat** : le dashboard affiche l'état du système en temps réel.

---

## 🧪 Tests

### Tests Python (30 tests)

```bash
./run_tests.sh
```

### Tests C++ (69 tests)

```bash
cd decision/build
ctest --output-on-failure
```

### Validation par injection de défauts

```bash
# Terminal 1 : ECU Décision
cd decision/build && ./decision_main --duration 60

# Terminal 2 : orchestrateur d'injection
python -m tests.injection.run_all
```

**Résultat** : 4/4 scénarios validés (CRC corrompu, compteur figé, timeout,
valeurs aberrantes).

### Bilan global

| Suite | Nombre | Résultat |
|---|---|---|
| Python (pytest) | 30 | ✅ 100 % |
| C++ (GoogleTest) | 69 | ✅ 100 % |
| Injection défauts | 4 | ✅ 100 % |
| **Total** | **103** | ✅ **100 %** |

---

## 📂 Structure du projet

```
adas-can-sil/
├── perception/              # ECU Perception (Python)
│   ├── detector.py          #   Détection YOLOv8n
│   ├── distance.py          #   Distance monoculaire
│   ├── can_tx.py            #   Émission CAN (DBC)
│   ├── main.py              #   Orchestrateur
│   └── models/              #   Modèle YOLOv8n (non versionné)
│
├── decision/                # ECU Décision (C++)
│   ├── include/decision/    #   Headers (types, e2e, ttc, fsm, decoder, ...)
│   ├── src/                 #   Implémentations
│   ├── tests/               #   Tests GoogleTest (69)
│   └── CMakeLists.txt
│
├── dashboard/               # Dashboard (Python)
│   ├── decoder.py           #   Décodage DEC_ALERT + DEC_HB
│   ├── receiver.py          #   Réception SocketCAN + stats
│   └── main.py              #   Affichage rich TUI
│
├── shared/dbc/              # Dictionnaire CAN
│   └── adas.dbc             #   3 messages, 11 signaux
│
├── tests/                   # Tests
│   ├── test_dbc.py          #   Contrat DBC (30 tests)
│   ├── test_vcan_loopback.py
│   └── injection/           #   Injection de défauts (4 scénarios)
│
├── scripts/
│   └── setup_vcan.sh        #   Créer vcan0
│
├── docs/                    # Documentation
│   ├── requirements.md      #   REQ-xxx (50+ exigences)
│   ├── architecture.md      #   Architecture détaillée
│   ├── phase0_2_validation.md
│   ├── phase4_validation.md
│   ├── phase5_validation.md
│   ├── phase6_validation.md
│   ├── architecture_diagram.md
│   ├── workflow.md
│   └── videos/
│       └── demo_phase6.mp4  #   Vidéo démo
│
├── requirements.txt
├── pytest.ini
├── run_tests.sh
└── README.md
```

---

## ⚠️ Limites assumées

**Ce projet est un prototype SIL** — il démontre l'architecture et la logique
d'un système ADAS, **pas un produit embarquable**.

| Limite | Impact | Amélioration possible |
|---|---|---|
| Latence YOLO (587 ms) | 1.7 fps vs 30 fps cible | ONNX, quantization |
| Pas d'historique temporel Python | Vitesse relative = 0 | Buffer glissant |
| Distance monoculaire | ~15 % erreur | Fusion radar/LiDAR |
| Bus CAN virtuel | Latence nulle | SocketCAN réel |
| Pas de CRC sur `PERC_OBJECT` | Corruption acceptée | Ajouter au DBC |
| CPU x86 (pas ARM) | Non représentatif | Port Raspberry Pi / Jetson |

### Ce qu'il faudrait pour être un vrai ADAS

- **Flux vidéo continu** (au lieu d'images fixes)
- **Fusion multi-capteurs** : caméra + radar 77 GHz + LiDAR
- **Optimisation** : YOLO ONNX/INT8, cible ARM
- **Redondance** : double canal CAN
- **Certification** : ISO 26262 ASIL-D, MISRA C++, AUTOSAR Classic

---

## 🛠 Stack technique

| Domaine | Outils |
|---|---|
| **Langages** | Python 3.10, C++17 |
| **Protocoles** | SocketCAN, DBC, CAN bus, AUTOSAR E2E |
| **IA** | YOLOv8n, PyTorch (CPU), OpenCV |
| **Build** | CMake 3.22 |
| **Tests** | pytest, GoogleTest |
| **TUI** | rich |
| **VCS** | Git, GitHub |

---

## 👤 Auteur

**Molka Ammari**
Ingénieure junior en génie électrique — ENIM 2026

- 📧 Email : molka.ammari.enim@gmail.com
- 🐙 GitHub : [@molkaammari](https://github.com/molkaammari)
- 🔗 Projet : [adas-can-sil](https://github.com/molkaammari/adas-can-sil)

---

## 📜 License

MIT — voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

**⭐ Si ce projet vous plaît, n'hésitez pas à mettre une étoile !**

