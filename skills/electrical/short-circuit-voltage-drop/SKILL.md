---
name: short-circuit-voltage-drop
description: "Calculate available short-circuit (fault) current point-to-point and steady-state voltage drop for commercial and industrial power systems, per the Bussmann/Eaton SPD method and NEC 2023 (110.9, 110.10, 110.24, 240.86, 240.4(D), 310.14, 647.4(D)). Use whenever the user wants available fault current at a panel, switchboard, MCC, or transformer secondary; needs to check a breaker or fuse interrupting rating (AIC/AIR) against the fault current; needs the field-marked fault current for service equipment; is evaluating a series rating; wants voltage drop on a feeder or branch circuit; wants the smallest wire that holds 3% (or 1.5% for sensitive electronic equipment); or needs a conductor upsized for a long run. Trigger even on partial asks like 'what's my AIC at panel LP-1', 'is 22k enough', 'how much voltage drop on 250 feet of 4/0', or when the user pastes a one-line and asks for fault currents at each bus. This skill is INTAKE-DRIVEN: it asks for the inputs that change the answer before producing numbers, so it never silently guesses transformer impedance, raceway type, conductor arrangement, fault type, or which worst case is wanted."
---

# Short-Circuit & Voltage Drop (Bussmann SPD method, NEC 2023)

Two calculations that share the same inputs and the same failure mode. A fault-current
number that is too low buys a breaker that will not clear; a number that is too high buys
gear nobody needed. A voltage-drop number computed with a resistance-only shortcut misses
reactance entirely and can be 20% optimistic on a large feeder in steel conduit.

Both are done here with the Eaton/Bussmann *Selecting Protective Devices* point-to-point
method, whose tables carry AC resistance **and** reactance per raceway type. The arithmetic
is not the hard part — the inputs are. The impedance tolerance you assume, the raceway you
assume, and which direction of worst case you need change the answer more than any rounding.

Do not improvise the arithmetic. The "f" factor compounds down a cascade, so one wrong "C"
value silently moves every downstream number, and the single-phase forms use `2 × L` where
the three-phase form uses `1.732 × L`.

---

## Step 0 — Intake. Do this before any number.

Ask only for gaps. If the user gave a one-line, a panel schedule, a utility letter, or
transformer data in chat, extract those and don't re-ask. Infer sane defaults and **state
them inline** rather than stalling — but never silently assume any of the inputs marked ⚠.

In a chat interface, use `ask_user_input_v0` for the gaps (raceway type, conductor material,
and which worst case make good tappable choices). Group into one round; don't interrogate
one item at a time.

**A. Which calculation, and what decision hangs on it?**
1. Fault current, voltage drop, or both? They share conductor inputs, so if the user gives
   a feeder they usually want both — offer it.
2. What is the number *for*? This picks the worst case in item 7 and it is not optional:
   an interrupting-rating check and a ground-fault-pickup check need opposite assumptions
   from the same system.

**B. The source ⚠**
3. Either a **transformer** (kVA, secondary voltage, phase, and **%Z from the nameplate**),
   or a **known available fault current** from the utility letter or an upstream study.
   ⚠ If the user gives kVA but no %Z, say you are falling back to SPD Table 1 and that fault
   current is *inversely* proportional to %Z — Table 1 spans 1.0% to 4.0%, so the fallback
   can be off by a factor of three. Get the nameplate if the number will be issued.
4. Utility available fault at the primary, if known. With it you can start upstream and work
   down through the transformer (SPD Steps A–C) instead of assuming an infinite bus.
   Assuming infinite bus is conservative — it overstates the fault.
5. Phase: 1φ or 3φ. ⚠ Drives `1.732 × L` vs `2 × L` in the f-factor, a 15% swing.

**C. The conductor run ⚠**
6. Length in feet, size, material (Cu/Al), **conductors per phase**, and two things people
   forget: ⚠ **raceway** — steel is magnetic and raises both AC resistance and reactance
   (500 kcmil Cu at 600 V is C=22,185 in steel and C=26,706 in PVC, a 20% swing) — and
   ⚠ **arrangement**, three single conductors in a raceway vs a three-conductor cable.
   Busway is entered by ampacity and type (plug-in / feeder / high-impedance) instead.

**D. Which worst case ⚠**
7. **Maximum fault** (`--z-tolerance high`, %Z × 0.9) for interrupting ratings (110.9),
   withstand ratings (110.10), and arc-flash. This is the default and what every printed SPD
   example uses. **Minimum fault** (`--z-tolerance low`, %Z × 1.1, often with `--utility low`)
   for ground-fault pickup, series ratings, and "will the device actually trip". If a series
   rating or a GF study is in play, **run both** — reporting only the maximum is the most
   common first-pass failure.
8. Fault type: three-phase bolted (default), 1φ line-to-line, or 1φ line-to-neutral.
   ⚠ The L-N procedure is for a **center-tapped single-phase** transformer only. There is no
   SPD L-N method for a 3φ wye system; the script refuses that combination and points at
   Table 3 instead.

**E. Motors**
9. Total connected motor FLA downstream, or the motor fraction of the load. Motor
   contribution is `4 × motor FLA` (SPD Step 6A) added at **every** fault point undiminished,
   because the motors sit downstream of the conductor run. Skipping it under-reports the
   fault at exactly the panels where breakers get specified.

**F. Voltage drop only**
10. Load current (the **actual** running current, not 125% of it — 125% sizes the OCPD and
    ampacity, it does not increase the current that causes the drop), circuit voltage, and
    power factor (default 0.9 mixed commercial; motor-heavy runs 0.8 or below — say which).
11. The limit: 3% is the 210.19/215.2 Informational Note value and is **advisory, not
    enforceable**. 1.5% branch / 2.5% total is **mandatory** for sensitive electronic
    equipment (647.4(D)). Fire pumps have their own mandatory rules (695.7).
12. Ambient and current-carrying-conductor count if they differ from 30 °C and 3, plus the
    termination temperature (110.14(C): 60 °C column for equipment rated 100 A or less
    unless listed otherwise).

**Do not produce numbers until items 3, 5, 6 and 7 are known, and item 8 is known or
explicitly defaulted with the default stated. If the user cannot supply nameplate %Z, run
it anyway with the Table 1 fallback and put the caveat in the deliverable, not just in
your own reasoning.**

---

## Step 1 — Run the calculators. Don't hand-calculate.

Both scripts are stdlib Python 3, no dependencies, and print every intermediate value plus
an **ASSUMPTIONS** block and a **FLAGS / VERIFY** block.

```bash
# fault current: one conductor run from a transformer secondary
python3 scripts/short_circuit.py \
  --kva 1500 --percent-z 3.5 --secondary-v 480 \
  --length-ft 25 --size 500 --conductor cu --per-phase 6 --conduit steel \
  --motor-fla 1804 --device-air 65000

# fault current: a multi-point cascade (X1, X2, X3 ...) down a one-line
python3 scripts/short_circuit.py --system system.json
python3 scripts/short_circuit.py --example     # writes example_system.json and runs it

# voltage drop on a known conductor
python3 scripts/voltage_drop.py \
  --amps 40 --length-ft 180 --voltage 240 --phase 3 --size 6 --pf 0.8

# smallest conductor that holds the limit AND carries the load
python3 scripts/voltage_drop.py \
  --amps 200 --length-ft 300 --voltage 208 --conductor al --select \
  --limit-percent 3 --ambient-c 45 --ccc 6
```

Start from a known utility fault instead of a transformer with `--available-fault 45000`.
Run the minimum-fault case with `--z-tolerance low --utility low`. Check a device against
110.9 by passing `--device-air`. Charge upstream drop against a combined budget with
`--upstream-percent 1.8 --total-limit-percent 5`. Full flags: `--help` on either script.

**Use the JSON `--system` path whenever there is more than one fault point** — a service,
a distribution board, and an MCC is three points, and doing them as three separate runs
means re-typing the upstream current by hand and losing the audit trail. The schema is the
`EXAMPLE` block in `short_circuit.py`; `--example` writes a working copy. Both scripts write
only where you point them, but `--example` writes into the current directory — run from a
writable directory, never with the working directory set to this skill's folder.

**Read the assumptions and flags back to the user.** If any assumption is wrong, rerun.
Never paste a bare number — show the rule next to it.

---

## Step 2 — Resolve what the calculator flags (judgment + lookup)

The scripts give numbers; these need confirmation against `references/nec-requirements.md`
when the relevant flag fires:

- **110.9 interrupting rating** — the flag fires when `--device-air` is below the available
  fault. Confirm the rating is the device's *interrupting* rating at the actual system
  voltage, not its frame or continuous rating, and that the comparison used the **maximum**
  fault including motor contribution.
- **Series rating (240.86)** — only tested combinations, or a PE-selected combination in an
  *existing* installation. Then check 240.86(C): motor FLC between the two devices may not
  exceed **1%** of the load-side device's interrupting rating. That is ~100 A on a 10 kAIC
  breaker; one 75 hp motor nearly uses it up.
- **110.24 field marking** — the result has a shelf life. Record the %Z, the utility figure,
  the tolerance assumption, and the date; a transformer swap invalidates the marking.
- **Arc flash (110.16)** — this calculation gives the bolted fault current only. The Table 3
  arcing percentages the script prints are a sanity check, not an incident-energy study. Do
  not produce a label from this output.
- **Table 1 %Z fallback** — the flag fires whenever no nameplate %Z was given. Get the
  nameplate before anything is issued.
- **Voltage drop limit** — check whether the user's limit is advisory (3%/5% Informational
  Note) or mandatory (647.4(D) 1.5%/2.5%, 695.7 fire pump). Say which applies.
- **Ampacity vs drop** — a conductor upsized for voltage drop still has to satisfy 310.14,
  and its EGC grows in proportion per 250.122(B). Voltage drop never reduces required
  ampacity; flag the EGC as a downstream task.

Read `references/point-to-point-method.md` for the *why* when the user pushes back: the
1.732-vs-2 derivation, why %Z gives the fault current, the half-winding problem on
center-tapped transformers, and what the method does not model.

---

## Step 3 — Deliver

Default deliverable: a fault-current schedule the user can drop onto a one-line or into a
short-circuit study, **with the governing rule cited next to each number** so a reviewer can
check it.

```
## Available Fault Current — Service to MCC-1     (max case, %Z x 0.9)
- Source:            1500 kVA, 480V 3ph, 3.5%Z nameplate, infinite primary assumed
- X1  Xfmr secondary:  57,278 A  + 7,217 A motor  =  64,495 A   (SPD Steps 1-3 + 6A)
- X2  MDP bus:         55,138 A  + 7,217 A motor  =  62,355 A   (25 ft, 6x500 kcmil Cu, steel, C=22185; f=0.0388, M=0.9626)
- X3  MCC-1:           38,068 A  + 7,217 A motor  =  45,285 A   (50 ft, 1x500 kcmil Cu, steel; f=0.4484, M=0.6904)
- Device check:      MDP main 65 kAIC >= 62,355 A -> 110.9 OK
- Field marking:     64,495 A at service, calculated 2026-08-16 (110.24(A))
- Not included:      arcing fault current, X/R asymmetry, termination impedance
- Assumptions:       %Z x0.9 max case; motor = 100% of xfmr FLA x 4; infinite primary
```

Note how the numbers differ from a naive read: the motor contribution is **added
undiminished at every point**, not attenuated by the conductor run, and the value that
governs the service main is **64,495 A at X1**, not the lower number further downstream.

For voltage drop, give the drop, the percent, the limit that applies, whether it is advisory
or mandatory, and the ampacity check alongside — a conductor that passes drop and fails
ampacity is not a solution.

State every assumption in one explicit block. For any ⚠ input that was assumed rather than
confirmed, say what changes if it's wrong (e.g. "if the raceway is PVC rather than steel,
X3 rises to about 41,000 A"). If a series rating or ground-fault question is in scope, show
**both** the maximum and minimum cases side by side.

---

## Hard rules (don't violate)

- **Maximum and minimum fault are different questions.** Interrupting rating needs the
  maximum (%Z × 0.9); ground-fault pickup and series ratings need the minimum (%Z × 1.1).
  Running one and reporting it as "the" fault current is wrong for half of all uses.
- **Motor contribution is added at every fault point undiminished.** Attenuating it by M is
  the classic error — the motors are downstream of the run, so their current never passes
  through it.
- **Motor contribution does not cross a transformer.** Different voltage. Count secondary
  motors separately.
- **Never quote a line-to-neutral volt loss against a line-to-line nominal voltage.** It
  halves the reported drop. The percent is the same either way on a balanced circuit.
- **Voltage drop is an additional constraint on top of ampacity, never a substitute.** Check
  both; the script does.
- **This is not an arc-flash calculation.** Bolted fault current is one of four fields a
  110.16 label needs. Incident energy requires IEEE 1584 and device clearing times.
- **This is not a stamped study.** Generators, paralleled sources, network transformers, and
  motor-plant decay need per-unit or symmetrical components (IEEE 141 / 242). Say so rather
  than stretching the method.
- Re-run `python3 scripts/verify_spd.py` after any edit to `scripts/spd_tables.py`. A failure
  means the table disagrees with the printed handbook — **fix the table, not the tolerance.**

## Editions

Method and tables: Eaton/Bussmann SPD, **2014** edition. Code citations: **NEC 2023**. The
handbook prints the pre-2020 Article 310 numbering (310.15(B)(16), 310.15(B)(2)(a)); the
values are unchanged but the designations moved — see `references/tables-and-errata.md` §6.
The NEC Handbook PDF in this vault is the **2017** edition; do not quote section numbers
from it as current. If the AHJ adopts a different cycle, confirm the changed sections.

## Reference files

- `references/point-to-point-method.md` — the six-step procedure, all three f-factor forms, Notes 1–5, the known-primary-fault variant (Steps A–C), the single-phase half-winding problem, motor contribution, the volt-loss method, and what the method does not model. Read for the *why* and when a number is challenged.
- `references/nec-requirements.md` — 110.9 vs 110.10, 110.24 field marking, 240.86 series ratings and the 1% motor rule, 110.16 arc flash, advisory vs mandatory voltage drop, the 310.14/110.14(C) two-step, 240.4(D). Read when a flag fires.
- `references/tables-and-errata.md` — what is encoded and from which page, how the transcription was verified, the three deliberate errata, lookup keys, where the tables run out, and 2014-vs-2023 edition drift. Read before editing the data module or when a table value is disputed.

## Scripts

- `scripts/spd_tables.py` — Data only, no logic. Both calculators import it, so they can never disagree about a "C" value or an ampacity. Not run directly.
- `scripts/short_circuit.py` — Point-to-point fault current; the single source of truth for those numbers. Always run it. Flags for one hop, `--system` JSON for a cascade, `--format json` emits the machine dict.
- `scripts/voltage_drop.py` — Volt-loss calculation and minimum-wire-size selection, with the ampacity check built in. Always run it. `--format json` emits the machine dict.
- `scripts/verify_spd.py` — Regression harness: reproduces all 40 values the handbook prints. Run after any table edit, and to demonstrate the numbers are trustworthy.
