# Phase 0.2 — Validation vcan0 / SocketCAN

**Date** : 2026-10-07
**Environnement** : Ubuntu 22.04.5 LTS (VM VirtualBox), noyau 6.8.0
**Objectif** : valider la pile SocketCAN virtuelle (vcan0) côté shell et Python.

## 1. Module noyau


## 2. Interface vcan0


## 3. Loopback can-utils

## 4. Loopback Python SocketCAN

## Conclusion
Phase 0.2 validée. La pile SocketCAN est opérationnelle en émission
et réception, côté shell (can-utils) et côté Python (socket AF_CAN).
L'interface vcan0 est recréable à volonté via scripts/setup_vcan.sh.


