# Architecture — ADAS Forward Collision Warning (SIL)

**Version** : 0.1
**Date** : 2026-10-07
**Auteur** : Molka Ammari
**Statut** : Draft initial

## 1. Vue d'ensemble

Système SIL composé de **3 ECU logiciels** communiquant via **bus CAN virtuel** (`vcan0`).
Chaque ECU est un processus indépendant, ce qui permet de les redémarrer / tester
séparément et de simuler des pannes réalistes.

┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ ECU Perception │ │ ECU Décision │ │ Dashboard │
│ (Python) │ │ (C++) │ │ (Python) │
│ │ │ │ │ │
│ ┌────────────┐ │ │ ┌────────────┐ │ │ ┌────────────┐ │
│ │ YOLOv8n │ │ │ │ Décodeur │ │ │ │ Décodeur │ │
│ │ (CPU) │ │ │ │ cantools │ │ │ │ cantools │ │
│ └─────┬──────┘ │ │ └─────┬──────┘ │ │ └─────┬──────┘ │
│ │ │ │ │ │ │ │ │
│ ┌─────▼──────┐ │ │ ┌─────▼──────┐ │ │ ┌─────▼──────┐ │
│ │ Distance │ │ │ │ Calcul TTC │ │ │ │ Affichage │ │
│ │ monoculaire│ │ │ │ │ │ │ │ temps réel │ │
│ └─────┬──────┘ │ │ └─────┬──────┘ │ │ └─────┬──────┘ │
│ │ │ │ │ │ │ │ │
│ ┌─────▼──────┐ │ │ ┌─────▼──────┐ │ │ ┌─────▼──────┐ │
│ │ Encodeur │ │ │ │ FSM │ │ │ │ Alertes │ │
│ │ cantools │ │ │ │ 5 états │ │ │ │ visuelles │ │
│ └─────┬──────┘ │ │ └─────┬──────┘ │ │ └────────────┘ │
│ │ │ │ │ │ │ │
│ ┌─────▼──────┐ │ │ ┌─────▼──────┐ │ │ │
│ │ SocketCAN │ │ │ │ E2E : CRC8 │ │ │ │
│ │ TX │ │ │ │ + compteur │ │ │ │
│ └─────┬──────┘ │ │ └─────┬──────┘ │ │ │
│ │ │ │ │ │ │ │
└────────┼─────────┘ └────────┼─────────┘ └──────────▲───────┘
│ │ │
│ 0x100 PERC_OBJECT │ 0x200 DEC_ALERT │
│ 20 Hz │ 20 Hz │
└──────────────►────────────┤ │
│ 0x201 DEC_HB │
│ 10 Hz │
└─────────────────────────────┘
vcan0 (SocketCAN)






## 2. Description des ECU

### 2.1 ECU Perception (Python)

| Aspect | Détail |
|---|---|
| Rôle | Détecter les véhicules et estimer la distance |
| Entrées | Flux d'images (dataset KITTI ou webcam simulée) |
| Sorties | Trame `PERC_OBJECT` (0x100) à 20 Hz sur `vcan0` |
| Dépendances | `ultralytics` (YOLOv8n), `opencv-python`, `cantools`, `python-can` |
| Fichiers | `perception/detector.py`, `perception/distance.py`, `perception/can_tx.py` |

**Pipeline** :
1. Charger une image KITTI (ou vidéo)
2. Inférence YOLOv8n (CPU) → bounding boxes
3. Filtrer classe `car` + ROI centrale (voie du véhicule)
4. Estimation distance monoculaire (hauteur bbox / hauteur réelle connue)
5. Calcul TTC préliminaire
6. Encodage DBC + envoi sur `vcan0`

### 2.2 ECU Décision (C++)

| Aspect | Détail |
|---|---|
| Rôle | Décider FCW / freinage / faute |
| Entrées | Trame `PERC_OBJECT` (0x100) |
| Sorties | `DEC_ALERT` (0x200) à 20 Hz, `DEC_HB` (0x201) à 10 Hz |
| Dépendances | SocketCAN natif, `cantools` (ou décodeur manuel), GoogleTest |
| Fichiers | `decision/main.cpp`, `decision/ttc.cpp`, `decision/fsm.cpp`, `decision/e2e.cpp` |

**Logique** :
1. Boucle de réception SocketCAN (non bloquante)
2. Décodage trame → structure `ObjectData`
3. Calcul TTC = distance / |vitesse_relative|
4. Machine à états : OFF → STANDBY → WARNING → BRAKE (+ FAULT)
5. Application E2E : CRC8 + compteur 4 bits sur `DEC_ALERT`
6. Émission `DEC_ALERT` + `DEC_HB`

### 2.3 Dashboard (Python)

| Aspect | Détail |
|---|---|
| Rôle | Afficher l'état temps réel du système |
| Entrées | `DEC_ALERT` (0x200) + `DEC_HB` (0x201) |
| Sorties | Interface console (ou matplotlib en Phase 5) |
| Dépendances | `python-can`, `cantools`, `rich` ou `textual` |
| Fichiers | `dashboard/main.py` |

## 3. Interfaces

### 3.1 Bus CAN

| Message | ID | DLC | Cycle | Émetteur | Récepteurs |
|---|---|---|---|---|---|
| `PERC_OBJECT` | 0x100 | 8 | 50 ms | Perception | Décision, Dashboard |
| `DEC_ALERT` | 0x200 | 4 | 50 ms | Décision | Dashboard |
| `DEC_HB` | 0x201 | 2 | 100 ms | Décision | Dashboard |

Détail des signaux : voir `shared/dbc/adas.dbc`.

### 3.2 Interface Python ↔ C++

Pas d'appel direct. Toute communication passe par le bus CAN. C'est **volontaire** : cela
force une frontière nette entre les composants et permet de simuler des pannes
(perte de trame, latence, corruption).

## 4. Machine à états (ECU Décision)





┌───────────────────────────────────────────┐
│ │
▼ │
┌───────┐ init ┌──────────┐ trame OK ┌───┴────┐
│ OFF ├──────────►│ STANDBY ├───────────►│ WARN │
└───────┘ └────┬─────┘ └───┬────┘
│ │
│ trame invalide │ TTC < 1.2 s
│ ou timeout │
▼ ▼
┌──────────┐ ┌──────────┐
│ FAULT │◄──────────┤ BRAKE │
└──────────┘ erreur └──────────┘







| État | Condition d'entrée | Action |
|---|---|---|
| `OFF` | Démarrage | Aucune émission |
| `STANDBY` | Init OK | `alert_level = 1` |
| `WARNING` | `1.2 < TTC < 2.0 s` | `alert_level = 2`, alerte visuelle |
| `BRAKE` | `TTC < 1.2 s` | `alert_level = 3`, freinage urgence |
| `FAULT` | Timeout > 100 ms, CRC KO, compteur figé | `alert_level = 4`, log erreur |

## 5. Protection E2E

Conforme **AUTOSAR E2E Profile 1** (adapté) :

| Mécanisme | Implémentation |
|---|---|
| CRC | CRC8 poly 0x1D sur les 3 premiers octets de `DEC_ALERT` |
| Compteur | 4 bits (0–15, wrap) |
| Détection | Trame rejetée si CRC KO ou compteur identique 3 fois |
| Timeout | 100 ms sans trame valide → `FAULT` |

## 6. Arborescence cible

adas-can/
├── docs/
│ ├── phase0_2_validation.md
│ ├── requirements.md
│ └── architecture.md
├── perception/
│ ├── detector.py
│ ├── distance.py
│ └── can_tx.py
├── decision/
│ ├── main.cpp
│ ├── ttc.cpp
│ ├── fsm.cpp
│ ├── e2e.cpp
│ └── CMakeLists.txt
├── dashboard/
│ └── main.py
├── shared/
│ └── dbc/
│ └── adas.dbc
├── scripts/
│ └── setup_vcan.sh
├── tests/
│ ├── test_vcan_loopback.py
│ ├── test_dbc.py
│ └── test_fsm.cpp
└── README.md


## 7. Limites assumées

| Limite | Impact | Mitigation |
|---|---|---|
| Estimation distance monoculaire | Erreur ~15 % | Documenter, tester sur plusieurs scénarios KITTI |
| Pas de fusion capteurs | Robustesse réduite | Hors scope |
| YOLOv8n CPU | ~100–200 ms / image | Fréquence CAN réduite à 20 Hz, pas 30 Hz |
| Bus `vcan` logiciel | Jitter non garanti | Acceptable en SIL |
| Pas de redondance matérielle | — | Hors scope |

## 8. Choix techniques justifiés

| Choix | Justification |
|---|---|
| Python pour Perception | Écosystème IA mature (ultralytics, numpy, opencv) |
| C++ pour Décision | Représentatif d'un ECU embarqué réel, MISRA-friendly |
| SocketCAN direct (pas de wrapper haut niveau) | Contrôle total, apprentissage bas niveau |
| DBC + `cantools` | Standard industrie, réutilisable |
| CRC8 poly 0x1D | Standard AUTOSAR E2E Profile 1 |
| FSM explicite | Traçabilité et testabilité |

## 9. Historique

| Version | Date | Changement |
|---|---|---|
| 0.1 | 2026-10-07 | Création initiale |


### Précision de l'estimation de distance

La méthode monoculaire par hauteur de bbox a une erreur type de ~15 %.
Sources principales :
- Incertitude sur la hauteur réelle de l'objet (± 20 %)
- Précision de la bbox YOLO (± 5–10 px)
- Inclinaison de l'objet (vue de biais)
- Absence de correction de distorsion

Améliorations possibles (hors scope Phase 2) :
- Ground plane method (point de contact pneu/sol) → ~5 %
- Lissage temporel (moyenne N frames) → réduction bruit
- Vision stéréo → ~5 % (nécessite 2 caméras calibrées)
- Modèles IA de profondeur (MiDaS) → ~10 % (lent sur CPU)




