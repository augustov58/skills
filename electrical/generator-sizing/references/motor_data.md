# Motor Data — Deterministic Reference

This file holds fixed engineering data. Do NOT look these up online; cite this file.
Sources: NEC 2023 Tables 430.250 / 430.7(B), NEMA MG-1, generator OEM sizing literature
(Cummins, Generac, Kohler), IEEE 446 (Orange Book).

## Table of Contents
1. Three-Phase Motor Full-Load Current (NEC 430.250)
2. NEMA Code Letters — Locked Rotor kVA/hp (NEC 430.7(B))
3. Starting Method Multipliers (sKVA reduction)
4. Motor Starting kW vs kVA (power factor at start)
5. Running kW per HP

---

## 1. Three-Phase Motor Full-Load Current — NEC Table 430.250 (Amps)

Use these for running-load and FLC-based calculations. Induction-type, squirrel cage & wound rotor.

| HP   | 208V | 230V | 460V | 575V |
|------|------|------|------|------|
| 0.5  | 2.4  | 2.2  | 1.1  | 0.9  |
| 0.75 | 3.5  | 3.2  | 1.6  | 1.3  |
| 1    | 4.6  | 4.2  | 2.1  | 1.7  |
| 1.5  | 6.6  | 6.0  | 3.0  | 2.4  |
| 2    | 7.5  | 6.8  | 3.4  | 2.7  |
| 3    | 10.6 | 9.6  | 4.8  | 3.9  |
| 5    | 16.7 | 15.2 | 7.6  | 6.1  |
| 7.5  | 24.2 | 22   | 11   | 9    |
| 10   | 30.8 | 28   | 14   | 11   |
| 15   | 46.2 | 42   | 21   | 17   |
| 20   | 59.4 | 54   | 27   | 22   |
| 25   | 74.8 | 68   | 34   | 27   |
| 30   | 88   | 80   | 40   | 32   |
| 40   | 114  | 104  | 52   | 41   |
| 50   | 143  | 130  | 65   | 52   |
| 60   | 169  | 154  | 77   | 62   |
| 75   | 211  | 192  | 96   | 77   |
| 100  | 273  | 248  | 124  | 99   |
| 125  | 343  | 312  | 156  | 125  |
| 150  | 396  | 360  | 180  | 144  |
| 200  | 528  | 480  | 240  | 192  |
| 250  | —    | 602  | 302  | 242  |
| 300  | —    | —    | 361  | 289  |
| 350  | —    | —    | 414  | 336  |
| 400  | —    | —    | 477  | 382  |
| 450  | —    | —    | 515  | 412  |
| 500  | —    | —    | 590  | 472  |

**Single-phase quick ref (NEC 430.248), 230V:** 1hp=8A, 2hp=12A, 3hp=17A, 5hp=28A, 7.5hp=40A, 10hp=50A.

---

## 2. NEMA Code Letters — Locked-Rotor kVA per HP — NEC 430.7(B)

This is the single most important table for **motor starting** sizing. The code letter is stamped
on the motor nameplate. It defines the locked-rotor (inrush) apparent power at start.

**Locked Rotor kVA = HP × (kVA/hp factor)**

| Code Letter | kVA/hp Range  | Use Value (midpoint) |
|-------------|---------------|----------------------|
| A           | 0–3.14        | 1.6                  |
| B           | 3.15–3.54     | 3.3                  |
| C           | 3.55–3.99     | 3.8                  |
| D           | 4.0–4.49      | 4.25                 |
| E           | 4.5–4.99      | 4.75                 |
| F           | 5.0–5.59      | 5.3                  |
| G           | 5.6–6.29      | 5.9                  |
| H           | 6.3–7.09      | 6.7                  |
| J           | 7.1–7.99      | 7.5                  |
| K           | 8.0–8.99      | 8.5                  |
| L           | 9.0–9.99      | 9.5                  |
| M           | 10.0–11.19    | 10.6                 |
| N           | 11.2–12.49    | 11.8                 |
| P           | 12.5–13.99    | 13.25                |
| R           | 14.0–15.99    | 15.0                 |
| S           | 16.0–17.99    | 17.0                 |
| T           | 18.0–19.99    | 19.0                 |
| U           | 20.0–22.39    | 21.2                 |
| V           | 22.4 and up   | 23.0                 |

**Default when nameplate unknown:** Code G (≈5.9 kVA/hp) for standard NEMA Design B motors.
Modern high-efficiency (NEMA Premium / IE3+) motors often pull Code H–K (6.3–9 kVA/hp).
When in doubt and efficiency is high, use **Code H (6.7)**.

**Rule of thumb fallback:** Locked-rotor amps ≈ 6 × FLC for older motors, up to ~10–11 × FLC
for high-efficiency motors. Always prefer the code-letter method when the letter is known.

---

## 3. Starting Method Multipliers — applied to full-voltage (DOL) locked-rotor kVA

The starting method drastically reduces the sKVA the generator sees. Multiply the DOL
locked-rotor kVA by the factor below.

| Starting Method           | sKVA Factor | Starting Torque Factor | Notes |
|---------------------------|-------------|------------------------|-------|
| Direct-on-line (DOL)      | 1.00        | 1.00                   | Worst case for genset. Default if unknown. |
| Autotransformer 80% tap   | 0.64        | 0.64                   | |
| Autotransformer 65% tap   | 0.42        | 0.42                   | |
| Autotransformer 50% tap   | 0.25        | 0.25                   | |
| Wye-Delta (star-delta)    | 0.33        | 0.33                   | Open transition causes a 2nd transient. |
| Part-winding              | 0.60–0.70   | 0.50                   | Use 0.65. |
| Soft starter (SCR)        | 0.30–0.50   | varies                 | Use 0.40; adds harmonics (derate alternator). |
| VFD                       | 0.10–0.20   | full                   | Use 0.15; near-zero inrush, but harmonics — see harmonics derate. |

---

## 4. Motor Starting Power Factor (for converting sKVA → sKW)

At locked rotor, motors are highly inductive. Starting power factor is low.

| Motor HP Range | Starting PF | Use for sKW = sKVA × PF |
|----------------|-------------|--------------------------|
| < 100 hp       | 0.30        | |
| 100–1000 hp    | 0.20        | |
| > 1000 hp      | 0.15        | |

**Starting kW (sKW) = Starting kVA (sKVA) × Starting PF.** This is the transient power the
engine (not just the alternator) must absorb. Engine block-load capability governs frequency dip.

---

## 5. Running kW per HP (for steady-state engine load)

**Running kW = HP × 0.746 / motor efficiency**

| Motor Efficiency | kW per HP |
|------------------|-----------|
| 0.85 (standard)  | 0.878     |
| 0.90 (high-eff)  | 0.829     |
| 0.93 (premium)   | 0.802     |

Default efficiency 0.90 if unknown. Driven equipment may not load motor to 100% nameplate —
if a load factor is known (e.g., pump at 80% BHP), apply it.
