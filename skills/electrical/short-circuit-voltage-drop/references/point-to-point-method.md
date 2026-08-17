# Point-to-Point Method — Deterministic Reference

This file holds the fixed procedure. Do NOT look it up online or re-derive it; cite this file.
Source: Eaton/Bussmann *Selecting Protective Devices* (SPD), 2014 edition, pages 237–243.
The scripts implement exactly what is written here, so if a number is challenged, the audit
trail is: printed handbook → this file → `scripts/spd_tables.py` → `scripts/verify_spd.py`.

## Table of Contents

1. The six-step procedure
2. Step 4 — the "f" factor, all three forms
3. Notes 1–5 — the adjustments that change the answer
4. Fault at a downstream transformer with a known primary fault (Steps A–C)
5. Single-phase center-tapped transformers — the half-winding problem
6. Motor contribution
7. Voltage drop — the volt-loss method
8. What this method does NOT do

---

## 1. The six-step procedure

```
Step 1  Transformer full-load amps
          3-phase:  I_FLA = kVA x 1000 / (E_L-L x 1.732)
          1-phase:  I_FLA = kVA x 1000 / E_L-L

Step 2  Transformer multiplier
          Multiplier = 100 / %Z_transformer

Step 3  Transformer let-through short-circuit current
          I_s.c. = I_FLA x Multiplier

Step 4  The "f" factor for the conductor run (see section 2)

Step 5  M = 1 / (1 + f)

Step 6  I_s.c. at the fault point
          I_s.c.sym.RMS = I_s.c. x M

Step 6A Add motor contribution, if significant (see section 6)
```

Then repeat Steps 4–6 for the next run, carrying the current forward. That carry-forward is
the whole method: **f compounds**, so one wrong "C" value moves every downstream number.

**Why %Z gives the fault current.** Transformer impedance is measured by shorting the
secondary and raising primary voltage until rated secondary current flows. That applied
voltage divided by rated primary voltage, times 100, is %Z. So at full rated voltage the
secondary delivers `100/%Z` times its rated current into a bolted fault. A 480 V primary
needing 9.6 V to drive full secondary current is a 2%Z transformer.

---

## 2. Step 4 — the "f" factor, all three forms

```
3-phase faults          f = 1.732 x L x I_3-phase / (C x n x E_L-L)

1-phase line-to-line    f = 2 x L x I_L-L / (C x n x E_L-L)

1-phase line-to-neutral f = 2 x L x I_L-N / (C x n x E_L-N)

  L = length in feet of conductor to the fault
  C = constant from Table 4 (conductors) or Table 5 (busway)
  n = conductors per phase (parallel runs)
  I = available short-circuit current in amperes at the BEGINNING of the run
  E = voltage of the circuit
```

**The 1.732 vs 2 is not a typo.** A three-phase fault loop is one conductor's impedance
scaled by √3. A single-phase fault traverses the run twice — out on one conductor and back
on the other — so the length doubles. Using 1.732 on a single-phase circuit understates the
impedance by 15% and overstates the fault current.

**The scripts use 1.732, not `math.sqrt(3)`.** The handbook prints 1.732 and carries it
through every worked example. `sqrt(3)` shifts results ~0.03% and stops the output matching
the printed page, which would make `verify_spd.py` useless as an audit.

**"C" is one-over-impedance-per-foot**, so a bigger C is a lower-impedance conductor. It
depends on material, size, **raceway** (steel is magnetic and raises AC resistance and
reactance), conductor arrangement (three singles vs a three-conductor cable), and voltage
class. Picking the wrong raceway column is the most common quiet error — for 500 kcmil Cu
the 600 V steel value is 22,185 and the non-magnetic value is 26,706, a 20% swing.

---

## 3. Notes 1–5 — the adjustments that change the answer

| Note | What it says | Effect |
|---|---|---|
| 1 | %Z from the nameplate, or Table 1 if unknown | Nameplate always wins |
| 2 | UL 1561 allows ±10% on the nameplate %Z of transformers 25 kVA and larger. ANSI-built units are ±7.5% | **×0.9 for the maximum fault; ×1.1 for the minimum** |
| 3 | Utility voltages vary ±10% for power and ±5.8% for 120 V lighting | ×1.1 or ×1.058 for the high case; ×0.9 or ×0.942 for the low |
| 4 | Motor contribution ≈ 4× motor FLA (4 to 6 commonly accepted) | See section 6 |
| 5 | At a 1-phase center-tapped transformer's terminals, `I_L-N = 1.5 × I_L-L` | L-N is the governing fault THERE |

**Which direction is worst case depends on what you are checking.**

- **Interrupting rating (110.9), withstand rating (110.10), arc-flash worst case** →
  you need the **maximum** fault. Use `--z-tolerance high` (×0.9). This is the script default
  and what every printed SPD example uses.
- **Series ratings, ground-fault pickup, "will the breaker actually trip"** → you need the
  **minimum** fault. Use `--z-tolerance low` (×1.1), and consider `--utility low`.

Running only the maximum case and calling it a study is the single most common failure in
a first-pass calculation.

**Note 5 detail.** At some distance from the terminals the L-N fault falls *below* the L-L
fault. The 1.5 multiplier is an approximation that varies 1.33–1.67 depending on the turns
ratio, and it assumes an infinite source, zero feet from the terminals, 1.2 × %X and
1.5 × %R for L-N vs L-L. Begin L-N calculations at the secondary terminals, then proceed
point-to-point — do not apply 1.5 downstream.

---

## 4. Fault at a downstream transformer with a known primary fault (Steps A–C)

Use this when you know the fault available at a transformer's **primary** — from the utility
letter, or because you just calculated it point-to-point — and want the secondary.

```
Step A  3-phase:  f = I_s.c.primary x V_primary x 1.732 x %Z / (100,000 x kVA_transformer)
        1-phase:  f = I_s.c.primary x V_primary x %Z / (100,000 x kVA_transformer)

Step B  M = 1 / (1 + f)

Step C  I_s.c.secondary = (V_primary / V_secondary) x M x I_s.c.primary
```

The printed Step A shows `1.73`, but every worked example carries `1.732`. The scripts use
1.732; reproducing SPD System B fault X₄ (32,842 A printed) requires it.

Apply the Note 2 tolerance factor to this transformer's %Z too — `--z-tolerance` propagates
to downstream transformer segments unless the segment overrides it.

**Motor contribution does not cross a transformer.** It is a different voltage. Motors on
the secondary must be counted separately at the secondary; the script flags this.

---

## 5. Single-phase center-tapped transformers — the half-winding problem

Three things differ from the 3-phase procedure (SPD p.239):

1. **Primary conductor impedance is counted both ways.** The 3-phase formula compensates by
   multiplying single-conductor impedance by 1.732; the 1-phase formula multiplies the
   3-phase primary source impedance by two.
2. **The transformer impedance must be adjusted for the half winding.** During an L-N fault
   the full primary winding is involved but only *half* the secondary winding is. The actual
   %R and %X of that condition differ from the full-winding nameplate:

   | Basis | %R multiplier | %X multiplier |
   |---|---|---|
   | Full-winding nameplate %R / %X | **1.5** | **1.2** |
   | Half-winding kVA base (½ nameplate kVA ÷ secondary L-N volts) | **0.75** | **0.6** |

   These are the same adjustment expressed on two different bases — 1.5/2 = 0.75 and
   1.2/2 = 0.6. The "Impedance Data for Single-Phase Transformers" table prints the
   half-winding column; SPD p.239 prints the full-winding column. Mixing them halves or
   doubles the answer. Above 167 kVA the tabulated %X multiplier is 1.0, not 0.6.
3. **Cable impedance counts both ways.** An L-L fault 50 ft from the transformer includes
   100 ft of cable impedance. The `2 × L` in the f-factor is exactly this.

The scripts implement the Note-5 terminal multiplier and the `2 × L` doubling. They do
**not** decompose %Z into %R and %X — that requires nameplate %R and %X, and the resulting
half-winding calculation is a separate exercise. When the user has %R and %X and needs the
half-winding treatment, use the multipliers above by hand and pass the adjusted %Z.

---

## 6. Motor contribution

A running induction motor is a generator for the first few cycles after a fault. SPD's
practical estimate:

```
I_motor contribution = 4 x (total motor full-load amps)
```

Values of 4 to 6 are commonly accepted; 4 is the SPD default. Two rules that are easy to
get wrong:

- **It is added at every fault location, undiminished.** The motors sit downstream of the
  conductor run, so their contribution does not pass through the run's impedance on the way
  to the fault. Attenuating it by M is wrong.
- **When only part of the load is motors, scale the FLA, not the multiplier.** SPD System A
  assumes 100% motor load; its own footnote shows the 50% case as
  `4 × 1804 × 0.5 = 3,608 A`.

---

## 7. Voltage drop — the volt-loss method

```
volt loss = feet x amperes x table figure / 1,000,000 / conductors-per-phase

wire selection:  needed figure = permissible volt loss x 1,000,000 / (feet x amperes)
                 then pick the largest tabulated figure NOT ABOVE that number
```

Tables A (copper) and B (aluminum) give the figure by size, raceway, phase, and power
factor. **The figure already includes reactance**, which is why the same wire in steel and
in PVC gives different answers and why the familiar `2 × K × I × L / cmil` shortcut cannot
reproduce these numbers. On large conductors reactance dominates and the figure *rises* as
power factor falls; on small conductors resistance dominates and it falls. Both behaviors
are in the table.

All figures are **line-to-line**, and the three-phase figures are the average of the three
phases. For line-to-neutral volts, divide the three-phase value by 1.73 or the single-phase
value by 2 — but on a balanced circuit the **percent** drop is unchanged, because the
reference voltage divides by the same factor. Quoting line-to-neutral volts against a
line-to-line nominal voltage halves the reported drop; that is the classic way to make a
failing feeder look compliant.

**Open wiring** volt loss depends on conductor separation and is approximately equal to the
non-magnetic-conduit values.

---

## 8. What this method does NOT do

Point-to-point is a first-pass hand method. It is not a substitute for a modeled study.

- **No arc-flash / incident energy.** Table 3 gives arcing fault current as a percentage of
  the bolted value; incident energy needs IEEE 1584 with clearing times from the actual
  device curves. The label required by 110.16 does not come from this calculation.
- **No X/R ratio tracking.** The method works in magnitudes. Asymmetrical peak current, DC
  offset, and the multiplying factors used to check a device's *asymmetrical* rating need
  the X/R ratio, which the transformer tables give but this procedure does not carry.
- **Impedance of everything except conductors and transformers is ignored** — terminations,
  bus stabs, CT windings, current-limiting reactors, the utility source itself when an
  "infinite bus" is assumed. The result is therefore slightly **high**: conservative for an
  interrupting-rating check, optimistic for a minimum-fault check.
- **No generators, no paralleled sources, no network transformers, no motor-plant decay.**
  Those need per-unit or symmetrical components (IEEE 141 Red Book, IEEE 242 Buff Book).
- **Voltage drop is steady-state.** Motor-starting dip is a different calculation — see the
  `generator-sizing` skill for the transient case.
