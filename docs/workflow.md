# Workflow complet — De l'image à la décision

## Vue linéaire

```mermaid
flowchart TD
    START([📸 Image KITTI]) --> STEP1

    STEP1[1. Chargement image<br/>1080x810 pixels]
    STEP1 --> STEP2

    STEP2[2. YOLOv8n<br/>Détection objets]
    STEP2 --> STEP3{Classes pertinentes ?}

    STEP3 -->|Non| SKIP[Ignoré]
    STEP3 -->|Oui car/truck/bus| STEP4

    STEP4[3. Extraction bbox<br/>x1,y1,x2,y2]
    STEP4 --> STEP5

    STEP5[4. Filtrage ROI centrale<br/>Voie du véhicule]
    STEP5 --> STEP6

    STEP6[5. Distance monoculaire<br/>Z = f_y × H_réel / h_bbox]
    STEP6 --> STEP7

    STEP7[6. Construction PerceivedObject<br/>obj_id, dist, v_rel, ttc, valid]
    STEP7 --> STEP8

    STEP8[7. Encodage DBC<br/>8 octets little-endian]
    STEP8 --> STEP9

    STEP9[8. Émission CAN<br/>0x100 @ 20 Hz]
    STEP9 --> BUS((BUS vcan0))

    BUS --> STEP10[9. Réception ECU Décision]
    STEP10 --> STEP11

    STEP11[10. Décodage manuel<br/>bit-level extraction]
    STEP11 --> STEP12

    STEP12[11. Calcul TTC<br/>TTC = d / |v_rel|]
    STEP12 --> STEP13

    STEP13[12. FSM transition]
    STEP13 --> DEC{État}

    DEC -->|TTC > 2s| STANDBY[🟢 STANDBY]
    DEC -->|1.2 < TTC < 2s| WARNING[🟡 WARNING]
    DEC -->|TTC < 1.2s| BRAKE[🔴 BRAKE]
    DEC -->|timeout| FAULT[⚫ FAULT]

    STANDBY --> STEP14
    WARNING --> STEP14
    BRAKE --> STEP14
    FAULT --> STEP14

    STEP14[13. CRC8 + compteur E2E]
    STEP14 --> STEP15

    STEP15[14. Encodage DEC_ALERT<br/>4 octets]
    STEP15 --> STEP16

    STEP16[15. Émission CAN<br/>0x200 @ 20 Hz]
    STEP16 --> BUS2((BUS vcan0))

    BUS2 --> STEP17[16. Réception Dashboard]
    STEP17 --> STEP18

    STEP18[17. Décodage cantools<br/>+ vérification E2E]
    STEP18 --> STEP19

    STEP19[18. Affichage rich TUI<br/>État + TTC + stats]
    STEP19 --> END([📊 Alerte affichée])

    style START fill:#e1f5ff
    style END fill:#e8f5e9
    style STANDBY fill:#c8e6c9
    style WARNING fill:#fff9c4
    style BRAKE fill:#ffcdd2
    style FAULT fill:#e0e0e0
```

