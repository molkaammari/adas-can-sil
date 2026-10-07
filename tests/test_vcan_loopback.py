#!/usr/bin/env python3
"""Sanity check SocketCAN vcan0 — Phase 0.2."""
import socket
import struct
import threading
import time

CAN_IFACE = "vcan0"
CAN_ID = 0x123
DATA = bytes([0xDE, 0xAD, 0xBE, 0xEF])


def emitter():
    """Émet une trame CAN brute sur vcan0."""
    time.sleep(0.3)  # laisse le temps au récepteur de bind
    s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
    s.bind((CAN_IFACE,))
    s.send((struct.pack("<IB3x8s", CAN_ID, len(DATA), DATA)))
    s.close()
    print(f"[TX] ID=0x{CAN_ID:X} DLC={len(DATA)} DATA={DATA.hex()}")


def receiver():
    s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
    s.bind((CAN_IFACE,))
    s.settimeout(2.0)
    try:
        frame = s.recv(16)
        can_id, can_dlc = struct.unpack("<IB3x8s", frame)[:2]
        payload = frame[8:8 + can_dlc]
        print(f"[RX] ID=0x{can_id:X} DLC={can_dlc} DATA={payload.hex()}")
        assert can_id == CAN_ID, "ID mismatch"
        assert payload == DATA, "Payload mismatch"
        print("✅ Test loopback Python OK")
    except socket.timeout:
        print("❌ Timeout : aucune trame reçue")
    finally:
        s.close()


if __name__ == "__main__":
    t = threading.Thread(target=emitter)
    t.start()
    receiver()
    t.join()
