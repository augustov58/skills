---
name: transformer-sizing-design
description: "Size and design a complete dry-type transformer installation for a commercial or industrial building per NEC 2023 (Articles 450.3, 450.21, 240.21(C), 250.30, 408.36). Use whenever the user wants to size a transformer, select a kVA rating, design a step-down (e.g. 480V to 208Y/120V), pick primary or secondary overcurrent protection, size a transformer feeder or secondary tap conductors, apply the tap rules to a transformer secondary, ground a separately derived system, choose a K-factor for nonlinear loads, or check transformer clearance, ventilation, room, or vault requirements. Trigger even on partial asks like 'what size transformer for a 200A panel', 'size the OCPD for a 75 kVA xfmr', or when the user uploads a panel schedule and wants a transformer fed from it. This skill is INTAKE-DRIVEN: it asks for the inputs that change the code outcome before producing numbers, so it never silently guesses voltage, phase, load basis, OCPD configuration, or conductor material."
---

# Transformer Sizing & Installation Design (NEC 2023)

Sizing a transformer is not one number. It is a chain of coupled decisions where one early assumption silently changes a downstream code result. The classic errors all come from skipping the intake: assuming primary-only protection when the design has a secondary main (wrong OCPD column), assuming copper when the contractor buys aluminum (wrong wire size), applying a power factor to a load that was already in kVA (oversized unit), or treating a wye-wye with a bonded neutral as a separately derived system when it is not (wrong grounding scheme entirely).

So this skill runs **intake first**, then a **deterministic calculator**, then **judgment** for the parts code leaves to the engineer. This is work that gets signed and plan-reviewed. Do not improvise the arithmetic — the rounding rules in Table 450.3(B) are asymmetric and the 9 A threshold is easy to miss by hand.

Written against the 2023 NEC (Florida adopts 2023 via the FBC). The 450.3(B) percentages and 250.30 SDS rules have been stable across recent cycles, but if the user is on a different edition, confirm and note it.

---

## Step 0 — Intake. Do this before any number.

Ask only for gaps. If the user gave a load and voltages in chat, a panel schedule, or a load calc, extract those and don't re-ask. Infer sane defaults and **state them inline** rather than stalling — but never silently assume any of the four outcome-changing inputs marked ⚠.

In a chat interface, use `ask_user_input_v0` for the gaps (phase, protection config, conductor material make good tappable choices). Group into one round; don't interrogate one item at a time. If the user uploaded a panel schedule or the `load-calc-generator` skill produced a demand total, read it and pre-fill.

**A. Load basis — what are we sizing to?**
1. Demand/connected load: kVA, or kW + power factor, or a panel total in amps. ⚠ If given kW with no PF, do **not** assume it's already apparent power — ask, or default PF 0.9 mixed-commercial / 0.8 motor-heavy and say so.
2. Is the load already demand-adjusted (post-Article 220) or a raw connected total? Sizing to raw connected oversizes the unit and wastes no-load losses for 30 years. Prefer demand. If there's a building to calculate and `load-calc-generator` is available, suggest it first.
3. Spare capacity: default 25% headroom (size so demand ≈ 80% of nameplate). This is engineering practice, not an NEC mandate — say so.

**B. Voltages & configuration ⚠**
4. Primary voltage (480, 480Y/277, 208…). 5. Secondary voltage (208Y/120, 480Y/277, 240/120 1φ…). 6. Phase: 1φ or 3φ — drives the √3 in every formula. 7. Connection (Δ-Y, Δ-Δ, Y-Y). Decides whether you have a **separately derived system** (Step 4). A 480Δ–208Y/120V step-down *is* an SDS; a Y-Y with a factory H0-X0 neutral link is *not*.

**C. Protection configuration ⚠**
8. Primary-only, or primary **and** secondary protection? This one choice moves the max primary OCPD from **125%** to **250%** of primary FLA. A secondary main breaker or a downstream panel main = secondary protection present. If the secondary feeds tap conductors to a downstream OCPD, you also work 240.21(C).
9. Primary current ≥ 9 A? Below 9 A (and below 2 A) the table allows higher multipliers. The calculator checks this; most commercial units are well above 9 A.

**D. Conductors & environment ⚠**
10. Conductor material: copper or aluminum. 11. Termination temp rating: size terminations at the **75°C** column for most commercial gear even if the wire is 90°C-rated. 12. Ambient / conductor count for derating (default 30°C, ≤3 CCC, no derate — state it). 13. Secondary run length transformer → first OCPD (≤10 ft, 10–25 ft, outside) to pick the tap rule.

**E. Type & load character**
14. Dry-type (standard indoor commercial) or liquid-filled. 15. Nonlinear load fraction (LED drivers, VFDs, servers, UPS) → K-factor + possible 200% neutral. 16. Indoor/outdoor & enclosure (NEMA 1 / 3R).

**Do not produce numbers until items 1, 4, 5, 6 are known and items 8 and 13 are known or explicitly defaulted with the default stated.**

---

## Step 1 — Run the calculator. Don't hand-calculate.

The deterministic sizer does FLA, kVA selection to the next standard NEMA size, OCPD per Table 450.3(B) (with the 9 A / 2 A branches and the Note-1 rounding asymmetry), a first-pass 75°C conductor size, 240.21(C) tap-rule selection, and 250.30 grounding-conductor sizing.

```bash
python3 scripts/size_transformer.py \
  --load-kva 95 \
  --primary-v 480 --primary-phase 3 \
  --secondary-v 208 --secondary-phase 3 \
  --secondary-ocpd yes \
  --spare 0.25 --nonlinear-pct 40 \
  --conductor cu --sec-length 8
```

Size from a known kVA instead of a load with `--kva 75`. Size from kW with `--load-kw 60 --pf 0.9`. Full flags: `--help`.

The script prints every intermediate value (FLA, raw %, the standard size it rounded to, the table cell) plus an **ASSUMPTIONS** block and a **FLAGS / VERIFY** block. **Read the assumptions and flags back to the user.** If any assumption is wrong, rerun. Never paste a bare number — show the rule next to it.

Standard 3φ kVA: 15 30 45 75 112.5 150 225 300 500 750 1000 1500 2000 2500. Standard OCPD per 240.6(A): 15 20 25 30 35 40 45 50 60 70 80 90 100 110 125 150 175 200 225 250 300 …

---

## Step 2 — Resolve what the calculator flags (judgment + lookup)

The script gives numbers; these need a confirmation against `references/nec-requirements.md` when the relevant flag fires:

- **Tap rule (240.21(C))** — the script names the scenario from the length. Confirm the secondary conductor it sized meets that scenario's ampacity floor: the 10-ft rule needs ampacity ≥ load *and* ≥ ⅒ of (primary OCPD × V_pri/V_sec); the 25-ft rule needs ≥ ⅓ of that. Both require termination in a single OCPD.
- **Room / clearance (450.21)** — flag fires at the 112.5 kVA boundary. > 112.5 kVA dry-type → 1-hour fire-rated room (unless a Class-155 exception). ≤ 112.5 kVA → 12 in from combustibles unless a fire-rated barrier. > 35 kV → vault. Confirm against the actual location.
- **Grounding (250.30)** — script sizes the system bonding jumper and GEC. You decide *where* the single N-G bond lands (transformer vs. secondary disconnect, never both) and confirm the electrode (building steel / water pipe within 5 ft of entry).
- **Inrush** — script flags primary-only at 125% as nuisance-trip-prone on DOE-2016/K-rated units. Resolve by adding secondary protection + 250% primary, or a high-instantaneous device (D-curve MCB / adjustable STD MCCB set above 8–12× FLA).
- **Panelboard (408.36)** — if the secondary feeds a panelboard, confirm bus rating ≥ secondary OCPD and the panel is protected at its rating.

Read `references/sizing-methodology.md` for the *why* when the user pushes back: temperature-rise classes, DOE 2016 efficiency, impedance/inrush physics, ambient/altitude/harmonic derating.

---

## Step 3 — Deliver

Default deliverable: a markdown schedule the user can drop into a one-line or submittal, **with the governing NEC section cited next to each number** so a plan reviewer can check it.

```
## Transformer Schedule — T-1
- Rating / type:     75 kVA, 3φ, dry-type, K-13, NEMA 1
- Voltage:           480V Δ primary → 208Y/120V wye secondary (SDS)
- Primary FLA:       90.2 A     Secondary FLA: 208.2 A
- Primary OCPD:      225 A   (Table 450.3(B), pri+sec, ≤250%)
- Secondary OCPD:    300 A   (Table 450.3(B), ≤125% sec FLA)
- Primary feeder:    <size> Cu, <conduit>      (75°C, verify derating)
- Secondary cond.:   <size> Cu, 240.21(C)(2) 10-ft
- Grounding (SDS):   SBJ <size> per 250.102(C)(1); GEC <size> per 250.66 to bldg steel; bond at xfmr
- Install:           <12 in clearance / 1-hr room / vault per size>
- Assumptions:       <PF, spare, 75°C term, Cu, ambient> — all listed explicitly
```

State every assumption in one explicit block. For any ⚠ input that was assumed rather than confirmed, say what changes if it's wrong (e.g. "if primary-only, the primary breaker drops to 125 A and the secondary conductors lose their protection path").

Offer — don't build unprompted — a formatted artifact: a transformer-schedule spreadsheet (use the xlsx skill), a one-line diagram (SVG via the visualizer), or a spec section (docx skill).

---

## Reference files
- `references/nec-requirements.md` — Table 450.3(B) both rows + notes, 240.21(C) all scenarios, 250.30 grounding, 450.21/450.9/450.13 installation, 408.36 panelboard. Read when a flag fires or a number is challenged.
- `references/sizing-methodology.md` — FLA formulas, kVA-selection logic, temp-rise classes, DOE 2016 efficiency, impedance/inrush, K-factor, derating. Read for explanations and trade-offs.

## Scripts
- `scripts/size_transformer.py` — Deterministic sizer; the single source of truth for numbers. Always run it.
