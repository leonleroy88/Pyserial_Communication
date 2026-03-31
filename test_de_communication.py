#!/usr/bin/env python3
"""
Test PySerial — Lecture boutons Arduino
Affiche dans le terminal ce que l'Arduino envoie
"""

import serial

# ── Config ────────────────────────────────────────────────────────
PORT  = "COM5"   # ← adapter si besoin (vérifier gestionnaire périphériques)
BAUD  = 9600     # ← même valeur que Serial.begin() dans l'Arduino

# ── Connexion ─────────────────────────────────────────────────────
print(f"Connexion sur {PORT} @ {BAUD} bps...")

ser = serial.Serial(PORT, BAUD, timeout=1)

print("En écoute — appuyez sur vos boutons (Ctrl+C pour quitter)\n")

# ── Boucle de lecture ─────────────────────────────────────────────
try:
    while True:
        ligne = ser.readline().decode("utf-8").strip()
        if ligne:
            print(ligne)

except KeyboardInterrupt:
    print("\nArrêt.")
    ser.close()