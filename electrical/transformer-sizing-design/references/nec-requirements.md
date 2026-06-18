# NEC 2023 Requirements — Transformer Installation

Read the section that matches the flag the calculator raised. All citations are 2023 NEC unless noted.

## Contents
1. Table 450.3(B) — transformer OCPD (≤1000V)
2. 240.21(C) — transformer secondary conductors (tap rules)
3. 250.30 — grounding the separately derived system
4. 450 Part II — installation (clearance, room, vault, ventilation)
5. 408.36 / 450 misc — panelboard protection, disconnect, accessibility

---

## 1. Table 450.3(B) — Overcurrent protection, transformers ≤ 1000 V

Two separate jobs people conflate: **protecting the transformer** (Art. 450) and **protecting the conductors** (Art. 240). Both must be satisfied. Table 450.3(B) gives the *maximum* OCPD as a percentage of rated (FLA) current.

| Primary current | Protection method | Primary max | Secondary max |
|---|---|---|---|
| ≥ 9 A | Primary **only** | **125%** | not required |
| ≥ 9 A | Primary **and** secondary | **250%** | **125%** |
| 2–9 A | Primary only | 167% | — |
| < 2 A | Primary only | 300% | — |

(Secondary currents ≥ 9 A assumed for the secondary column; a 2-row variant in the table covers secondary < 9 A.)

**The rounding asymmetry (Note 1) — this is the trap:**
- Note 1 lets you round **UP** to the next standard OCPD (240.6(A)) **only** for the **125%** primary-only cell and the **125%** secondary cell.
- Note 1 does **NOT** apply to the **250% / 167% / 300%** cells. Those are hard ceilings — round **DOWN** to the next standard size at or below the computed max.

**Worked example — 75 kVA, 480V Δ → 208Y/120V, 3φ:**
- Primary FLA = 75000 / (480 × 1.732) = 90.2 A. Secondary FLA = 75000 / (208 × 1.732) = 208.2 A.
- *Primary-only:* 90.2 × 1.25 = 112.8 → round **up** → **125 A** primary breaker, no secondary OCPD required.
- *Primary + secondary:* the table now *permits* up to 90.2 × 2.50 = 225.5 → **225 A** primary (max) and 208.2 × 1.25 = 260.3 → **260 A** secondary (max; round-up cell would give 300 A but see the cap below). **These are ceilings, not the design values.** The default design is still **125 A** primary (coupled to the conductor — see below) and a secondary OCPD capped at the downstream panel bus. The 225 A primary is only used when inrush demands it, and then the primary conductor is upsized to suit.

**Why 250% exists:** headroom for magnetizing inrush. DOE-2016 high-efficiency and K-rated units can draw 12–25× FLA for the first cycle. A primary device at exactly 125% can nuisance-trip on energization. The 250% allowance (paired with a required secondary OCPD) gives that headroom; alternatively use a device with a high instantaneous/short-time setting (D-curve MCB, or MCCB with STD pickup set 6–10× FLA at 0.1–0.2 s). Do **not** simply disable instantaneous — that removes bolted-fault protection.

**Conductor protection vs. transformer protection — the coupling rule:** 450.3(B) protects the **transformer**; 240.4 protects the **conductor**. They are independent (450.3 Informational Note → 240.4 / 240.21 / 240.100 for conductors). On a **radial primary feeder** a single upstream device does both jobs, so the primary OCPD may not exceed what 240.4(B) allows for the primary conductor — which pins it at the 125% basis. To legally run a 250% primary breaker you must either (a) **upsize the primary conductor** so its ampacity ≥ the breaker (240.4), accepting the copper penalty for inrush margin, or (b) make the primary a **240.21(B) tap** so the tap rules protect the conductor instead of the breaker. Putting a 250% breaker on a 125%-FLA-sized conductor is a 240.4 overload-protection violation (short-circuit protection still works; overload protection does not). **Secondary conductors are generally NOT protected by the primary device** (exceptions: 1φ 2-wire, and 3φ Δ-Δ 3-wire, per 240.4(F)); they go through 240.21(C) below.

---

## 2. 240.21(C) — Transformer secondary conductors (tap rules)

Secondary conductors have OCPD ahead of them (the primary device) that exceeds their ampacity, so they're tap conductors governed by 240.21(C). Pick the scenario:

**240.21(C)(1) — protected by primary OCPD.** Only the two narrow configs above (1φ 2-wire; 3φ Δ-Δ 3-wire) where the primary device, multiplied by the voltage ratio, protects the secondary conductor.

**240.21(C)(2) — secondary not over 10 ft.** Conductor ampacity must be:
- ≥ the load served, AND
- ≥ 1/10 of the primary OCPD rating × (V_primary / V_secondary)  *(i.e. the primary OCPD referred to the secondary voltage, divided by 10)*, AND
- they must terminate in a single OCPD that limits the load to the conductor ampacity, stay inside the enclosure/raceway, and not leave the building.

**240.21(C)(6) — secondary 10 to 25 ft.** Conductor ampacity ≥ 1/3 of (primary OCPD × V_pri/V_sec); terminate in a single OCPD ≤ conductor ampacity; protected from physical damage. (This is the transformer-secondary analogue of the 25-ft feeder tap.)

**240.21(C)(4) — outside secondary conductors.** Unlimited length under specific conditions (outdoors except at termination, single OCPD at the load end, etc.).

Key constraints across all: a tap can't supply another tap; the load-end OCPD is a single device (or up to six per 450.3 for the transformer-protection count, but conductor protection wants one); the EGC/supply-side bonding jumper rules differ — secondary conductors usually carry a **supply-side bonding jumper** sized per Table 250.102(C)(1), not a Table 250.122 EGC.

---

## 3. 250.30 — Grounding a separately derived system (SDS)

**First: is it an SDS?** A transformer secondary is separately derived if it has **no direct electrical connection** (including a solidly bonded neutral) to the supply system. A Δ-Y step-down is the classic SDS. A Y-Y with a factory H0-X0 neutral bond between primary and secondary is **not** separately derived — get this right, it determines the whole scheme.

If it IS an SDS (250.30(A)):
- **System bonding jumper (SBJ):** the single neutral-to-EGC bond. Install at **one** point only — at the transformer **or** the first downstream disconnect, **never both** (double bonds create objectionable parallel neutral current, 250.6 / 250.30(A)(1)). Size per **Table 250.102(C)(1)** based on the largest ungrounded secondary conductor.
- **Grounding electrode conductor (GEC):** from that same point to the nearest effective electrode — building structural steel or metal water pipe within 5 ft of entry (250.30(A)(4)/(5), 250.68(C)). Size per **Table 250.66** on the largest ungrounded secondary conductor.
- **Supply-side bonding jumper:** bonds the secondary raceway/enclosures between the transformer and the first disconnect; sized per 250.102(C)(1).
- **Grounded (neutral) conductor:** if the bond is at the disconnect rather than the transformer, route the neutral with the secondary conductors, sized no smaller than Table 250.102(C)(1).

**Table 250.66 (GEC) — common rows by largest ungrounded conductor:**
| Largest ungrounded (Cu) | GEC (Cu) |
|---|---|
| 2 AWG or smaller | 8 AWG |
| 1 or 1/0 AWG | 6 AWG |
| 2/0 or 3/0 AWG | 4 AWG |
| over 3/0 to 350 kcmil | 2 AWG |
| over 350 to 600 kcmil | 1/0 AWG |
| over 600 to 1100 kcmil | 2/0 AWG |
| over 1100 kcmil | 3/0 AWG |

Outdoor source: 250.30(C) — ground at the outdoor source per 250.50.

---

## 4. Article 450 Part II — Installation

**Dry-type indoors, by size:**
- **≤ 112.5 kVA (450.21(A)):** min **12 in (300 mm)** from combustible material unless separated by a fire-resistant, heat-insulating barrier. Does not apply to ≤ 600V units fully enclosed except for vents.
- **> 112.5 kVA (450.21(B)):** install in a **fire-resistant transformer room, min 1-hour rating**. Exceptions: Class 155+ insulation either (1) separated ≥ 6 ft horizontal / 12 ft vertical or by a fire-rated barrier, or (2) completely enclosed except for vents.
- **> 35,000 V (450.21(C)):** vault required, complying with Part III.

**Ventilation (450.9):** openings must not be blocked; the loaded transformer must be able to pull cool air and shed heat. Marked clearances on the nameplate must be honored.

**Accessibility (450.13):** transformers must be readily accessible to qualified personnel — **except** dry-type ≤ 1000V may be (A) in the open on walls/columns/structures, or (B) in hollow spaces of buildings if ≤ 50 kVA and not permanently closed in.

**Disconnecting means (450.14):** required; in sight of the transformer, or remote with a lockable disconnect (location field-marked on the transformer).

**Working space (110.26):** the room/space must still provide code working clearance in front of the transformer, its OCPD, and the disconnect — the 12-in combustible clearance is a *separate* requirement from working space.

**Vault (Part III, if required):** floors/walls/roof min 3-hour fire resistance (e.g. 6-in reinforced concrete); 3-hour door (drops to 1-hour with sprinklers); natural-ventilation opening area ≥ 3 in² per kVA, min 1 ft²; fire dampers rated ≥ 1.5 hr on indoor vault openings.

---

## 5. Panelboard, count, misc.

- **408.36 — panelboard OCPD:** a panelboard fed from the secondary must be protected at or below its bus rating by an OCPD (the secondary main, or upstream where permitted). Confirm panel bus ≥ secondary OCPD.
- **Number of secondary OCPDs:** 450.3 permits the transformer secondary protection to be up to six breakers/fuse-sets grouped, total not exceeding the single-device rating — but conductor protection (240.21(C)) wants a single device.
- **Nameplate (450.11):** marked clearances and ratings; match the drawings to the nameplate.
