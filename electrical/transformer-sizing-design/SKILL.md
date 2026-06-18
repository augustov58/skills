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
8. Primary-only, or primary **and** secondary protection? A secondary main breaker or a downstream panel main = secondary protection present; if the secondary feeds tap conductors to a downstream OCPD you also work 240.21(C).
9. **Primary OCPD basis — default 125%, NOT 250%.** Table 450.3(B) *raises the ceiling* to 250% of primary FLA when secondary protection exists, but that is a maximum, not a target. 450.3(B) protects the **transformer**; the **conductor** is protected independently by 240.4. On a normal radial feeder the *same* device does both jobs, so the primary OCPD can't exceed what 240.4(B) allows for a 125%-FLA-sized primary conductor — which lands you right back at 125%. Going to 250% forces the primary conductor up to the breaker rating (e.g. 2 AWG → 4/0) for zero benefit. So **default `--primary-basis min` (125%)** and only escalate when one of these is true:
   - **Inrush nuisance-tripping** on a high-efficiency/K-rated unit → `--primary-basis inrush`. The script will upsize the primary conductor to match and warn you it only buys inrush margin.
   - **Primary is a 240.21(B) tap** off a larger feeder (not a dedicated radial breaker) → `--primary-tap`. Then the tap rules, not the OCPD, protect the conductor; the script flags it for hand-verification against the upstream feeder.
10. Primary current ≥ 9 A? Below 9 A (and below 2 A) the table allows higher multipliers and the max can fall below the smallest standard breaker (control transformers are protected by the upstream branch OCPD). The calculator checks this.

**C2. Downstream panel ⚠**
12. If the secondary feeds a panelboard, get its **bus ampere rating** (`--panel-bus`). The secondary OCPD is capped at the bus rating (408.36) even when 125% of secondary FLA would allow more — this is the classic "300 A breaker on a 225 A panel" trap. Also watch the inverse: if the transformer's secondary FLA is *below* the panel bus, the panel can be loaded past the transformer's rating (the script flags this capacity mismatch).

**D. Conductors & environment ⚠**
13. Conductor material: copper or aluminum. 14. Termination temp (110.14(C)): default `--term-temp auto` — the script uses the **60°C** column for circuits ≤100 A (by OCPD) and **75°C** above, which is what 110.14(C)(1) requires unless the gear is listed otherwise. Force `--term-temp 75` only if you've confirmed 75°C terminations on a small unit. 15. Ambient / conductor count for derating (default 30°C, ≤3 CCC, no derate — state it). 16. Secondary run length transformer → first OCPD (≤10 ft, 10–25 ft, outside) to pick the tap rule.

**E. Type & load character**
17. Dry-type (standard indoor commercial) or liquid-filled. 18. Nonlinear load fraction (LED drivers, VFDs, servers, UPS) → K-factor + possible 200% neutral. 19. Indoor/outdoor & enclosure (NEMA 1 / 3R).

**Do not produce numbers until items 1, 4, 5, 6 are known and items 8 and 16 (protection config and secondary run length) are known or explicitly defaulted with the default stated. Default `--primary-basis min` and `--term-temp auto` unless a reason to change is established.**

---

## Step 1 — Run the calculator. Don't hand-calculate.

The deterministic sizer does FLA, kVA selection to the next standard NEMA size, OCPD per Table 450.3(B) (with the 9 A / 2 A branches and the Note-1 rounding asymmetry), the **primary OCPD↔conductor coupling** (125% default, gated 250%), the **panel-bus cap** on the secondary OCPD, a first-pass 60/75°C conductor size, 240.21(C) tap-rule selection *with the actual ampacity floor computed*, and 250.30 grounding-conductor sizing.

```bash
python3 scripts/size_transformer.py \
  --load-kva 65 \
  --primary-v 480 --primary-phase 3 \
  --secondary-v 208 --secondary-phase 3 \
  --secondary-ocpd yes --panel-bus 225 \
  --spare 0 --conductor cu --sec-length 8
```

Size from a known kVA with `--kva 75`, from kW with `--load-kw 60 --pf 0.9`, or from a panel amp total with `--load-amps 180` (interpreted at the secondary voltage). Pass `--spare 0` when the load figure already includes headroom (e.g. "80% of bus"). Escalate the primary only with `--primary-basis inrush` (high-inrush unit) or `--primary-tap` (240.21(B) tap). Full flags: `--help`.

The script prints every intermediate value (FLA, raw %, the standard size it rounded to, the table cell) plus an **ASSUMPTIONS** block and a **FLAGS / VERIFY** block. **Read the assumptions and flags back to the user.** If any assumption is wrong, rerun. Never paste a bare number — show the rule next to it.

Standard 3φ kVA: 15 30 45 75 112.5 150 225 300 500 750 1000 1500 2000 2500. Standard OCPD per 240.6(A): 15 20 25 30 35 40 45 50 60 70 80 90 100 110 125 150 175 200 225 250 300 …

---

## Step 2 — Resolve what the calculator flags (judgment + lookup)

The script gives numbers; these need a confirmation against `references/nec-requirements.md` when the relevant flag fires:

- **Tap rule (240.21(C))** — the script now *computes* the floor, not just names the scenario: 10-ft needs ampacity ≥ load *and* ≥ ⅒ of (primary OCPD × V_pri/V_sec); 25-ft needs ≥ ⅓. It prints OK / TOO SMALL. Both require termination in a single OCPD. Confirm the run truly stays within the length and enclosure conditions.
- **Room / clearance (450.21)** — flag fires at the 112.5 kVA boundary. > 112.5 kVA dry-type → 1-hour fire-rated room (unless a Class-155 exception). ≤ 112.5 kVA → 12 in from combustibles unless a fire-rated barrier. > 35 kV → vault. Confirm against the actual location.
- **Grounding (250.30)** — script sizes the system bonding jumper and GEC. You decide *where* the single N-G bond lands (transformer vs. secondary disconnect, never both) and confirm the electrode (building steel / water pipe within 5 ft of entry).
- **Primary OCPD basis / inrush** — script defaults to 125% and couples the conductor. If the user reports (or you expect) energization nuisance trips on a high-efficiency/K-rated unit, rerun with `--primary-basis inrush`: the breaker rises toward 250% **and the primary conductor is upsized to match** (240.4). Never present a >125% primary breaker on a 125%-sized conductor — that was the old bug. The alternative to upsizing is a high-instantaneous device (D-curve MCB / adjustable-magnetic MCCB set above 8–12× FLA) left at 125% thermal.
- **Panelboard (408.36)** — pass `--panel-bus`; the script caps the secondary OCPD at the bus and flags the capacity mismatch if the transformer FLA is below the bus. Confirm the panel main ≤ bus rating.

Read `references/sizing-methodology.md` for the *why* when the user pushes back: temperature-rise classes, DOE 2016 efficiency, impedance/inrush physics, ambient/altitude/harmonic derating.

---

## Step 3 — Deliver

Default deliverable: a markdown schedule the user can drop into a one-line or submittal, **with the governing NEC section cited next to each number** so a plan reviewer can check it.

```
## Transformer Schedule — T-1   (example: 75 kVA, 180 A load, 225 A panel)
- Rating / type:     75 kVA, 3φ, dry-type, NEMA 1 (K-13 only if >35% nonlinear)
- Voltage:           480V Δ primary → 208Y/120V wye secondary (SDS)
- Primary FLA:       90.2 A     Secondary FLA: 208.2 A
- Primary OCPD:      125 A   (Table 450.3(B), 125% basis; coupled to 2 AWG feeder per 240.4(B))
- Secondary OCPD:    225 A   (capped at panel bus, 408.36; ≤260 A 450.3(B) max; ≥125%×180 A cont)
- Primary feeder:    2 AWG Cu + #6 EGC   (75°C, verify derating)
- Secondary cond.:   4/0 Cu, 240.21(C)(2) 10-ft   (sized to the 225 A OCPD, not 125% nameplate)
- Grounding (SDS):   SBJ #2 per 250.102(C)(1); GEC #2 per 250.66 to bldg steel; bond at xfmr ONLY
- Install:           ≤112.5 kVA → 12 in clearance (450.21(A))
- Assumptions:       spare, 75°C term, Cu, ambient, primary-basis=min — all listed explicitly
```
Note how the numbers differ from a naive read of the table: the secondary OCPD is **225 A (panel-bus-capped), not the 260–300 A** that 125% of nameplate FLA would allow, and the primary is **125 A on 2 AWG**, not a 250% breaker on an undersized conductor.

State every assumption in one explicit block. For any ⚠ input that was assumed rather than confirmed, say what changes if it's wrong (e.g. "if primary-only, the primary breaker drops to 125 A and the secondary conductors lose their protection path").

**Built-in riser / one-line.** The skill generates the diagram directly from the sizer's results — no redrawing, no transcription. Pipe the JSON into `draw_riser.py`:

```bash
python3 scripts/size_transformer.py --load-amps 180 --primary-v 480 --secondary-v 208 \
  --panel-bus 225 --spare 0 --sec-length 8 --tag T-1 --source-tag HP --load-tag LP-1 \
  --format json | python3 scripts/draw_riser.py --out /mnt/user-data/outputs/T-1_riser.svg
```

The SVG shows source panel → primary feeder → primary OCPD → delta-wye transformer (with the SDS ground broken out) → secondary main → secondary feeder → load panel, with the governing NEC section beside every device and conductor. Because it consumes the same JSON the schedule is built from, the diagram can never disagree with the numbers. It degrades gracefully: "by upstream branch" when the primary OCPD is below the smallest breaker, "NO SECONDARY OCPD" for primary-only, and "PARALLEL sets" when a feeder exceeds a single conductor. Present it with `present_files`. Still offer (don't build unprompted) the xlsx schedule and docx spec section.

---

## Reference files
- `references/nec-requirements.md` — Table 450.3(B) both rows + notes, 240.21(C) all scenarios, 250.30 grounding, 450.21/450.9/450.13 installation, 408.36 panelboard. Read when a flag fires or a number is challenged.
- `references/sizing-methodology.md` — FLA formulas, kVA-selection logic, temp-rise classes, DOE 2016 efficiency, impedance/inrush, K-factor, derating. Read for explanations and trade-offs.

## Scripts
- `scripts/size_transformer.py` — Deterministic sizer; the single source of truth for numbers. Always run it. `--format json` emits the machine dict.
- `scripts/draw_riser.py` — Reads the sizer's `--format json` (stdin or `--in`) and writes a one-line/riser SVG to `--out`. Computes nothing itself, so it always matches the schedule.
