#!/usr/bin/env python3
"""
Test Arduino → Dynamixel
- Bouton 1 (D4) → moteur ID3 tourne dans un sens
- Bouton 2 (D5) → moteur ID3 tourne dans l'autre sens
- Rien appuyé  → moteur stop
- Potentiomètre (A0) → affiché dans le terminal
"""

import serial
import time
from dynamixel_sdk import *

# ══════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════
ARDUINO_PORT = "COM5"   # ← port Arduino
ARDUINO_BAUD = 9600

DXL_PORT     = "COM4"   # ← port U2D2
DXL_BAUD     = 57600
PROTOCOL     = 2.0

MOTOR_ID     = 4        # ← ID du moteur à tester (3 ou 4)
VITESSE      = 30       # ← vitesse de rotation (0–265, lent)

ADDR_TORQUE_ENABLE  = 64
ADDR_OPERATING_MODE = 11
ADDR_GOAL_VELOCITY  = 104
MODE_VELOCITY       = 1

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

# Mode vitesse + couple ON
pkh.write1ByteTxRx(ph, MOTOR_ID, ADDR_TORQUE_ENABLE,  0)
pkh.write1ByteTxRx(ph, MOTOR_ID, ADDR_OPERATING_MODE, MODE_VELOCITY)
pkh.write1ByteTxRx(ph, MOTOR_ID, ADDR_TORQUE_ENABLE,  1)
print(f"[OK] Moteur ID {MOTOR_ID} → mode VITESSE")

def set_vel(vel):
    pkh.write4ByteTxRx(ph, MOTOR_ID, ADDR_GOAL_VELOCITY, int(vel))

# ══════════════════════════════════════════════════════════════════
# CONNEXION ARDUINO
# ══════════════════════════════════════════════════════════════════
arduino = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)
time.sleep(2)           # attendre reset Arduino
arduino.flushInput()
print(f"[OK] Arduino — {ARDUINO_PORT} @ {ARDUINO_BAUD}")

# ══════════════════════════════════════════════════════════════════
# BOUCLE PRINCIPALE
# ══════════════════════════════════════════════════════════════════
print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("  BTN1 → tourne sens +")
print("  BTN2 → tourne sens -")
print("  Rien → stop")
print("  Ctrl+C pour quitter")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

last_state = None   # évite d'envoyer la même commande en boucle

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
            btn1 = int(parts[0])
            btn2 = int(parts[1])
            pot  = int(parts[2])
        except ValueError:
            continue

        # Déterminer l'état
        if btn1 and not btn2:
            state = "AVANT"
        elif btn2 and not btn1:
            state = "ARRIERE"
        else:
            state = "STOP"

        # Envoyer commande seulement si changement d'état
        if state != last_state:
            if state == "AVANT":
                set_vel(VITESSE)
                print(f"  ▶ AVANT   | Pot: {pot:4d}")
            elif state == "ARRIERE":
                set_vel(-VITESSE & 0xFFFFFFFF)  # négatif en uint32
                print(f"  ◀ ARRIÈRE | Pot: {pot:4d}")
            else:
                set_vel(0)
                print(f"  ■ STOP    | Pot: {pot:4d}")
            last_state = state
        else:
            # Affiche le pot même sans changement (toutes les ~20 trames)
            if not hasattr(set_vel, '_cnt'):
                set_vel._cnt = 0
            set_vel._cnt += 1
            if set_vel._cnt % 20 == 0:
                print(f"  {'▶' if state=='AVANT' else '◀' if state=='ARRIERE' else '■'} {state:<8} | Pot: {pot:4d}", end="\r")

except KeyboardInterrupt:
    print("\n\nArrêt...")

finally:
    set_vel(0)
    pkh.write1ByteTxRx(ph, MOTOR_ID, ADDR_TORQUE_ENABLE, 0)
    ph.closePort()
    arduino.close()
    print("Moteur arrêté — connexions fermées.")
