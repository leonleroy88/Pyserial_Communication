#!/usr/bin/env python3
"""
Test Potentiomètre → Dynamixel position
Potentiomètre (0–1023) → Moteur ID4 (0–2048 ticks = 180°)
Arduino COM3 — U2D2 COM4
"""

import serial
import time
from dynamixel_sdk import *

# ══════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════
ARDUINO_PORT = "COM5"
ARDUINO_BAUD = 9600

DXL_PORT     = "COM4"
DXL_BAUD     = 57600
PROTOCOL     = 2.0

MOTOR_ID     = 4

# Mapping : pot 0–1023 → position 0–2048 (180°)
POT_MIN      = 0
POT_MAX      = 1023
DXL_MIN      = 0
DXL_MAX      = 2048

# Vitesse de profil — très lente et précise
PROFILE_VEL  = 15
PROFILE_ACCEL = 6

# Zone morte : ignore les micro-variations du pot (bruit ADC)
DEADBAND     = 6    # en ticks Dynamixel

# Control Table
ADDR_TORQUE_ENABLE  = 64
ADDR_OPERATING_MODE = 11
ADDR_PROFILE_ACCEL  = 108
ADDR_PROFILE_VEL    = 112
ADDR_GOAL_POSITION  = 116
ADDR_PRESENT_POS    = 132
MODE_POSITION       = 3

# ══════════════════════════════════════════════════════════════════
# UTILITAIRES
# ══════════════════════════════════════════════════════════════════
def map_value(x, in_min, in_max, out_min, out_max):
    return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

def clamp(val, lo, hi):
    return max(lo, min(hi, int(val)))

# ══════════════════════════════════════════════════════════════════
# CONNEXION DYNAMIXEL
# ══════════════════════════════════════════════════════════════════
ph  = PortHandler(DXL_PORT)
pkh = PacketHandler(PROTOCOL)

if not ph.openPort():
    print(f"[ERREUR] Impossible d'ouvrir {DXL_PORT}")
    exit(1)
if not ph.setBaudRate(DXL_BAUD):
    print(f"[ERREUR] Baudrate refusé")
    exit(1)
print(f"[OK] Dynamixel — {DXL_PORT} @ {DXL_BAUD}")

# Mode position + couple ON
pkh.write1ByteTxRx(ph, MOTOR_ID, ADDR_TORQUE_ENABLE,  0)
pkh.write1ByteTxRx(ph, MOTOR_ID, ADDR_OPERATING_MODE, MODE_POSITION)
pkh.write1ByteTxRx(ph, MOTOR_ID, ADDR_TORQUE_ENABLE,  1)
pkh.write4ByteTxRx(ph, MOTOR_ID, ADDR_PROFILE_ACCEL,  PROFILE_ACCEL)
pkh.write4ByteTxRx(ph, MOTOR_ID, ADDR_PROFILE_VEL,    PROFILE_VEL)
print(f"[OK] Moteur ID {MOTOR_ID} → mode POSITION (0–2048 ticks / 180°)")

def set_position(pos):
    pos = clamp(pos, DXL_MIN, DXL_MAX)
    pkh.write4ByteTxRx(ph, MOTOR_ID, ADDR_GOAL_POSITION, pos)

def get_position():
    v, r, _ = pkh.read4ByteTxRx(ph, MOTOR_ID, ADDR_PRESENT_POS)
    return v if r == COMM_SUCCESS else None

# ══════════════════════════════════════════════════════════════════
# CONNEXION ARDUINO
# ══════════════════════════════════════════════════════════════════
arduino = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)
time.sleep(2)
arduino.flushInput()
print(f"[OK] Arduino — {ARDUINO_PORT} @ {ARDUINO_BAUD}")

# ══════════════════════════════════════════════════════════════════
# BOUCLE PRINCIPALE
# ══════════════════════════════════════════════════════════════════
print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("  Tournez le potentiomètre pour bouger le moteur")
print("  Ctrl+C pour quitter")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

last_target = -1   # dernière position envoyée au moteur

try:
    while True:
        ligne = arduino.readline().decode("utf-8", errors="ignore").strip()
        if not ligne:
            continue

        # Parse CSV : btn1,btn2,pot
        parts = ligne.split(",")
        if len(parts) != 3:
            continue

        try:
            pot = int(parts[2])
        except ValueError:
            continue

        # Remapping pot → position moteur
        target = map_value(pot, POT_MIN, POT_MAX, DXL_MIN, DXL_MAX)

        # Envoyer seulement si déplacement > deadband
        if abs(target - last_target) > DEADBAND:
            set_position(target)
            last_target = target

            # Lecture position réelle
            real = get_position()
            deg  = round(target / 4095 * 360, 1)

            print(f"  Pot: {pot:4d}  →  Cible: {target:4d} ticks ({deg:5.1f}°)"
                  f"  |  Réelle: {real if real else '?':>4}", end="\r")

except KeyboardInterrupt:
    print("\n\nArrêt...")

finally:
    pkh.write1ByteTxRx(ph, MOTOR_ID, ADDR_TORQUE_ENABLE, 0)
    ph.closePort()
    arduino.close()
    print("Moteur arrêté — connexions fermées.")
