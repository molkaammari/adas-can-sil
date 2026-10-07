#!/usr/bin/env bash
set -e
sudo modprobe vcan
ip link show vcan0 >/dev/null 2>&1 || sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
ip -brief link show vcan0

chmod +x scripts/setup_vcan.sh
