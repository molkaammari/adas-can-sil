# Injection de défauts — Validation SIL

Scripts d'injection de défauts pour la validation de robustesse du système ADAS FCW.

## Objectif

Vérifier que l'ECU Décision C++ et le Dashboard détectent et gèrent correctement
les anomalies suivantes :

| Défaut | Script | Vérifie |
|---|---|---|
| **CRC corrompu** | `crc_corruption.py` | Détection par CRC8 E2E |
| **Compteur figé** | `frozen_counter.py` | Détection de séquence E2E invalide |
| **Timeout** | `timeout.py` | Détection d'absence de trame (FAULT) |
| **Valeurs aberrantes** | `out_of_range.py` | Rejet par validation de plage |

## Prérequis

- `vcan0` UP (`bash scripts/setup_vcan.sh`)
- venv Python activé (`source .venv/bin/activate`)
- ECU Décision compilé (`decision/build/decision_main`)

## Utilisation

### Test d'un défaut isolé

**Terminal 1** — ECU Décision :
```bash
cd decision/build
./decision_main --duration 30
```

**Terminal 2** — Injection :
```bash
cd ~/adas-can
source .venv/bin/activate
python -m tests.injection.crc_corruption
```

### Test complet (tous les défauts)

**Terminal 1** — ECU Décision :
```bash
cd decision/build
./decision_main --duration 120
```

**Terminal 2** — Injection complète :
```bash
cd ~/adas-can
source .venv/bin/activate
python -m tests.injection.run_all
```

## Résultats attendus

| Défaut | Réaction attendue |
|---|---|
| CRC corrompu | `[FSM] tick transition → FAULT` (timeout détecté) |
| Compteur figé | `[WARNING] Compteur E2E sauté` côté dashboard |
| Timeout | `[FSM] tick transition → FAULT` |
| Valeurs aberrantes | Rejet silencieux (objet invalide ignoré) |

## Structure

```
tests/injection/
├── __init__.py
├── common.py                # Helpers partagés
├── crc_corruption.py        # Injection CRC
├── frozen_counter.py        # Injection compteur
├── timeout.py               # Injection timeout
├── out_of_range.py          # Injection valeurs limites
└── run_all.py               # Orchestrateur
```

## Références

- `docs/requirements.md` — REQ-E2E-001 à 004, REQ-ROB-001
- `docs/architecture.md` — section E2E
- `docs/phase4_validation.md` — protection E2E


