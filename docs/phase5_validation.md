# Phase 5 — Validation du Dashboard (Python)

**Date** : 2026-10-09
**Auteur** : Molka Ammari
**Environnement** : Ubuntu 22.04.5 LTS (VM VirtualBox)
**Objectif** : valider l'IHM temps réel qui affiche l'état du système ADAS

---

## 1. Résumé

Le Dashboard Python écoute le bus `vcan0`, décode les trames `DEC_ALERT` (0x200)
et `DEC_HB` (0x201) émises par l'ECU Décision C++, et affiche l'état en temps réel
via une interface console `rich`.

**Résultat** : affichage temps réel fonctionnel, transitions FSM visibles,
détection E2E (compteur + heartbeat), statistiques en direct.

---

## 2. Architecture

### 2.1 Modules Python

| Module | Fichier | Rôle |
|---|---|---|
| Décodeur | `dashboard/decoder.py` | Décodage DEC_ALERT + DEC_HB (cantools) |
| Récepteur | `dashboard/receiver.py` | SocketCAN + état + statistiques |
| Interface | `dashboard/main.py` | Affichage `rich` (TUI live) |

### 2.2 Flux de données

