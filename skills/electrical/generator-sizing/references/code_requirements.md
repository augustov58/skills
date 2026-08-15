# Code & Standards Reference — Emergency / Standby Generators

Deterministic regulatory data. Cite this file; do not re-search unless verifying a code-cycle change.
Editions assumed: NEC 2023 (NFPA 70), NFPA 110-2025, NFPA 101-2024, NFPA 99-2024, NFPA 20-2022.
Flag to user if their AHJ adopts a different cycle.

## Table of Contents
1. The three NEC categories (700 / 701 / 702) — selection
2. NEC capacity & sizing rules per category
3. NFPA 110 Level / Type / Class classification
4. Fuel storage rules
5. Fire pump rules (NEC 695 / NFPA 20)
6. Generator ratings (ISO 8528 / OEM) — standby vs prime vs continuous
7. Other hard constraints (ground fault, separation, ATS, alternator derates)

---

## 1. NEC Category Selection — 700 vs 701 vs 702

The category is **driven by what the loads are and who mandates them**, not by owner preference.
A single facility can have all three, usually on separate ATSs.

| Category | Article | What it covers | Transfer time | Wiring separation | Who mandates |
|----------|---------|----------------|---------------|-------------------|--------------|
| Emergency | 700 | Life-safety: egress lighting, exit signs, fire alarm, smoke control, elevators for egress | ≤ 10 s | Fully separate raceways/boxes/panels (700.10(B)) | Building/fire code via legal requirement |
| Legally Required Standby | 701 | Aids responders / mandated but not life-critical: smoke removal, sewage, comm, some HVAC | ≤ 60 s | May share raceways with each other, not with 700 | Governmental agency |
| Optional Standby | 702 | Owner-chosen: data centers, refrigeration, process, comfort | No limit | Normal wiring methods | Owner |

Decision logic:
- Is the load required by code for life safety / egress? → **700**.
- Is the load required by a governmental agency / building code but not life safety? → **701**.
- Is it owner-elected for property/business continuity? → **702**.

A single generator can serve all three if it has adequate capacity AND a priority/load-shed scheme
(700.5(D)): emergency loads have absolute priority, then 701, then 702.

---

## 2. NEC Capacity & Sizing Rules

### 700.4 / 701.4 — Emergency & Legally Required Capacity
- Must have adequate capacity to carry **all loads expected to operate simultaneously** (700.4(A)).
- Load shedding (700.4(B) / 700.5) permits a smaller source IF a listed automatic shed scheme keeps
  emergency loads served first. Without load shed, size for the full simultaneous load.

### 702.4 — Optional Standby Capacity (2023 NEC)
- **702.4(A)(1) Manual transfer:** source must handle the equipment the user will run at one time.
- **702.4(A)(2)(a) Automatic transfer, full load:** source must supply the **entire connected load**
  it can automatically pick up.
- **702.4(A)(2)(b) Automatic transfer + EMS/PCS:** source sized for the **maximum load the EMS will
  permit** (Power Control System per 750/705 must limit it).

### 220.87 — Existing facilities "approved method"
Permitted to size on **actual demand** instead of full Article 220 connected load when:
1. Max-demand data available for 1 year (or recorded 15-min peak over min. 30 days), AND
2. Max demand × 125% + new load ≤ source rating, AND
3. Overcurrent protection compliant.
This is the lever to **shrink** an optional-standby genset when metered data exists.

### 445.13 — Generator conductor ampacity
Conductors from generator terminals to the first OCPD must be **≥ 115% of nameplate current**.
(Drives the feeder size, which feeds back into voltage-drop checks.)

### Generator nameplate current
`I = kW × 1000 / (√3 × V_LL × PF)` for 3-phase. PF default 0.8 for genset rating.

---

## 3. NFPA 110 Classification — Level / Type / Class

NFPA 110 governs **how** the EPSS is built/tested, not whether you need one (that comes from
NFPA 101 / 99 / building code). Three independent dimensions:

### Level — criticality
| Level | Definition |
|-------|------------|
| 1 | Failure could cause loss of human life or serious injury. Strictest. |
| 2 | Less critical to life/safety. |

### Type — max transfer time (seconds) to pick up Level 1/2 loads
| Type | Max time |
|------|----------|
| Type U | Uninterruptible (no break) |
| Type 10 | 10 s (standard for Level 1 emergency) |
| Type 60 | 60 s |
| Type 120 | 120 s |
| Type M | Manual, no fixed time |

### Class — minimum runtime at full load WITHOUT refueling (hours)
| Class | Hours |
|-------|-------|
| Class 0.083 | 5 min |
| Class 0.25 | 15 min |
| Class 2 | 2 h |
| Class 6 | 6 h |
| Class 48 | 48 h |
| Class X | "Other" — set by application/AHJ; commonly 72 or 96 h |

**Common mandated combos:**
- High-rise (NFPA 101 11.8.5.3): **Type 60, Class 1, Level 1** (verify edition; some cite Type 60 Class 2).
- Healthcare (NFPA 99 / 110): **Type 10, Class X, Level 1.**
- Data center (owner-elected best practice): Level 1, Type 10, Class 48+.

---

## 4. Fuel Storage Rules

- **NEC 700.12(B)(2):** on-site fuel for **min. 2 hours** full-demand operation (emergency, prime-mover).
- **NFPA 110:** on-site fuel for the **Class** runtime (e.g., Class 48 = 48 h).
- **NFPA 110 "133% rule":** main tank must hold **133%** of the Class fuel requirement at full rated load.
- **Seismic / disaster AHJ interpretation (A.4.2):** Level 1 in high seismic → often 96 h.
- Allowed fuels (5.1.1): diesel (preferred Level 1, fast start, on-site storage), natural gas, LP/LPG.
  Large natural-gas units may not meet Type 10 single-step block load — flag for Level 1 Type 10.

### Diesel fuel burn rate (approx, gal/hr at load) — for tank sizing
| Genset kW | 25% load | 50% load | 75% load | 100% load |
|-----------|----------|----------|----------|-----------|
| 100  | 2.6  | 4.1  | 5.8  | 7.4  |
| 150  | 3.6  | 6.1  | 8.5  | 11.0 |
| 200  | 4.7  | 8.0  | 11.3 | 14.4 |
| 300  | 6.8  | 11.6 | 16.8 | 21.5 |
| 400  | 8.9  | 15.4 | 22.3 | 28.6 |
| 500  | 11.0 | 19.0 | 28.0 | 36.0 |
| 750  | 16.0 | 28.0 | 41.0 | 53.0 |
| 1000 | 21.0 | 37.0 | 54.0 | 71.0 |
| 1500 | 31.0 | 55.0 | 80.0 | 105.0 |
| 2000 | 41.0 | 73.0 | 107.0| 140.0 |
Rule of thumb: diesel ≈ **0.07 gal/hr per kW at 100% load** (≈0.05 at 75%). Use for interpolation.

---

## 5. Fire Pump (NEC 695 / NFPA 20)

If the building has a fire pump on the generator, it usually **drives the sizing**.

- **NEC 695.3 / NFPA 20:** alternate source must carry the **locked-rotor current** of the fire pump
  motor(s) plus FLC of associated equipment (jockey pump, etc.).
- **NEC 695.7 / NFPA 20 9.4 (a.k.a. 9.2.2):** voltage at controller line terminals must not drop more
  than **15%** during motor starting (locked rotor). Motor terminals ≤ 5% drop at 115% FLC running.
  *Exception:* the 15% limit does not apply when the pump is started by manual mechanical means
  (mechanically-held breaker).
- **NFPA 20:** if the generator is the alternate source, it needs fuel for **8 hours** of continuous
  fire-pump operation (in addition to/coordinated with other Class requirements).
- Practical effect: the 15% dip limit on a genset is **tighter than the typical 20–35% dip used for
  ordinary motors**, so the fire pump can force a much larger alternator. Size the alternator so
  locked-rotor sKVA causes ≤15% dip including feeder voltage drop.
- **Starting-method caveat:** fire pump starting must use a **listed fire pump controller** type per
  NFPA 20 (across-the-line, wye-delta, part-winding, autotransformer, soft-start, or listed
  variable-speed). When the sizing script's mitigation output suggests reduced-voltage starting for
  a FIRE PUMP motor, the option is only valid as a listed FP controller of that type — never a
  generic soft starter or VFD. Also note many reduced-voltage FP controllers bypass to full voltage
  on failure, so some AHJs require sizing for the across-the-line case anyway. Confirm with the AHJ.

---

## 6. Generator Power Ratings (ISO 8528-1 / OEM)

Pick the right **rating definition** before comparing OEM model kW.

| Rating | Definition | Typical use | Load profile |
|--------|------------|-------------|--------------|
| Emergency Standby (ESP) | Varying load, **no overload**, avg ≤ 70% of rating, ≤ 200 h/yr | Utility-outage backup | Backup only |
| Limited-Time Prime (LTP) | Constant load up to 500 h/yr | Scheduled utility-limited | Constant, limited |
| Prime (PRP) | Unlimited hours, varying load, avg ≤ 70%, 10% overload 1h/12h | Genset is main source | Variable, unlimited |
| Continuous (COP / Base) | Unlimited hours, constant non-varying load | Base-load / cogen | Constant, unlimited |
| Mission Critical Standby (MCS) | Data-center standby, avg ≤ 85%, ≤ 500 h/yr | Data centers | Backup, higher util |

**The same physical engine has different kW labels under each rating.** For code backup systems,
use the **Standby (ESP)** rating. If the genset runs the building as prime power, use **Prime (PRP)**
— Prime rating is typically ~10% lower kW than Standby for the same machine.

---

## 7. Other Hard Constraints

- **Ground fault:** 700.6/701.6 allow ground-fault **indication (alarm only)** — emergency/required
  systems may keep running through a ground fault. **702 has no such exception → must TRIP** on GF
  for services/feeders ≥1000A, 480/277V (per 230.95). Big design difference for optional systems.
- **Selective coordination:** required for 700.32 and 701.32 (emergency & legally required). Optional
  (702) does not require it. This affects OCPD selection, not generator kW, but flag it.
- **ATS rating:** must be **listed for emergency use** (700/701). Open-transition (10–100 ms break)
  vs closed-transition (make-before-break, parallels momentarily) — closed needed for UPS-backed or
  no-break loads, and is required for paralleling/peak-shaving.
- **Alternator harmonic derate:** nonlinear loads (VFDs, UPS rectifiers, SCR soft starters) inject
  harmonics. Keep voltage THD ≤ **10%** (IEEE 519). When UPS/VFD load > ~30% of capacity, **oversize
  the alternator** (often select the next frame, or specify a PMG + lower-reactance winding) — the
  engine kW may be fine but the alternator runs hot from harmonic current.
- **Altitude/temperature derate:** engines lose power above ~500 ft and above ~25–40°C. Typical diesel
  derate ≈ **3% per 1000 ft above 500 ft**, plus temperature derate. Apply to the OEM rating before
  comparing to required kW. (OEM curves are authoritative — ask user for site elevation & ambient.)
- **Step-load / block load (NFPA 110 5.6.3.1.2):** Level 1 prime movers generally must accept the
  full Level 1 load in a **single step**. This is an engine transient-capability constraint, separate
  from the alternator sKVA constraint. Diesel handles single-step block load better than gas.
