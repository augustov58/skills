# Tables & Errata — What Is Encoded and How Far to Trust It

Read this when a table value is challenged, when a lookup fails, or before editing
`scripts/spd_tables.py`. Every number in that module came from the Eaton/Bussmann SPD 2014
handbook, pages 241–245.

## Contents

1. What is encoded, and from which page
2. Transcription verification — how the numbers were proved
3. Errata — deliberate departures from the printed page
4. Lookup keys and accepted spellings
5. Where the tables run out
6. Edition drift — 2014 handbook vs 2023 NEC

---

## 1. What is encoded, and from which page

| Constant | Source | Contents |
|---|---|---|
| `TRANSFORMER_Z` | Table 1, p.241 | FLA and typical %Z for 29 kVA/voltage/phase combinations |
| `XFMR_1PH_IMPEDANCE` | p.241 | 1-phase X/R ratio, %Z range, L-N half-winding multipliers, 9 rows |
| `C_VALUES` | Table 4, p.242 | 504 conductor "C" constants: Cu/Al × single/cable × steel/non-magnetic × 600 V/5 kV/15 kV × 21 sizes |
| `BUSWAY_C` | Table 5, p.242 | 60 busway "C" constants, 225 A through 4000 A |
| `FAULT_TYPE_PERCENT` | Table 3, p.241 | Other fault types as a percent of the 3-phase bolted value |
| `VOLT_LOSS` | Tables A/B, pp.244–245 | 1,148 cells: ampacity (60/75/90 °C), DC volt loss, and 3-phase and 1-phase volt loss at five power factors |
| `SMALL_CONDUCTOR_LIMIT` | Table A/B footnote | NEC 240.4(D) OCPD caps |
| `AMBIENT_CORRECTION` | NEC Table 310.15(B)(1) | Ambient correction, 30 °C base |
| `CCC_ADJUSTMENT` | NEC Table 310.15(C)(1) | More than three current-carrying conductors |

Table 2 ("M" multiplier) is **not** encoded. It is a lookup table for `M = 1/(1+f)`, which
the scripts compute directly and exactly. Encoding it would only introduce rounding.

---

## 2. Transcription verification — how the numbers were proved

Two independent passes, because ~1,800 hand-copied numbers will contain errors:

1. **Double entry.** The tables were transcribed once from the page, then re-extracted
   independently from the PDF's embedded text layer with per-glyph x/y coordinates, bucketed
   into columns by numeric column centre, and diffed cell by cell. **1,815 cells compared.**
   The first pass contained 11 genuine errors, all corrected.
2. **Behavioural regression.** `scripts/verify_spd.py` reproduces every worked example the
   handbook prints — 40 assertions covering System A and System B three-phase (faults X₁–X₃),
   System B fault X₄ through a downstream transformer, the single-phase L-L and L-N cascades,
   both volt-loss examples, and raw table spot-checks. Worst deviation is 0.22%, which is the
   handbook's own display rounding.

**Reading these tables off a page image is not reliable.** During verification, low-resolution
page rendering agreed with several cells that both the text layer and 10× zoom crops
contradicted — the image read anchored to the value it was checking. If a cell is ever
disputed, extract the text layer or use a high-zoom crop; do not eyeball the page.

Re-run `python3 scripts/verify_spd.py` after **any** edit to `spd_tables.py`. A failure means
the table disagrees with the printed handbook. **Fix the table, not the tolerance.**

---

## 3. Errata — deliberate departures from the printed page

**The Direct Current volt-loss column.** DC volt loss cannot depend on the raceway — there
is no reactance in a DC circuit and the conductor's DC resistance is identical either way.
The printed tables nonetheless diverge between the Steel and Non-Magnetic blocks at exactly
three of 41 size rows:

| Row | Steel column | Non-Magnetic column | Stored |
|---|---|---|---|
| Cu 12 AWG | 3860 | 3464 | **3860** |
| Cu 3 AWG | 490 | 470 | **490** |
| Al 3/0 | 259 | 252 | **259** |

The other 38 rows agree exactly, so all three are print errors. DC volt loss is stored once
per size, taken from the Steel column. The Cu 12 AWG case is diagnostic: the printed
Non-Magnetic value 3464 is identical to the three-phase 100% PF figure in the same row — a
column-shift artefact.

This affects only the DC column, which the calculators do not currently use. It is recorded
so a future reader does not "fix" the module back to the printed error.

**Table 5, the 4000 A row.** It prints three em-dashes and two numbers, and the dashes sit
right of their columns' numeric centres, which initially read as an ambiguous row. Column-
centre analysis resolved it: `277800` and `256400` land on the feeder-copper and
feeder-aluminium centres to 0.01 pt — the same x-offset as the 2000/2500/3000 rows — and the
em-dash glyph carries a consistent +6.9 pt right offset throughout the table. The row is
encoded as plug-in (none, none), feeder (277800, 256400), high-impedance (none).

---

## 4. Lookup keys and accepted spellings

Table 4 prints `1/0`; Tables A and B print `0`. Both are accepted and normalise to `1/0`.
`normalize_size()` also accepts `#12`, `250 kcmil`, `4/0 AWG`, and mixed case.

| Parameter | Accepted | Means |
|---|---|---|
| material | `cu`, `copper` / `al`, `aluminum`, `aluminium` | — |
| conduit | `steel`, `magnetic`, `emt`, `rmc`, `imc` | magnetic raceway |
| | `nonmagnetic`, `pvc`, `aluminum`, `fibre` | non-magnetic raceway |
| arrangement | `single` | three single conductors in a raceway |
| | `cable`, `mc`, `tray` | three-conductor cable |
| voltage_class | `600`, `5k`, `15k` | conductor insulation class |
| busway_type | `plug_in`, `feeder`, `high_impedance` | high-impedance is copper only |

An unrecognised size **raises** rather than defaulting. That is deliberate: silently falling
back to the smallest row would produce a plausible-looking, badly wrong answer, which is the
worst failure mode a fault calculator has.

---

## 5. Where the tables run out

- **Conductors below 6 AWG have no 5 kV or 15 kV C value** (and 8 AWG has no 15 kV value).
  The table prints a dash; the module stores `None` and the lookup raises with the reason.
  56 dash cells, all verified in position.
- **Aluminium volt loss starts at 12 AWG.** Table B has no 14 AWG row.
- **Busway** is tabulated only at the 12 listed ampacities, and only as a survey average
  across manufacturers. Above 3000 A the script flags it — confirm against the submittal.
- **Power factor below 0.60** is off the end of Tables A/B. The calculator rejects it rather
  than extrapolating; the figures are not linear far outside the tabulated span.
- **Transformer %Z from Table 1 is a planning number.** UL 1561 permits ±10% on the
  nameplate itself, and Table 1 spans 1.0% to 4.0% across the kVA range. Fault current is
  *inversely* proportional to %Z, so a Table 1 lookup can be off by a factor of three
  against the real nameplate. The script raises an assumption whenever it falls back to
  Table 1, and a flag when the kVA is not even a tabulated row.

---

## 6. Edition drift — 2014 handbook vs 2023 NEC

The handbook is 2014-vintage and prints the pre-2020 Article 310 numbering. The **values**
are unchanged in the 2023 cycle for every size encoded here; only the designations moved.

| Handbook prints (2014) | 2023 NEC |
|---|---|
| Table 310.15(B)(16) | **Table 310.16** |
| 310.15(B)(2)(a) — ambient correction | **Table 310.15(B)(1)**, rule at 310.14(B) |
| 310.15(B)(3)(a) — more than 3 CCCs | **Table 310.15(C)(1)**, rule at 310.14(C)(1) |
| 310.15(B)(2)(b) — 40 °C ambient | **Table 310.15(B)(2)** |

The handbook's "Room Temperature Affects Ratings" table stops at 80 °C and omits the rows
below 30 °C. `AMBIENT_CORRECTION` in the module carries the **full** NEC Table 310.15(B)(1)
including the 10–29 °C correction factors above 1.0, because a cold ambient legitimately
increases ampacity and the handbook's abbreviated table would silently forfeit it.

The vault's copy of the NEC Handbook is the **2017** edition. Do not quote section numbers
from it as current — Article 310 was renumbered after it was printed.
