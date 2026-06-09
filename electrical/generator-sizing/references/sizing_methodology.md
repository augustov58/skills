# Sizing Methodology & Standard Sizes — Deterministic Reference

Cite this file. Methodology synthesized from Cummins, Generac, Kohler, Caterpillar sizing
literature, IEEE 446 (Orange Book), and Consulting-Specifying Engineer sizing articles.

## Table of Contents
1. The four sizing constraints (why a genset is "big enough")
2. Sizing workflow (the algorithm)
3. Standard generator sizes (kW)
4. Voltage-dip / sKVA recovery rules
5. Margin / spare-capacity guidance

---

## 1. The Four Sizing Constraints

A generator must satisfy ALL FOUR. The required size is the **largest** of these.

1. **Running kW (engine).** Sum of steady-state running real power of all loads expected to run
   simultaneously, after demand factors. Engine must carry this continuously without overload at
   the chosen rating.

2. **Running kVA / alternator thermal.** Sum of running apparent power. Alternator is kVA-limited
   and must not overheat. Low-PF and harmonic loads stress this.

3. **Starting / transient kVA (alternator voltage dip).** Largest motor (or simultaneous group)
   starting on top of the already-running base load. The instantaneous voltage dip must stay within
   the allowable for the most sensitive connected load. This is governed by alternator transient
   reactance X″d (subtransient). Typical max dip: 20–35% general, **15% for fire pump (NEC 695.7)**,
   10–15% for UPS/electronics.

4. **Starting / transient kW (engine frequency dip).** The block-load sKW the engine must absorb in
   one step. Governs frequency/RPM dip and recovery. NFPA 110 Level 1 often requires single-step
   acceptance of the full Level 1 load.

The classic failure mode: a genset sized only on running kW stalls or browns out when the biggest
motor starts. Always check constraint 3 (and 4) against the *largest motor starting last* (worst case).

---

## 2. Sizing Workflow (Algorithm)

```
Step 1  Build load list. For each load: type, kW or HP, voltage, PF, qty,
        demand factor, whether on generator, starting method, NEMA code letter.

Step 2  Running totals:
          Running_kW   = Σ (load_kW × demand_factor)
          Running_kVA  = Σ (load_kVA × demand_factor)
        Motor running kW = HP × 0.746 / efficiency × load_factor.

Step 3  Identify worst-case starting motor (the one whose start, applied last
        on top of the running base, produces the largest transient).
          For each motor: DOL_sKVA = HP × (kVA/hp from code letter)
                          applied_sKVA = DOL_sKVA × starting_method_factor
        Worst case is typically the largest applied_sKVA started last.

Step 4  Transient demand at the worst-start instant:
          base_running_kVA = running kVA of everything already on the bus
                             (exclude the motor being started)
          peak_kVA = base_running_kVA + applied_sKVA
          peak_kW  = base_running_kW  + (applied_sKVA × starting_PF)

Step 5  Voltage-dip check (alternator):
          Required alternator must hold the peak_kVA within allowable dip.
          Quick model: dip% ≈ applied_sKVA / (gen_kVA × (1/X″d_pu)) ... but
          OEM motor-starting curves are authoritative. Use the rule:
          a genset can typically start sKVA ≈ (0.7 to 1.0) × its rated kVA at
          a 90% voltage recovery point. Conservative planning factor:
            min_gen_kVA_for_start = applied_sKVA / max_startable_ratio
          where max_startable_ratio ≈ 0.65 for 20% dip target (use 0.65 default;
          0.45 for the tighter 15% fire-pump dip; verify on OEM curve).

Step 6  Size = MAX of:
          (a) Running_kW / gen_PF                → running kW need
          (b) Running_kVA                        → alternator thermal need
          (c) min_gen_kVA_for_start (→ kW at PF) → transient voltage dip need
          (d) peak_kW                            → engine block-load need
        Then convert kVA needs to kW at genset PF (0.8) and take the max kW.

Step 7  Apply derates (altitude, temperature, harmonics) to the OEM rating,
        then add margin, then round UP to the next standard size.
```

---

## 3. Standard Generator Sizes (kW) — round UP to one of these

Diesel/gas standby gensets are built in discrete frames. Common North-American kW ratings:

```
20, 25, 30, 35, 40, 50, 60, 80, 100, 125, 150, 175, 200, 230, 250, 300,
350, 400, 450, 500, 600, 750, 800, 1000, 1250, 1500, 1750, 2000, 2250, 2500, 2750, 3000
```

(OEM model lineups vary slightly. After computing required kW, present the next standard size up
and note the OEM model family is to be confirmed from the manufacturer's spec sheet at the site
elevation/ambient.)

---

## 4. Voltage-Dip / sKVA Recovery Rules

- NEMA / industry convention: alternator must recover to **≥90% of rated no-load voltage** after the
  specified motor-starting (low-PF) kVA is applied. This is the standard motor-starting spec language.
- Maximum allowable instantaneous dip by load sensitivity:

| Connected load type            | Max instantaneous voltage dip |
|--------------------------------|-------------------------------|
| General motor loads / HVAC     | 30–35%                        |
| Lighting present (flicker)     | 20%                           |
| Fire pump (NEC 695.7)          | 15%                           |
| UPS / electronics / VFD logic  | 10–15%                        |
| Sensitive (some static UPS)    | frequency rate < 1 Hz/s also  |

- Frequency dip: most loads tolerate up to ~10 Hz dip; some static UPS trip above ~1 Hz/s rate of
  change. Engine block-load capability (constraint 4) governs this.

---

## 5. Margin / Spare Capacity Guidance

- Standby gensets are happiest loaded **30–80%**. Chronic light loading (<30%) on diesels causes
  wet stacking — flag if computed load is a small fraction of the rounded size.
- Add **10–25% spare** for future growth unless the user says otherwise (default 20% for optional
  standby; for code/life-safety size strictly to the required load unless owner wants growth room).
- If running load lands at >85% of a standard size, jump to the next size for headroom.
- Document every assumption (code letter defaults, PF defaults, efficiency, demand factors) — these
  are the levers an AHJ or peer reviewer will question.
