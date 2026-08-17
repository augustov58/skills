# NEC 2023 Requirements — Available Fault Current & Voltage Drop

Read the section that matches the flag the calculator raised. All citations are 2023 NEC
unless noted. If the AHJ adopts a different cycle, confirm the numbers — Article 310 was
renumbered in 2020 and the SPD handbook (2014) still prints the old 310.15(B)(2)(a) /
310.15(B)(3)(a) designations.

## Contents

1. 110.9 / 110.10 — interrupting rating vs short-circuit current rating
2. 110.24 — field marking the available fault current
3. 240.86 — series ratings, and the motor-contribution killer
4. 110.16 — arc-flash labels (what this calculation does and does not give you)
5. Voltage drop — what is advisory and what is mandatory
6. 310.14 / 310.15 / 110.14(C) — ampacity, derating, and terminations
7. 240.4(D) — the small-conductor rule

---

## 1. 110.9 / 110.10 — interrupting rating vs short-circuit current rating

These two are constantly conflated. They are different ratings on different equipment.

| | 110.9 — Interrupting Rating | 110.10 — Short-Circuit Current Rating (SCCR) |
|---|---|---|
| Applies to | Devices intended to **interrupt** fault current: breakers, fuses | Everything else in the circuit: busway, panelboard bus, starters, contactors, control panels |
| Requirement | Rating ≥ available fault current at nominal circuit voltage | Components selected and coordinated so the protective device clears the fault **without extensive damage** |
| Failure mode | The breaker fails to clear and the fault is not interrupted | The gear is destroyed even though the breaker did clear |

**110.9 is the check the script performs** with `--device-air`. The available fault current
compared against it must include motor contribution and must be the **maximum** case
(`--z-tolerance high`).

110.10 is not a single number check — it also requires the let-through energy of the
upstream device to be below the component's withstand. Listed equipment applied within its
marked SCCR satisfies it. An assembled control panel needs its SCCR determined per
UL 508A Supplement SB.

---

## 2. 110.24 — field marking the available fault current

**(A) Field Marking.** Service equipment in other than dwelling units shall be legibly
field-marked with the **maximum available fault current**, including **the date the
calculation was performed**, and the marking must have sufficient durability to withstand
the environment.

**(B) Modifications.** When the electrical installation is modified in a way that affects
the available fault current, the calculation must be **redone** and the marking updated.

*Exception:* not required in industrial installations where conditions of maintenance and
supervision ensure only qualified persons service the equipment.

Practical consequence: the output of this skill is a document with a shelf life. Record the
transformer %Z, the utility figure, and the tolerance assumption used — a utility
transformer swap or a service upgrade invalidates the marking. This is why every run prints
which %Z and which tolerance factor it used.

---

## 3. 240.86 — series ratings, and the motor-contribution killer

A series rating lets a **downstream device with an interrupting rating below the available
fault current** be used, because the upstream device limits the let-through. Three
conditions, and the third is the one that fails in the field:

- **(A) Engineering supervision, existing installations only** — a licensed PE selects the
  combination and documents it; the field marking must indicate the series rating.
- **(B) Tested combinations** — the specific manufacturer/catalog-number pairs marked on the
  equipment. You may not invent a combination.
- **(C) Motor contribution** — a series rating **shall not be used** where the sum of motor
  full-load currents connected **between** the line-side (higher-rated) device and the
  load-side (lower-rated) device exceeds **1%** of the load-side device's interrupting
  rating.

That 1% is tiny. A 10 kAIC downstream breaker permits only 100 A of intervening motor FLC.
One 75 hp motor at 480 V (96 A) very nearly consumes the entire allowance. **Run the
minimum-fault case (`--z-tolerance low`) as well when a series rating is in play** — a
series combination that relies on the upstream device operating needs the fault current to
actually reach the level the test assumed.

---

## 4. 110.16 — arc-flash labels

**(A) General.** Electrical equipment in other than dwelling units, likely to require
examination while energized, shall be field-marked to warn of potential arc-flash hazards.

**(B) Service Equipment.** For services rated **1200 A or more**, the label must include the
nominal system voltage, the available fault current at the service overcurrent device, the
**clearing time** of that device, and the **date** — or, alternatively, the incident energy
or PPE category per NFPA 70E.

**This skill produces exactly one of those four fields.** The clearing time comes from the
device's published time-current curve at the calculated fault current, and incident energy
comes from an IEEE 1584 calculation using the **arcing** current, not the bolted current.
SPD Table 3 (which the script prints) gives arcing fault current as a percentage of the
bolted value — that is an order-of-magnitude sanity check, not an incident-energy study.
Do not let an arc-flash label be produced from this output alone.

---

## 5. Voltage drop — what is advisory and what is mandatory

**Advisory (Informational Notes — not enforceable requirements):**

- **210.19(A), Informational Note** — branch circuits sized to prevent a voltage drop
  exceeding **3%** at the farthest outlet, where the maximum total drop on both feeders and
  branch circuits does not exceed **5%**, provides reasonable efficiency of operation.
- **215.2(A), Informational Note** — the same 3% feeder / 5% combined guidance.

Informational Notes are explanatory material per 90.5(C) and **are not enforceable as
Code requirements**. An AHJ cannot cite them as a violation. An owner specification, a
utility requirement, or an energy code very often *does* make them binding, and most
engineers design to them regardless because equipment performance degrades below them.
Note the exact Informational Note numbering shifts between cycles; the section is stable.

**Mandatory (enforceable):**

- **647.4(D) — sensitive electronic equipment** on separately derived 120/240 V technical
  power systems: **branch circuit ≤ 1.5%**, combined branch + feeder **≤ 2.5%**. This is a
  hard requirement, not a note. Pass `--limit-percent 1.5`.
- **695.7 — fire pumps:** voltage at the controller line terminals shall not drop more than
  **15%** below normal during motor starting, and voltage at the motor terminals shall not
  drop more than **5%** below the motor's rated voltage while running at 115% of full-load
  current. The starting case is a transient calculation, not this steady-state method —
  see the `generator-sizing` skill for motor-starting dip.

**Voltage drop never reduces required ampacity.** A conductor upsized for drop still must
satisfy 310.14, and its EGC grows in proportion per 250.122(B). Voltage drop is an
*additional* constraint layered on top of ampacity, never a substitute.

---

## 6. 310.14 / 310.15 / 110.14(C) — ampacity, derating, and terminations

The order of operations is where most first-pass sizing goes wrong. It is a **two-step**,
and the steps are independent:

```
Step 1  Start from the ampacity of the conductor's OWN INSULATION rating
        (90C for THHN/THWN-2/XHHW-2), Table 310.16.
        Apply ambient correction   -> Table 310.15(B)(1)   [rule: 310.14(B)]
        Apply CCC adjustment       -> Table 310.15(C)(1)   [rule: 310.14(C)(1)]

Step 2  Independently, cap the result at the ampacity from the TERMINATION
        temperature column                                 [rule: 110.14(C)]

Final ampacity = min(Step 1 result, Step 2 cap)
```

Deriving from the 75 °C column throws away the 90 °C headroom the Code explicitly allows
for derating, and under-sizes the conductor. Deriving from 90 °C and forgetting the
termination cap over-sizes the circuit's allowable load. The script does both steps and
prints which one governed.

**110.14(C)(1) termination temperatures:**

- Equipment rated **100 A or less**, or marked for 14 AWG through 1 AWG conductors → the
  **60 °C** column, unless the equipment *and* the connectors are listed for higher.
- Equipment rated **over 100 A**, or marked for conductors larger than 1 AWG → the
  **75 °C** column.
- 90 °C conductors may be **used**, but only at their 60/75 °C ampacity for termination.
  The 90 °C column exists for derating, not for loading.

**310.15(C)(1) adjustment** applies to more than three current-carrying conductors bundled
longer than 24 in. A neutral carrying only unbalance is not a CCC; a neutral on a
harmonic-heavy 3-wire wye circuit is (310.15(E)).

---

## 7. 240.4(D) — the small-conductor rule

Regardless of what the ampacity table permits after derating, overcurrent protection is
capped:

| Conductor | Max OCPD |
|---|---|
| 14 AWG Cu | 15 A |
| 12 AWG Cu | 20 A |
| 10 AWG Cu | 30 A |
| 12 AWG Al / Cu-clad Al | 15 A |
| 10 AWG Al / Cu-clad Al | 25 A |

These are exactly the rows the SPD volt-loss tables mark with an asterisk. The script flags
the cap whenever one of these sizes is selected, and flags a violation when `--ocpd` exceeds
it. The rule has exceptions in 240.4(E) (tap conductors) and 240.4(G) (specific
applications such as motor circuits, which are governed by Article 430 instead).
