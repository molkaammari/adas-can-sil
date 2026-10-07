# Requirements — ADAS Forward Collision Warning (SIL)

**Version** : 0.1
**Date** : 2026-10-07
**Auteur** : Molka Ammari
**Statut** : Draft initial

## 1. Portée

Système ADAS de type Forward Collision Warning (FCW) simulé en Software-in-the-Loop.
Aucun matériel physique. Communication inter-ECU via bus CAN virtuel SocketCAN (`vcan0`).

## 2. Acteurs et ECU

| ECU | Langage | Rôle |
|---|---|---|
| Perception | Python | Détection objets (YOLOv8n) + estimation distance monoculaire |
| Décision | C++ | Réception trames, calcul TTC, FSM, protection E2E |
| Dashboard | Python | Affichage temps réel de l'état et des alertes |

## 3. Exigences fonctionnelles — Perception

| ID | Exigence | Critère d'acceptation |
|---|---|---|
| REQ-PER-001 | Détecter les véhicules (classe `car`) sur flux vidéo KITTI | Précision YOLOv8n ≥ 0.5 mAP@0.5 |
| REQ-PER-002 | Estimer la distance relative au véhicule détecté | Erreur < 15 % sur 10–50 m (limite monoculaire assumée) |
| REQ-PER-003 | Calculer la vitesse relative | Dérivée temporelle de la distance, lissage EMA |
| REQ-PER-004 | Émettre une trame CAN `PERC_OBJECT` à 20 Hz | Jitter < 5 ms |
| REQ-PER-005 | Ne traiter que l'objet le plus proche dans la voie | Sélection par ROI centrale (TBD) |

## 4. Exigences fonctionnelles — Bus CAN

| ID | Exigence | Critère d'acceptation |
|---|---|---|
| REQ-CAN-001 | Utiliser SocketCAN `vcan0` | Déjà validé Phase 0.2 |
| REQ-CAN-002 | Décrire toutes les trames dans `shared/dbc/adas.dbc` | Format DBC 8.x |
| REQ-CAN-003 | Trames : `PERC_OBJECT` (0x100), `DEC_ALERT` (0x200), `DEC_HB` (0x201) | Voir DBC |
| REQ-CAN-004 | DLC et endianness cohérents avec le DBC | Vérifié par `cantools` |

## 5. Exigences fonctionnelles — Décision

| ID | Exigence | Critère d'acceptation |
|---|---|---|
| REQ-DEC-001 | Recevoir et décoder les trames `PERC_OBJECT` | Décodage `cantools` en C++ |
| REQ-DEC-002 | Calculer le TTC = distance / vitesse_relative | Conforme ISO 15622 |
| REQ-DEC-003 | Déclencher FCW si TTC < 2.0 s | Latence < 100 ms |
| REQ-DEC-004 | Déclencher freinage urgence si TTC < 1.2 s | Priorité sur FCW |
| REQ-DEC-005 | Machine à états : `OFF / STANDBY / WARNING / BRAKE / FAULT` | Toutes transitions testées |
| REQ-DEC-006 | Émettre `DEC_ALERT` à 20 Hz avec état courant | Jitter < 5 ms |
| REQ-DEC-007 | Émettre `DEC_HB` (heartbeat) à 10 Hz | Compteur vivant 8 bits |

## 6. Exigences de sécurité (E2E)

| ID | Exigence | Critère d'acceptation |
|---|---|---|
| REQ-E2E-001 | Protection E2E sur `DEC_ALERT` | CRC8 (poly 0x1D) + compteur 4 bits |
| REQ-E2E-002 | Détection de trame corrompue | 100 % des corruptions CRC détectées |
| REQ-E2E-003 | Détection de compteur figé | Après 3 trames identiques → FAULT |
| REQ-E2E-004 | Timeout trame perception > 100 ms → FAULT | Transition FSM vérifiée |

## 7. Exigences de robustesse

| ID | Exigence | Critère d'acceptation |
|---|---|---|
| REQ-ROB-001 | Aucun crash sur trame malformée | Test par fuzzing basique |
| REQ-ROB-002 | Gestion des signaux SIGINT / SIGTERM | Arrêt propre des threads |
| REQ-ROB-003 | Log horodaté de toutes les transitions FSM | Format ISO 8601 |
| REQ-ROB-004 | Code C++ conforme MISRA C++ (sous-ensemble raisonnable) | Vérification manuelle + flags compilateur |

## 8. Exigences de validation (SIL)

| ID | Exigence | Critère d'acceptation |
|---|---|---|
| REQ-VAL-001 | Tests unitaires C++ avec GoogleTest | Couverture ≥ 70 % |
| REQ-VAL-002 | Injection de défauts : perte trame, CRC corrompu, compteur figé | 3 scénarios minimum |
| REQ-VAL-003 | Scénario bout-en-bout : KITTI → décision → dashboard | Démonstration reproductible |
| REQ-VAL-004 | Logs de session archivés dans `logs/` | Nom horodaté |

## 9. Contraintes

- 100 % Software-in-the-Loop, aucun matériel physique.
- Cible de dev : VM Ubuntu 22.04.5, 4 vCPU, 8 Go RAM.
- CPU uniquement (pas de GPU).
- Python 3.10+, C++17, CMake ≥ 3.22.

## 10. Limites assumées (honnêteté technique)

| Limite | Impact | Justification |
|---|---|---|
| Estimation distance monoculaire | Erreur ~15 % | Pas de radar / LiDAR dans le scope |
| Pas de fusion multi-capteurs | Détection moins robuste | Choix de simplification |
| Modèle YOLOv8n CPU | Inférence ~100–200 ms | Contrainte matérielle de la VM |
| Pas de bus CAN temps réel | Jitter non garanti < 1 ms | `vcan` est purement logiciel |
| Pas de validation sur véhicule réel | Scope académique | Projet SIL uniquement |

## 11. Traçabilité

| Phase | Documents produits |
|---|---|
| Phase 0.2 | `docs/phase0_2_validation.md` |
| Phase 1 | `docs/requirements.md` (ce doc), `shared/dbc/adas.dbc`, `docs/architecture.md` |
| Phase 2 | `perception/` (code + tests) |
| Phase 3 | `shared/dbc/` + `tests/test_dbc.py` |
| Phase 4 | `decision/` (C++ + GoogleTest) |
| Phase 5 | `dashboard/` |
| Phase 6 | `docs/phase6_validation.md` |

## 12. Historique

| Version | Date | Changement |
|---|---|---|
| 0.1 | 2026-10-07 | Création initiale |
