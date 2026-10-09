# Phase 4 — Validation de l'ECU Décision (C++)

**Date** : 2026-10-09
**Auteur** : Molka Ammari
**Environnement** : Ubuntu 22.04.5 LTS (VM VirtualBox), noyau 6.8.0
**Objectif** : valider l'ECU Décision C++ de bout en bout sur `vcan0`

---

## 1. Résumé

L'ECU Décision C++ reçoit les trames `PERC_OBJECT` (0x100) émises par l'ECU Perception Python,
calcule le TTC, applique une machine à états (FSM) à 5 états, et émet des alertes
protégées par CRC E2E (`DEC_ALERT` 0x200 et `DEC_HB` 0x201).

**Résultat** : intégration SIL bout-en-bout validée.

---

## 2. Architecture logicielle

### 2.1 Modules C++

| Module | Fichiers | Rôle | Tests |
|---|---|---|---|
| Types | `types.hpp` | Structures de données partagées | — |
| E2E | `e2e.hpp/cpp` | CRC8 (poly 0x1D) + compteur 4 bits | 8 |
| TTC | `ttc.hpp/cpp` | Calcul TTC + estimateur vitesse | 15 |
| Decoder | `decoder.hpp/cpp` | Décodage PERC_OBJECT (bit-level) | 9 |
| Encoder | `encoder.hpp/cpp` | Encodage DEC_ALERT + DEC_HB | 14 |
| FSM | `fsm.hpp/cpp` | Machine à états (5 états + hystérésis) | 17 |
| CAN RX/TX | `can_rx.hpp/cpp`, `can_tx.hpp/cpp` | SocketCAN natif | 6 |
| Main | `main.cpp` | Orchestrateur (boucle principale) | — |

**Total : 69 tests unitaires, tous verts.**

### 2.2 Flux de données

```
┌──────────────┐    PERC_OBJECT    ┌──────────────┐    DEC_ALERT     ┌──────────┐
│  Perception  │  ─── 0x100 ────►  │   Décision   │  ─── 0x200 ────► │Dashboard │
│   (Python)   │      20 Hz        │    (C++)     │      20 Hz       │ (Python) │
└──────────────┘                   │              │                  └──────────┘
                                   │              │    DEC_HB
                                   │              │  ─── 0x201 ────►  (idem)
                                   └──────────────┘      10 Hz
```

---

## 3. Machine à états (FSM)

### 3.1 Diagramme

```
         ┌──────────────────────────────────────┐
         ▼                                      │
     ┌───────┐   init   ┌──────────┐  trame  ┌──┴─────┐
     │  OFF  ├─────────►│ STANDBY  ├────────►│WARNING │
     └───────┘          └────┬─────┘  TTC<2s └──┬─────┘
                             │                  │ TTC<1.2s
                             │ timeout/erreur   ▼
                             ▼              ┌──────────┐
                        ┌──────────┐        │  BRAKE   │
                        │  FAULT   │◄───────└──────────┘
                        └──────────┘  erreur
```

### 3.2 Règles de transition

| État | Condition d'entrée | AlertLevel |
|---|---|---|
| `OFF` | Init | 0 |
| `STANDBY` | Trame valide reçue, TTC ≥ 2.0 s | 1 |
| `WARNING` | 1.2 < TTC < 2.0 s | 2 |
| `BRAKE` | TTC < 1.2 s | 3 |
| `FAULT` | Timeout > 100 ms, trame invalide | 4 |

**Hystérésis** : 500 ms pour éviter les oscillations aux seuils.

**Sécurité** : pas d'auto-recovery depuis FAULT. Une nouvelle trame valide est
**obligatoire** pour revenir en STANDBY (REQ-E2E-003).

---

## 4. Protection E2E

### 4.1 CRC8 AUTOSAR E2E Profile 1

| Paramètre | Valeur |
|---|---|
| Polynôme | `0x1D` |
| Init | `0xFF` |
| Xorout | `0xFF` |
| Refin / Refout | Non / Non |
| Détection bit-flip | 100 % sur 1 bit |

### 4.2 Compteur 4 bits

- Wrap : `0 → 15 → 0`
- Détection de compteur figé : après 3 trames identiques → FAULT

---

## 5. Tests unitaires

### 5.1 Répartition

| Suite | Nombre | Couverture |
|---|---|---|
| `test_e2e.cpp` | 8 | CRC8 + compteur |
| `test_ttc.cpp` | 15 | TTC + estimateur vitesse |
| `test_decoder.cpp` | 9 | Décodage PERC_OBJECT |
| `test_encoder.cpp` | 14 | Encodage DEC_ALERT + DEC_HB |
| `test_fsm.cpp` | 17 | FSM : transitions, hystérésis, timeout |
| `test_can.cpp` | 6 | SocketCAN : open/send/recv |
| **Total** | **69** | — |

### 5.2 Exécution

```
$ cd decision/build
$ ctest --output-on-failure

100% tests passed, 0 tests failed out of 69
Total Test time (real) =   0.78 sec
```

---

## 6. Validation sur bus CAN réel (`vcan0`)

### 6.1 Trames observées

**Émission DEC_ALERT (0x200) à 20 Hz** :
```
vcan0  200   [4]  00 00 00 F1
vcan0  200   [4]  00 00 01 EC
vcan0  200   [4]  00 00 02 CB
...
vcan0  200   [4]  00 00 0F 4A
vcan0  200   [4]  00 00 00 F1    ← wrap compteur E2E
```

**Émission DEC_HB (0x201) à 10 Hz** :
```
vcan0  201   [2]  00 00
vcan0  201   [2]  01 00
vcan0  201   [2]  02 00
...
```

### 6.2 Intégration avec Python Perception

**Terminal 1** — `candump vcan0`

**Terminal 2** — ECU Décision :
```
$ ./decision_main --duration 60
[INIT] CAN receiver ouvert (filtre 0x100)
[INIT] CAN sender ouvert
[RUN] boucle démarrée

[FSM] transition → STANDBY (ttc=0.000 s)
[FSM] tick transition → FAULT
[FSM] transition → STANDBY (ttc=0.000 s)
[FSM] tick transition → FAULT
...
[STOP] arrêt propre
```

**Terminal 3** — Python en boucle :
```bash
for i in $(seq 1 20); do
    python -m perception.main --image perception/data/samples/bus.jpg
    sleep 0.5
done
```

**Observation** : la FSM alterne `STANDBY ↔ FAULT` à chaque cycle
(une trame reçue → STANDBY, timeout 100 ms → FAULT, nouvelle trame → STANDBY).

**Conclusion** : la chaîne complète fonctionne. Python → C++ → FSM → Émission.

---

## 7. Limites assumées

| Limite | Impact | Mitigation |
|---|---|---|
| Timeout perception 100 ms | FSM oscille si source à basse fréquence | Paramétrable (`PERCEPTION_TIMEOUT_S`) |
| Python perception ~0.5 Hz | Loin des 20 Hz cible | Utiliser un flux vidéo continu en Phase 6 |
| TTC = 0 si `v_rel = 0` | Pas d'alerte sur objet immobile | Correct : pas de collision prévue |
| Pas de CRC check côté réception | Trames corrompues acceptées | À ajouter (Phase 6, injection défauts) |
| Pas de test avec `PERC_OBJECT` à TTC bas | WARNING/BRAKE non observés en SIL | À faire en Phase 6 |

---

## 8. Ce qui reste

- **Phase 5** : Dashboard Python (IHM temps réel)
- **Phase 6** : Validation SIL + injection de défauts
- **Phase 7** : Valorisation (README final, pitch, LinkedIn)

---

## 9. Historique

| Version | Date | Changement |
|---|---|---|
| 0.1 | 2026-10-09 | Création initiale — Phase 4 clôturée |

