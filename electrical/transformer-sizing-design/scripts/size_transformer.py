#!/usr/bin/env python3
"""
size_transformer.py — Deterministic dry-type transformer sizer (NEC 2023).

Single source of truth for the numbers in the transformer-sizing-design skill.
Encodes: FLA, standard-kVA rounding, Table 450.3(B) OCPD logic (incl. the 9A/2A
branches and the Note-1 rounding asymmetry), first-pass conductor sizing from a
75C ampacity table, 240.21(C) tap-rule selection, and 250.30 grounding-conductor
sizing (Tables 250.66 and 250.102(C)(1)).

It prints a structured report AND the assumptions/flags so the calling agent can
read them back to the user. Hand-calculation is discouraged because the rounding
rules and 9A threshold are easy to get wrong.

USAGE
  python3 size_transformer.py --load-kva 95 \
      --primary-v 480 --primary-phase 3 \
      --secondary-v 208 --secondary-phase 3 \
      --secondary-ocpd yes --spare 0.25 --nonlinear-pct 40 \
      --conductor cu --sec-length 8

  # size from kW instead of kVA:
  python3 size_transformer.py --load-kw 60 --pf 0.9 ... 

All flags: --help
"""
import argparse
import math
import sys

# ---- Standard ratings ---------------------------------------------------------
STD_KVA_3PH = [15, 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000, 1500, 2000, 2500]
STD_KVA_1PH = [15, 25, 37.5, 50, 75, 100, 167, 250, 333, 500, 667, 833]
# NEC 240.6(A) standard OCPD ampere ratings
STD_OCPD = [15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 110, 125, 150,
            175, 200, 225, 250, 300, 350, 400, 450, 500, 600, 700, 800, 1000,
            1200, 1600, 2000, 2500, 3000, 4000, 5000, 6000]

# ---- 75C ampacity, Table 310.16 (copper / aluminum), common building sizes ----
# (size_label, copper_75C_amp, aluminum_75C_amp). Used for a FIRST-PASS size only;
# real designs verify against the full table with derating.
AMPACITY_75C = [
    ("14 AWG", 20, None), ("12 AWG", 25, 20), ("10 AWG", 35, 30),
    ("8 AWG", 50, 40), ("6 AWG", 65, 50), ("4 AWG", 85, 65),
    ("3 AWG", 100, 75), ("2 AWG", 115, 90), ("1 AWG", 130, 100),
    ("1/0 AWG", 150, 120), ("2/0 AWG", 175, 135), ("3/0 AWG", 200, 155),
    ("4/0 AWG", 230, 180), ("250 kcmil", 255, 205), ("300 kcmil", 285, 230),
    ("350 kcmil", 310, 250), ("400 kcmil", 335, 270), ("500 kcmil", 380, 310),
    ("600 kcmil", 420, 340), ("700 kcmil", 460, 375), ("750 kcmil", 475, 385),
    ("800 kcmil", 490, 395), ("1000 kcmil", 545, 445),
]
# small-conductor rule 240.4(D): 14->15A, 12->20A, 10->30A max OCPD regardless of table
SMALL_COND_MAX = {"14 AWG": 15, "12 AWG": 20, "10 AWG": 30}

# ---- GEC, Table 250.66 (by largest ungrounded conductor area) -----------------
# list of (max_cu_size_or_kcmil, max_al, gec_cu, gec_al). Compared by area rank.
# Simplified to the standard table rows.
T250_66 = [
    # (cu_up_to, al_up_to, gec_cu, gec_al)
    ("2 AWG", "1/0 AWG", "8 AWG", "6 AWG"),
    ("1 AWG", "2/0 AWG", "6 AWG", "4 AWG"),   # 1 or 1/0 cu / 2/0-3/0 al
    ("2/0 AWG", "4/0 AWG", "4 AWG", "2 AWG"),
    ("3/0 AWG", "4/0 AWG", "4 AWG", "2 AWG"),
    ("350 kcmil", "500 kcmil", "2 AWG", "1/0 AWG"),
    ("600 kcmil", "900 kcmil", "1/0 AWG", "3/0 AWG"),
    ("1100 kcmil", "1750 kcmil", "2/0 AWG", "4/0 AWG"),
    ("BIG", "BIG", "3/0 AWG", "250 kcmil"),
]

# rank conductors by area for comparisons
AREA_RANK = {lbl: i for i, (lbl, _, _) in enumerate(AMPACITY_75C)}
AREA_RANK["1100 kcmil"] = 99
AREA_RANK["900 kcmil"] = 98
AREA_RANK["1750 kcmil"] = 100
AREA_RANK["BIG"] = 999


def fla(kva, volts, phase):
    if phase == 3:
        return kva * 1000.0 / (volts * math.sqrt(3))
    return kva * 1000.0 / volts


def round_up_std(value, table):
    for s in table:
        if s >= value - 1e-9:
            return s
    return table[-1]  # cap


def round_down_std(value, table):
    """Largest standard size <= value. Returns None if value is below the
    smallest standard size (caller must flag — a 'max' rule can't be satisfied
    by going UP to the next standard size)."""
    if value < table[0] - 1e-9:
        return None
    chosen = table[0]
    for s in table:
        if s <= value + 1e-9:
            chosen = s
        else:
            break
    return chosen


def select_kva(demand_kva, spare, phase):
    target = demand_kva * (1.0 + spare)
    table = STD_KVA_3PH if phase == 3 else STD_KVA_1PH
    return round_up_std(target, table), target


def ocpd_primary(fla_pri, secondary_ocpd):
    """Return (amps, pct_applied, rule_note). Table 450.3(B), <=1000V.
    amps may be None if the max% rule lands below the smallest standard OCPD —
    caller flags this (typical for tiny control transformers protected upstream)."""
    if fla_pri >= 9:
        if secondary_ocpd:
            # 250% column, secondary protection present. Note 1 does NOT apply -> round DOWN.
            raw = fla_pri * 2.50
            amp = round_down_std(raw, STD_OCPD)
            return amp, 250, "<=250% (sec protection present); Note 1 N/A, do not round up"
        else:
            # 125% primary-only. Note 1 applies -> may round UP to next standard.
            raw = fla_pri * 1.25
            amp = round_up_std(raw, STD_OCPD)
            return amp, 125, "<=125% primary-only; Note 1 allows round up to next std"
    elif fla_pri >= 2:
        raw = fla_pri * 1.67
        amp = round_down_std(raw, STD_OCPD)
        return amp, 167, "primary FLA 2-9A: <=167% (Note 1 N/A)"
    else:
        raw = fla_pri * 3.00
        amp = round_down_std(raw, STD_OCPD)
        return amp, 300, "primary FLA <2A: <=300% (Note 1 N/A)"


def ocpd_secondary(fla_sec):
    """125% secondary, Note 1 allows round up. Only meaningful if sec >=9A here."""
    raw = fla_sec * 1.25
    amp = round_up_std(raw, STD_OCPD)
    return amp, 125, "<=125% sec FLA; Note 1 allows round up"


def size_conductor(required_amp, conductor):
    """First-pass: smallest 75C conductor whose ampacity >= required_amp."""
    idx = 1 if conductor == "cu" else 2
    for lbl, cu, al in AMPACITY_75C:
        amp = cu if idx == 1 else al
        if amp is None:
            continue
        if amp >= required_amp - 1e-9:
            return lbl, amp
    return AMPACITY_75C[-1][0], (AMPACITY_75C[-1][idx])


def gec_size(sec_cond_label, conductor):
    rank = AREA_RANK.get(sec_cond_label, 0)
    for cu_up, al_up, gec_cu, gec_al in T250_66:
        cap = AREA_RANK.get(cu_up if conductor == "cu" else al_up, 999)
        if rank <= cap:
            return gec_cu if conductor == "cu" else gec_al
    return "3/0 AWG" if conductor == "cu" else "250 kcmil"


def sbj_size(sec_cond_label, conductor):
    # Table 250.102(C)(1) tracks 250.66 closely for typical sizes; reuse for first pass.
    return gec_size(sec_cond_label, conductor)


def k_factor(nonlinear_pct):
    if nonlinear_pct is None:
        return None, "not specified"
    if nonlinear_pct < 15:
        return "K-1 (standard)", "<15% nonlinear: standard transformer ok"
    if nonlinear_pct <= 35:
        return "K-4", "up to ~35% nonlinear"
    if nonlinear_pct <= 75:
        return "K-13", "up to ~75% nonlinear (offices/schools/hospitals default)"
    return "K-20", ">75%/100% electronic (data-center PDU class)"


def tap_rule(sec_length, secondary_ocpd):
    if sec_length is None:
        return "UNKNOWN", "secondary conductor length not given — cannot confirm 240.21(C) scenario"
    if not secondary_ocpd:
        return "see 450.3(B)", ("primary-only protection: secondary conductors are generally NOT "
                                "protected by the primary device except 1φ 2-wire / 3φ Δ-Δ 3-wire. "
                                "If a downstream OCPD exists, this is really 'both' — re-check intake.")
    if sec_length <= 10:
        return "240.21(C)(2) 10-ft", ("ampacity >= load AND >= (primary OCPD x V_pri/V_sec)/10; "
                                       "terminate in single OCPD; stay in enclosure/raceway; not outside")
    if sec_length <= 25:
        return "240.21(C)(6) 25-ft", ("ampacity >= (primary OCPD x V_pri/V_sec)/3; single OCPD; "
                                       "protected from damage")
    return "240.21(C)(4)/(1) >25ft/outside", "long/outside secondary — see reference, stricter conditions"


def main():
    p = argparse.ArgumentParser(description="NEC 2023 transformer sizer")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--load-kva", type=float, help="demand load in kVA")
    g.add_argument("--load-kw", type=float, help="demand load in kW (needs --pf)")
    g.add_argument("--kva", type=float, help="known transformer kVA (skip selection)")
    p.add_argument("--pf", type=float, default=0.9, help="power factor if load given in kW (default 0.9)")
    p.add_argument("--spare", type=float, default=0.25, help="spare-capacity fraction (default 0.25)")
    p.add_argument("--primary-v", type=float, required=True)
    p.add_argument("--secondary-v", type=float, required=True)
    p.add_argument("--primary-phase", type=int, choices=[1, 3], default=3)
    p.add_argument("--secondary-phase", type=int, choices=[1, 3], default=3)
    p.add_argument("--secondary-ocpd", choices=["yes", "no"], default="yes",
                   help="is there a secondary-side OCPD? drives 125% vs 250% primary")
    p.add_argument("--conductor", choices=["cu", "al"], default="cu")
    p.add_argument("--sec-length", type=float, default=None,
                   help="secondary conductor length ft (transformer -> first OCPD)")
    p.add_argument("--nonlinear-pct", type=float, default=None,
                   help="percent nonlinear load for K-factor")
    args = p.parse_args()

    assumptions = []
    flags = []

    # --- load -> kVA ---
    if args.kva is not None:
        kva = args.kva
        demand_kva = None
        assumptions.append(f"Transformer kVA given directly: {kva}")
    else:
        if args.load_kva is not None:
            demand_kva = args.load_kva
        else:
            demand_kva = args.load_kw / args.pf
            assumptions.append(f"Converted {args.load_kw} kW at PF {args.pf} -> {demand_kva:.1f} kVA demand")
        kva, target = select_kva(demand_kva, args.spare, args.secondary_phase)
        assumptions.append(f"Sized to {args.spare*100:.0f}% spare: demand {demand_kva:.1f} x "
                           f"{1+args.spare:.2f} = {target:.1f} kVA -> next std {kva} kVA")

    sec_ocpd = args.secondary_ocpd == "yes"
    if args.secondary_ocpd == "yes":
        assumptions.append("Secondary OCPD present -> 250% primary column available")
    else:
        assumptions.append("Primary-only protection assumed -> 125% primary cap")

    # --- FLA ---
    fla_p = fla(kva, args.primary_v, args.primary_phase)
    fla_s = fla(kva, args.secondary_v, args.secondary_phase)

    # --- OCPD ---
    op_amp, op_pct, op_note = ocpd_primary(fla_p, sec_ocpd)
    if op_amp is None:
        flags.append(f"Primary OCPD max ({op_pct}% of {fla_p:.1f}A = {fla_p*op_pct/100:.1f}A) is below the "
                     f"smallest standard breaker (15A). This transformer is typically protected by the "
                     f"upstream branch-circuit OCPD; do not install a 15A primary device that exceeds the max.")
    if sec_ocpd:
        os_amp, os_pct, os_note = ocpd_secondary(fla_s)
    else:
        os_amp = os_pct = os_note = None

    # --- conductors (first pass, at OCPD rating or 125% load) ---
    # primary feeder sized to carry >=125% pri FLA (continuous) but not exceed OCPD;
    # for first pass, size to the OCPD rating's protection (conductor ampacity >= ~ FLA*1.25).
    pri_cond_amp = max(fla_p * 1.25, 0)
    pri_cond, pri_cond_ampacity = size_conductor(pri_cond_amp, args.conductor)
    sec_cond_amp = fla_s * 1.25
    sec_cond, sec_cond_ampacity = size_conductor(sec_cond_amp, args.conductor)

    # If a 250% primary OCPD exceeds the primary feeder ampacity, the primary
    # conductors are themselves not protected at their ampacity by that device —
    # they rely on being part of the transformer circuit (Art. 450) / the 125% basis.
    if op_amp is not None and op_amp > pri_cond_ampacity + 1e-9:
        flags.append(f"Primary OCPD ({op_amp}A) exceeds primary feeder ampacity ({pri_cond_ampacity}A on "
                     f"{pri_cond}). At 250% this is expected — the primary conductors are sized to 125% FLA "
                     f"and protected as part of the transformer circuit, not by the {op_amp}A device. Confirm "
                     f"this is intended and that the feeder run/voltage-drop is acceptable.")

    # --- grounding ---
    gec = gec_size(sec_cond, args.conductor)
    sbj = sbj_size(sec_cond, args.conductor)

    # --- k factor ---
    kf, kf_note = k_factor(args.nonlinear_pct)
    if kf and "K-1" not in kf and kf != "K-1 (standard)" and args.nonlinear_pct and args.nonlinear_pct >= 35:
        flags.append(f"Nonlinear load {args.nonlinear_pct:.0f}% -> specify {kf} AND 200% neutral bus + upsized neutral conductor")

    # --- tap rule ---
    tr, tr_note = tap_rule(args.sec_length, sec_ocpd)
    if tr == "UNKNOWN":
        flags.append("Secondary conductor length not provided — cannot finalize 240.21(C) tap rule; ASK the user.")

    # --- installation flag ---
    if kva > 112.5:
        flags.append(f"{kva} kVA > 112.5 kVA -> requires fire-resistant room, min 1-hr rating (450.21(B)) unless an exception applies")
    else:
        flags.append(f"{kva} kVA <= 112.5 kVA -> min 12 in from combustibles unless fire-rated barrier (450.21(A))")

    # --- inrush sanity ---
    if not sec_ocpd:
        flags.append("Primary-only at 125%: DOE-2016/K-rated units can inrush 12-25x FLA and nuisance-trip. "
                     "Consider secondary OCPD + 250% primary, or a high-instantaneous (D-curve/STD) device.")

    # --- print report ---
    def amp(x): return f"{x:.1f} A" if x is not None else "n/a"
    print("=" * 64)
    print("TRANSFORMER SIZING REPORT (NEC 2023)")
    print("=" * 64)
    print(f"Rating:            {kva} kVA, "
          f"{args.primary_phase}\u03c6 pri / {args.secondary_phase}\u03c6 sec")
    print(f"Voltage:           {args.primary_v:g}V primary -> {args.secondary_v:g}V secondary")
    if kf:
        print(f"K-factor:          {kf}  ({kf_note})")
    print("-" * 64)
    print(f"Primary FLA:       {fla_p:.1f} A")
    print(f"Secondary FLA:     {fla_s:.1f} A")
    print("-" * 64)
    op_display = f"{op_amp} A" if op_amp is not None else "see flag (below smallest std)"
    print(f"Primary OCPD:      {op_display}   [{op_pct}% rule] {op_note}")
    if sec_ocpd:
        print(f"Secondary OCPD:    {os_amp} A   [{os_pct}% rule] {os_note}")
    else:
        print("Secondary OCPD:    none (primary-only)")
    print("-" * 64)
    print(f"Primary feeder:    {pri_cond} {args.conductor.upper()} (75C amp {pri_cond_ampacity}A) "
          f"[>=125% pri FLA = {pri_cond_amp:.1f}A]")
    print(f"Secondary cond.:   {sec_cond} {args.conductor.upper()} (75C amp {sec_cond_ampacity}A) "
          f"[>=125% sec FLA = {sec_cond_amp:.1f}A]")
    print(f"Tap rule:          {tr}")
    print(f"                   {tr_note}")
    print("-" * 64)
    print("GROUNDING (if separately derived system per 250.30):")
    print(f"  System bonding jumper:  {sbj}  (Table 250.102(C)(1), on sec ungrounded)")
    print(f"  Grounding electrode cond:{gec}  (Table 250.66, on sec ungrounded)")
    print(f"  Bond N-G at ONE point (transformer OR secondary disconnect, not both)")
    print("=" * 64)
    print("ASSUMPTIONS:")
    for a in assumptions:
        print(f"  - {a}")
    print("FLAGS / VERIFY:")
    for f in flags:
        print(f"  ! {f}")
    print("=" * 64)
    print("NOTE: conductor sizes are FIRST-PASS at 75C with no derating. Verify against")
    print("Table 310.16 with ambient/CCC derating (310.15) and termination temp before issue.")


if __name__ == "__main__":
    main()
