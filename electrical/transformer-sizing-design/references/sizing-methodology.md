# Transformer Sizing Methodology — the engineering *why*

Read this when you need to explain a number, defend a trade-off, or the user pushes back.

## 1. FLA formulas
- **3-phase:** FLA = kVA × 1000 / (V_LL × √3)
- **1-phase:** FLA = kVA × 1000 / V

Use line-to-line voltage for the √3 form. Quick check: 75 kVA at 480V 3φ → 75000/(480×1.732) = **90.2 A**. At 208V 3φ → **208.2 A**. The secondary FLA is always higher on a step-down because the voltage dropped.

## 2. kVA selection logic
1. Start from **demand** load (post-Article 220), not connected — connected oversizes and you pay no-load losses for the transformer's whole life.
2. If load is in kW: kVA = kW / PF. Default PF 0.9 mixed commercial, 0.8 motor-heavy. If the load is already kVA, don't divide again.
3. Apply spare: target = demand × (1 + spare). Default spare 25% → demand ≈ 80% of nameplate. Engineering practice, not NEC.
4. Round **up** to the next standard NEMA size: 15, 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000, 1500, 2000, 2500 (3φ).

Common building config: 480V Δ primary → 208Y/120V secondary. 208V for larger equipment, 120V for receptacles/lighting. Most commercial step-downs land at 75–300 kVA. General guidance caps dry-type comfortably around 300 kVA for low-voltage; larger goes to multiple units or liquid-filled.

## 3. Temperature-rise class (80 / 115 / 150 °C)
Dry-type units use the same 220°C insulation regardless of rise rating; the rise number is how hot the windings run at full load in a 40°C ambient.
- **150°C rise** — standard, cheapest, runs hottest. Default for distributor-counter / industrial.
- **115°C rise** — typical MEP consulting spec. ~13–21% less operating energy than 150°C in some comparisons; more thermal headroom for occasional overload, less waste heat to air-condition away.
- **80°C rise** — most headroom and lowest losses, highest cost.

DOE-2016 minimum efficiency is the **same regardless of rise class** (it's tested at 35% load), so "lower rise = more efficient" is not automatically true — compare actual loss data at the intended loading. Lower rise gives overload headroom and less heat into the space, which matters in a tight electrical room. A 115°C unit is often a derated 150°C design and thus mechanically robust.

## 4. DOE 2016 efficiency (10 CFR 431.196)
Low-voltage dry-type distribution transformers made on/after Jan 1 2016 must hit minimum efficiencies tested at **35% load**. Sample three-phase minimums: 15 kVA 97.89%, 75 kVA 98.60%, 112.5 kVA 98.74%, 150 kVA 98.83%, 300 kVA 99.02%, 500 kVA 99.14%, 1000 kVA 99.28%. Excluded types (no DOE requirement): autotransformers, drive/rectifier/UPS/welding/grounding/testing transformers, sealed/nonventilating, and units with ≥20% tap range. Don't size for efficiency alone — size for the loss at the *intended* loading profile.

## 5. Inrush & breaker coordination
Magnetizing inrush is a 1-cycle surge, decaying over a few cycles, roughly **8–12× FLA** for legacy units and **up to 12–25×** for DOE-2016/K-rated designs (more core/coil steel saturates harder). It depends on the point on the voltage wave at energization, so it varies shot-to-shot.

The risk: the primary OCPD's **instantaneous** (magnetic) trip band sits at a multiple of its rating. A thermal-mag breaker trips instantaneous at ~10× rating ±20%. If inrush lands in that band, you get a nuisance trip on energization.
- Field practice: specify assuming **12× FLA** for design margin.
- Trip-curve choice: B-curve 3–5× In, C-curve 5–10×, **D-curve 10–20×** — D-curve is the transformer-friendly MCB. MCCBs: set short-time-delay (STD) pickup 6–10× FLA at 0.1–0.2 s, long-time pickup 1.0–1.15× FLA. Set instantaneous high or rely on STD — don't disable instantaneous outright (loses bolted-fault protection).
- This is *why* the 250% primary allowance (with secondary OCPD) exists — it buys instantaneous headroom over inrush.

## 6. K-factor — surviving harmonic heat
A K-rated transformer does **not** filter harmonics; it's built (heavier conductors, better core, often 200% neutral bus) to **survive the extra eddy-current heating** that nonlinear load currents cause. UL-recognized ratings: K-1, K-4, K-9, K-13, K-20, K-30, K-40, K-50 (UL 1561 / IEEE C57.110).

Selection by nonlinear fraction of load (round up):
- < 15% electronic → standard K-1, no special action.
- ≤ 35% → **K-4** (offices with PCs, light VFD/LED).
- ≤ 75% → **K-13** (schools, hospitals, mixed commercial — the safe default when unsure).
- ~100% electronic / data-center PDU → **K-20**.

For any K-rated install, also: spec a **200% neutral bus** and **upsize the neutral conductor** — triplen (3rd, 9th…) harmonics add arithmetically in the shared neutral and can exceed phase current. K-rating is a heat rating, not a power-quality fix; if voltage distortion is the problem, that's harmonic-mitigating transformers or filters, a different tool.

## 7. Derating (ambient, altitude, harmonics)
Standard ratings assume 40°C ambient (some tables 30°C) at sea level.
- **Ambient:** above 40°C, derate dry-type ~8% per 10°C (≈1% per °C is the field rule of thumb).
- **Altitude:** above 3300 ft, derate ~0.3% per additional 330 ft.
- **Harmonics (if not using a K-rated unit):** THD > 15% → consider derating to ~90% of nameplate.
These can push you to the next larger standard size. Conductor derating is separate and lives in NEC 310.15 (ambient + conductor-count adjustment); the calculator's conductor size is a 75°C first pass with no derating — always re-check against Table 310.16 with the real ambient and conduit fill before issuing.

## 8. Why the conductor sizes from the script are "first pass"
The script picks the smallest 75°C conductor whose ampacity ≥ 125% FLA. It does not apply 310.15 ambient/conduit-fill adjustment, parallel-conductor sets, voltage-drop checks, or the 240.4(D) small-conductor rule beyond the standard table. For a real submittal: run voltage drop (≤3% feeder is the usual target), apply derating, and confirm the terminations are rated for the temperature column you sized at. The conductor must also satisfy whichever 240.21(C) tap-rule ampacity floor applies (see nec-requirements.md §2).
