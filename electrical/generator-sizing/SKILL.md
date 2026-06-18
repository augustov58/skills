---
name: generator-sizing
description: Size emergency, standby, or optional generators (gensets) for commercial, institutional, and industrial buildings, including code classification and full load analysis. Use this skill whenever the user wants to size, select, or spec a backup generator, standby generator, emergency generator, EPSS, or genset for a building; mentions NEC Article 700/701/702, NFPA 110, NFPA 101, or NFPA 99 in a power-source context; asks how big a generator they need; needs to classify an emergency power system by Level/Type/Class; needs motor-starting / voltage-dip analysis for a genset; or needs fuel-tank sizing for a generator. Trigger even if they just paste a load list and ask "what size generator," or describe a building and ask for backup power. Walks the user through structured intake, applies the four-constraint sizing method, runs a deterministic sizing script, and cites fixed code/engineering data from bundled references instead of re-searching.
---

# Generator Sizing

Size a building generator correctly the first time by satisfying all four sizing constraints
(running kW, alternator kVA, motor-start voltage dip, engine block-load) AND the applicable
NEC/NFPA code requirements. This skill drives a structured interview, applies deterministic
reference data, and runs a sizing script so the result is reproducible and defensible to an AHJ.

## When this skill is doing its job
The output is: (1) the correct code classification (700/701/702 + NFPA 110 Level/Type/Class),
(2) a transparent four-constraint calculation, (3) a recommended standard genset size with the
governing constraint named, and (4) fuel-tank and key-constraint notes. Every assumption is stated.

---

## Step 0 — Read the references first
Before doing any math or quoting any code, load the bundled reference files. They hold the fixed
data so you never have to look it up:
- `references/motor_data.md` — FLC tables, NEMA code-letter kVA/hp, start-method factors, start PF.
- `references/code_requirements.md` — NEC 700/701/702, NFPA 110 Level/Type/Class, fuel rules,
  fire-pump rules, ISO 8528 ratings, ground-fault/separation constraints.
- `references/sizing_methodology.md` — the four-constraint method, standard sizes, dip rules, margins.

The sizing arithmetic lives in `scripts/size_generator.py`. Do not redo its math by hand; build the
JSON load list and run it.

---

## Step 1 — Intake interview
Ask only for what you can't infer. Group questions; don't interrogate one at a time. Use the
`ask_user_input_v0` tool for the multiple-choice items when available. The minimum you need:

### A. Application & code path
1. **Building type / occupancy?** (office, healthcare, high-rise, data center, industrial, etc.)
   → drives whether 700/701/702 and NFPA 110 Level 1/2 apply.
2. **What must the generator carry?** Get the load list (below). For each, is it life-safety
   (egress, fire alarm, fire pump), code-mandated-but-not-life-safety, or owner-elected?
3. **Is there a fire pump on the generator?** (yes/no + HP) — if yes it usually governs sizing
   and imposes the 15% voltage-dip limit (NEC 695.7).
4. **Existing building with utility demand data, or new construction?**
   → existing + metered data unlocks NEC 220.87 to shrink an optional genset.
5. **Genset role:** backup only (Standby/ESP rating) or prime power (PRP rating)?

### B. Per-load data (build a table)
For every load on the generator:
- Name, category (emergency / legally_required / optional / firepump)
- Kind: **motor** or **static** (lighting, resistive, electronic/UPS)
- Motors: HP, voltage, **NEMA code letter** (nameplate), efficiency, load factor,
  **starting method** (DOL / wye-delta / soft starter / VFD / autotransformer), running PF
- Static: kW, PF, quantity, demand factor
- Whether it's actually on the generator

If the user doesn't know a value, use the documented defaults (code letter G, eff 0.90, start PF
per `motor_data.md`) and **flag the assumption**. Don't stall waiting for perfect data.

### C. Site & sensitivity
- Site **elevation** and **max ambient temperature** → derates.
- Fraction of load that is **nonlinear** (VFD/UPS/SCR) → alternator harmonic derate if >30%.
- Most **voltage-dip-sensitive** load present → sets the dip target (general 20%, lighting 20%,
  fire pump 15%, UPS/electronics 10–15%).
- Required **runtime without refueling** (sets NFPA 110 Class & fuel tank) and **transfer time**
  (Type 10 / 60 / 120).
- Desired **spare capacity** for growth (default 20% optional; size tight for pure life-safety).

---

## Step 2 — Classify (code path)
Using `references/code_requirements.md`:
1. Assign each load to **700 / 701 / 702**. State which ATS arrangement that implies (emergency must
   be separately wired; optional must trip on ground fault; etc.).
2. If life-safety/NFPA 110 applies, assign **Level (1/2)**, **Type (transfer seconds)**, and
   **Class (runtime hours)**. Name the mandating standard (NFPA 101 high-rise, NFPA 99 healthcare).
3. Note the capacity rule that applies: 700.4/701.4 simultaneous load (with optional load-shed), or
   702.4 full-load vs EMS, or 220.87 demand method for existing buildings.

---

## Step 3 — Size (run the script)
Build the JSON load list (schema = the `EXAMPLE` block in `scripts/size_generator.py`) and run:

```bash
python3 scripts/size_generator.py load_list.json
```

The script returns running kW/kVA, the worst-case starting motor and its applied sKVA, the peak
transient, **all four constraint values**, the **governing constraint**, derates (spare applied to
running constraints only), the **recommended standard size**, the **load factor with wet-stacking
warning**, and — when a transient constraint governs — **mitigation options with the kW saved**
(reduced-voltage starting what-ifs computed automatically). Pass `params`: `gen_pf` (0.8 default),
`dip_target_pct` (per the most sensitive load), `altitude_ft`, `ambient_c`,
`harmonic_load_fraction`, `spare_fraction`.

If the fire pump is present, set `dip_target_pct: 15` (or run a separate check) and verify the
locked-rotor sKVA holds ≤15% dip — this often forces a larger alternator than running load implies.

---

## Step 4 — Fuel & final report
1. **Fuel tank:** use the burn-rate table in `code_requirements.md`. Tank gallons ≈
   burn_rate(size, 100%) × Class_hours × 1.33 (NFPA 110 133% rule). Min 2 h per NEC 700.12(B)(2);
   8 h if fire pump (NFPA 20). Note seismic/disaster 96 h interpretation if Level 1.
2. **Report** (use a table): classification; the four constraints with the governing one bolded;
   recommended size + rating type; alternator/derate notes; fuel tank; and a bulleted list of every
   assumption made. End with the OEM-confirmation caveat: final selection must be validated against
   the manufacturer's motor-starting curve and derate sheet at the site elevation/ambient.

---

## Hard rules (don't violate)
- **Size = MAX of the four constraints**, never just running kW. The #1 field failure is a genset
  that runs the building fine but browns out when the biggest motor starts.
- Worst-case motor start = the **largest applied sKVA started last**, on top of the running base.
- **When voltage dip or block load governs, ALWAYS present mitigation options before recommending
  the brute-force size**: reduced-voltage starting on the worst motor (the script computes the kW
  delta automatically), staggered start sequencing, or an oversized alternator frame on the same
  engine. A dip-governed result is a design decision, not just a bigger purchase order — show the
  user what a soft starter saves in genset kW and let them choose.
- **Growth/spare margin applies to the running constraints only** (the script enforces this).
  Never compound spare onto a transient-governed size — it already carries running headroom.
- **Check the load factor on the recommended size.** Below 30% running load on a diesel, flag
  wet-stacking and recommend a load-bank provision (the script flags this automatically).
- **Standby (ESP) rating** for code backup systems; Prime (PRP) only if the genset is the main source.
  Prime kW ≈ 10% below standby kW for the same machine — don't mix rating columns.
- Fire pump → **15% dip limit** and **carry locked-rotor current** (NEC 695.3/695.7), plus 8 h fuel.
- Optional standby (702) has **no ground-fault trip exception** — must trip, unlike 700/701.
- Always **round up** to a standard size and **state the governing constraint** so the result is
  defensible.
- State assumptions explicitly. An AHJ/peer reviewer will challenge code-letter, PF, efficiency, and
  demand-factor defaults — make them visible.
- This sizes the engine-generator. Service/feeder transformer sizing, OCPD selective coordination,
  and conductor sizing are downstream tasks — flag them but don't silently fold them in.

## Editions
Defaults: NEC 2023, NFPA 110-2025, NFPA 101-2024, NFPA 99-2024, NFPA 20-2022. If the user's AHJ
adopts a different cycle, confirm the section numbers may shift and verify the changed ones.
