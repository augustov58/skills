#!/usr/bin/env python3
"""
size_transformer.py - Deterministic dry-type transformer sizer (NEC 2023).

Single source of truth for the numbers in the transformer-sizing-design skill.

Encodes:
  * FLA, standard-kVA rounding (next NEMA size, with spare-capacity factor)
  * Table 450.3(B) OCPD logic with the 9A / 2A branches and the Note-1
    rounding asymmetry (round UP only on the 125% values; the higher-multiple
    ceilings round DOWN).
  * PRIMARY OCPD <-> PRIMARY CONDUCTOR COUPLING.  450.3(B) protects the
    *transformer*; 240.4 protects the *conductor*.  On a radial primary feeder
    the same device does both jobs, so the OCPD may not exceed what 240.4(B)
    allows for the conductor.  The 250% column is therefore OPT-IN (inrush or a
    240.21(B) primary tap), and when invoked it FORCES the primary conductor up
    to the OCPD rating (radial) or hands off to the tap rule (tap).  No more
    "225A breaker on 2 AWG, protected as part of the transformer circuit."
  * SECONDARY OCPD capped at a downstream panelboard bus rating (408.36) and
    floored at 125% of the continuous secondary load (215.3).
  * SECONDARY CONDUCTOR sized to the secondary OCPD it terminates in
    (240.21(C) / 240.4(F)), then checked against the 240.21(C) tap-rule
    ampacity floor (which this script now actually computes, not just names).
  * 250.30 grounding-conductor sizing (Tables 250.66 / 250.102(C)(1)).
  * 110.14(C) termination temperature: 75C default, 60C available, and the
    <=100A 60C-default reminder.

It prints a structured report plus ASSUMPTIONS and FLAGS / VERIFY blocks so the
calling agent can read them back.  Hand-calculation is discouraged.

USAGE
  python3 size_transformer.py --load-kva 65 \
      --primary-v 480 --primary-phase 3 \
      --secondary-v 208 --secondary-phase 3 \
      --secondary-ocpd yes --panel-bus 225 \
      --spare 0 --conductor cu --sec-length 8

  # size from kW:    --load-kw 60 --pf 0.9
  # size from amps:  --load-amps 180        (interpreted at the SECONDARY voltage)
  # known kVA:       --kva 75
  # high inrush:     --primary-basis inrush   (or max)  -> upsizes primary conductor
  # primary is a tap:--primary-tap            -> conductor per 240.21(B), not coupled

All flags: --help
"""
import argparse
import math

SIZER_VERSION = "2.0.0-coupled-ocpd+riser (2026-06-18)"

# ---- Standard ratings ---------------------------------------------------------
STD_KVA_3PH = [15, 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000, 1500, 2000, 2500]
STD_KVA_1PH = [15, 25, 37.5, 50, 75, 100, 167, 250, 333, 500, 667, 833]
# NEC 240.6(A) standard OCPD ampere ratings
STD_OCPD = [15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 110, 125, 150,
            175, 200, 225, 250, 300, 350, 400, 450, 500, 600, 700, 800, 1000,
            1200, 1600, 2000, 2500, 3000, 4000, 5000, 6000]

# ---- Ampacity, Table 310.16 (60C / 75C, copper / aluminum) --------------------
# (label, cu60, cu75, al60, al75).  FIRST-PASS sizing only; real designs verify
# the full table with derating (310.15).  None = size not rated at that temp/metal.
AMPACITY = [
    ("14 AWG",   15,  20,  None, None),
    ("12 AWG",   20,  25,  15,   20),
    ("10 AWG",   30,  35,  25,   30),
    ("8 AWG",    40,  50,  30,   40),
    ("6 AWG",    55,  65,  40,   50),
    ("4 AWG",    70,  85,  55,   65),
    ("3 AWG",    85,  100, 65,   75),
    ("2 AWG",    95,  115, 75,   90),
    ("1 AWG",    110, 130, 85,   100),
    ("1/0 AWG",  125, 150, 100,  120),
    ("2/0 AWG",  145, 175, 115,  135),
    ("3/0 AWG",  165, 200, 130,  155),
    ("4/0 AWG",  195, 230, 150,  180),
    ("250 kcmil", 215, 255, 170, 205),
    ("300 kcmil", 240, 285, 195, 230),
    ("350 kcmil", 260, 310, 210, 250),
    ("400 kcmil", 280, 335, 225, 270),
    ("500 kcmil", 320, 380, 260, 310),
    ("600 kcmil", 355, 420, 285, 340),
    ("700 kcmil", 385, 460, 315, 375),
    ("750 kcmil", 400, 475, 320, 385),
    ("800 kcmil", 410, 490, 330, 395),
    ("1000 kcmil", 455, 545, 375, 445),
]
# small-conductor rule 240.4(D): hard OCPD caps regardless of ampacity column
SMALL_COND_MAX = {"14 AWG": 15, "12 AWG": 20, "10 AWG": 30}

# ---- GEC, Table 250.66 (by largest ungrounded conductor area) -----------------
T250_66 = [
    ("2 AWG", "1/0 AWG", "8 AWG", "6 AWG"),
    ("1 AWG", "2/0 AWG", "6 AWG", "4 AWG"),
    ("2/0 AWG", "4/0 AWG", "4 AWG", "2 AWG"),
    ("3/0 AWG", "4/0 AWG", "4 AWG", "2 AWG"),
    ("350 kcmil", "500 kcmil", "2 AWG", "1/0 AWG"),
    ("600 kcmil", "900 kcmil", "1/0 AWG", "3/0 AWG"),
    ("1100 kcmil", "1750 kcmil", "2/0 AWG", "4/0 AWG"),
    ("BIG", "BIG", "3/0 AWG", "250 kcmil"),
]

AREA_RANK = {lbl: i for i, (lbl, *_rest) in enumerate(AMPACITY)}
AREA_RANK["900 kcmil"] = 98
AREA_RANK["1100 kcmil"] = 99
AREA_RANK["1750 kcmil"] = 100
AREA_RANK["BIG"] = 999

_COL = {("cu", 60): 1, ("cu", 75): 2, ("al", 60): 3, ("al", 75): 4}


# ---- helpers ------------------------------------------------------------------
def fla(kva, volts, phase):
    return kva * 1000.0 / (volts * math.sqrt(3)) if phase == 3 else kva * 1000.0 / volts


def kva_from_amps(amps, volts, phase):
    return amps * volts * (math.sqrt(3) if phase == 3 else 1) / 1000.0


def round_up_std(value, table):
    for s in table:
        if s >= value - 1e-9:
            return s
    return table[-1]


def round_down_std(value, table):
    """Largest standard size <= value, or None if below the smallest size."""
    if value < table[0] - 1e-9:
        return None
    chosen = table[0]
    for s in table:
        if s <= value + 1e-9:
            chosen = s
        else:
            break
    return chosen


def ampacity_of(label, conductor, term):
    col = _COL[(conductor, term)]
    for row in AMPACITY:
        if row[0] == label:
            return row[col]
    return None


def size_conductor(required_amp, conductor, term):
    """Smallest conductor whose ampacity at this metal/temp >= required_amp."""
    col = _COL[(conductor, term)]
    for row in AMPACITY:
        amp = row[col]
        if amp is not None and amp >= required_amp - 1e-9:
            return row[0], amp
    last = AMPACITY[-1]
    return last[0], last[col]


def largest_ampacity(conductor, term):
    col = _COL[(conductor, term)]
    return max(r[col] for r in AMPACITY if r[col] is not None)


def max_ocpd_for_conductor(label, conductor, term):
    """240.4(B): the next standard OCPD at or above the conductor ampacity is
    permitted (<=800A, not for receptacle branch circuits). 240.4(D) caps for
    14/12/10 AWG override."""
    amps = ampacity_of(label, conductor, term)
    if amps is None:
        return 0
    allowed = round_up_std(amps, STD_OCPD)
    if allowed > 800:
        allowed = round_down_std(amps, STD_OCPD)
    if label in SMALL_COND_MAX:
        allowed = min(allowed, SMALL_COND_MAX[label])
    return allowed


def select_kva(demand_kva, spare, phase):
    target = demand_kva * (1.0 + spare)
    table = STD_KVA_3PH if phase == 3 else STD_KVA_1PH
    return round_up_std(target, table), target


def primary_ocpd_max(fla_pri, secondary_ocpd, basis):
    """Return (amps, pct, note). 'basis' = 'min' (125%, default) or 'max'/'inrush'
    (up to 250%, only legal WITH secondary protection)."""
    if fla_pri < 2:
        return round_down_std(fla_pri * 3.00, STD_OCPD), 300, "primary FLA <2A: <=300% (Note 1 N/A)"
    if fla_pri < 9:
        return round_down_std(fla_pri * 1.67, STD_OCPD), 167, "primary FLA 2-9A: <=167% (Note 1 N/A)"
    if basis in ("max", "inrush"):
        if not secondary_ocpd:
            return (round_up_std(fla_pri * 1.25, STD_OCPD), 125,
                    "250% requested but NO secondary protection -> not permitted; reverted to <=125%. "
                    "Add a secondary OCPD to use 250%.")
        return (round_down_std(fla_pri * 2.50, STD_OCPD), 250,
                "<=250% ceiling (sec protection present); Note 1 N/A, round DOWN")
    return (round_up_std(fla_pri * 1.25, STD_OCPD), 125,
            "<=125% basis (Note 1 allows round up to next std)")


def secondary_ocpd_size(fla_sec, panel_bus, cont_load_amps):
    """125% sec FLA (Note 1 round up), capped at panel bus (408.36) and checked
    against the continuous-load floor (215.3)."""
    flags = []
    amp = round_up_std(fla_sec * 1.25, STD_OCPD)
    note = "<=125% sec FLA (Note 1 round-up)"
    if panel_bus is not None:
        bus_std = round_down_std(panel_bus, STD_OCPD) or panel_bus
        if amp > bus_std:
            flags.append(f"125% sec FLA wants {amp}A but the downstream panel bus is {panel_bus:g}A. "
                         f"408.36 forbids an OCPD above the bus rating -> secondary OCPD CAPPED at "
                         f"{bus_std:g}A. (450.3(B) only sets the MAX; you may use less.)")
            amp = bus_std
            note = f"capped at panel bus {bus_std:g}A (408.36)"
    if cont_load_amps is not None:
        if amp < cont_load_amps * 1.25 - 1e-9:
            flags.append(f"Secondary OCPD {amp}A is below 125% of the {cont_load_amps:.0f}A continuous load "
                         f"({cont_load_amps*1.25:.0f}A). Cannot serve the load continuously - raise the panel "
                         f"bus or reduce load.")
        else:
            note += f"; >=125% x {cont_load_amps:.0f}A cont OK"
    return amp, note, flags


def gec_size(cond_label, conductor):
    rank = AREA_RANK.get(cond_label, 0)
    for cu_up, al_up, gec_cu, gec_al in T250_66:
        cap = AREA_RANK.get(cu_up if conductor == "cu" else al_up, 999)
        if rank <= cap:
            return gec_cu if conductor == "cu" else gec_al
    return "3/0 AWG" if conductor == "cu" else "250 kcmil"


def _is_wye(label):
    """Loose label test; handles 'Y', 'Wye', '208Y/120', and rejects 'Delta'/'Δ'."""
    u = (label or "").upper()
    if "DELTA" in u:
        return False
    return "WYE" in u or "STAR" in u or "Y" in u


def separately_derived(sds_arg, pri_conn, sec_conn, pri_phase, sec_phase):
    """Decide 250.30 SDS status from the CONNECTION, not the phase count.

    A separately derived system has no direct electrical connection to the
    supply conductors, INCLUDING a solidly connected grounded (neutral)
    conductor. A delta on either side cannot carry a neutral through, so those
    are always separately derived. Y-Y cannot be settled from ratings alone --
    a factory H0-X0 link makes it NOT separately derived -- so it is assumed
    SDS and flagged for nameplate confirmation.

    Returns (sds, assumption, flag); flag is None unless confirmation is due.
    """
    if sds_arg == "yes":
        return True, "SDS: forced by --sds yes; 250.30 applies.", None
    if sds_arg == "no":
        return False, ("SDS: forced by --sds no; 250.30 does NOT apply, so no SBJ/GEC at the "
                       "transformer."), None
    if pri_phase == 1 or sec_phase == 1:
        return True, ("SDS: assumed for a 1-phase transformer (no supply neutral carried into the "
                      "secondary). Pass --sds no if the secondary neutral is bonded to the supply "
                      "neutral."), None
    if _is_wye(pri_conn) and _is_wye(sec_conn):
        return True, "SDS: Y-Y assumed separately derived (see flag).", (
            "Y-Y connection: a factory H0-X0 neutral link makes this NOT a separately derived "
            "system -- 250.30 would not apply and the SBJ/GEC below would be wrong. Confirm the "
            "nameplate and rerun with --sds no if the neutral is carried through.")
    return True, (f"SDS: {pri_conn}-{sec_conn} carries no supply neutral into the secondary, so it "
                  f"is separately derived (250.30 applies)."), None


def k_factor(nonlinear_pct):
    if nonlinear_pct is None:
        return None, "not specified"
    if nonlinear_pct < 15:
        return "K-1 (standard)", "<15% nonlinear: standard transformer ok"
    if nonlinear_pct <= 35:
        return "K-4", "up to ~35% nonlinear"
    if nonlinear_pct <= 75:
        return "K-13", "up to ~75% nonlinear (offices/schools/hospitals default)"
    return "K-20", ">75% electronic (data-center PDU class)"


def main():
    p = argparse.ArgumentParser(description="NEC 2023 transformer sizer")
    p.add_argument("--version", action="version", version=f"%(prog)s {SIZER_VERSION}")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--load-kva", type=float, help="demand load in kVA")
    g.add_argument("--load-kw", type=float, help="demand load in kW (needs --pf)")
    g.add_argument("--load-amps", type=float, help="demand load in A at the SECONDARY voltage")
    g.add_argument("--kva", type=float, help="known transformer kVA (skip selection)")
    p.add_argument("--pf", type=float, default=0.9, help="PF if load given in kW (default 0.9)")
    p.add_argument("--spare", type=float, default=0.25,
                   help="spare fraction (default 0.25). Pass 0 if the load already includes headroom.")
    p.add_argument("--primary-v", type=float, required=True)
    p.add_argument("--secondary-v", type=float, required=True)
    p.add_argument("--primary-phase", type=int, choices=[1, 3], default=3)
    p.add_argument("--secondary-phase", type=int, choices=[1, 3], default=3)
    p.add_argument("--secondary-ocpd", choices=["yes", "no"], default="yes",
                   help="is there a secondary OCPD? gates the 250 pct primary option")
    p.add_argument("--primary-basis", choices=["min", "inrush", "max"], default="min",
                   help="min=125%% (default); inrush/max=up to 250%% (needs sec OCPD; upsizes pri conductor)")
    p.add_argument("--primary-tap", action="store_true",
                   help="primary conductors are a 240.21(B) tap off a larger feeder (not coupled to the OCPD)")
    p.add_argument("--panel-bus", type=float, default=None,
                   help="downstream panelboard bus rating (A) to cap the secondary OCPD per 408.36")
    p.add_argument("--conductor", choices=["cu", "al"], default="cu")
    p.add_argument("--term-temp", choices=["auto", "60", "75"], default="auto",
                   help="termination temp column (110.14(C)). auto = 60C for <=100A circuits else 75C")
    p.add_argument("--sec-length", type=float, default=None,
                   help="secondary conductor length ft (transformer -> first OCPD)")
    p.add_argument("--nonlinear-pct", type=float, default=None)
    p.add_argument("--format", choices=["report", "json"], default="report",
                   help="report = human text (default); json = machine dict for draw_riser.py")
    p.add_argument("--tag", default="T-1", help="transformer tag for the diagram")
    p.add_argument("--source-tag", default="HP", help="upstream (primary) panel tag")
    p.add_argument("--load-tag", default="LP", help="downstream (secondary) panel tag")
    p.add_argument("--primary-conn", default=None, help="primary connection label (e.g. Delta); default inferred")
    p.add_argument("--secondary-conn", default=None, help="secondary connection label (e.g. Y); default inferred")
    p.add_argument("--sds", choices=["auto", "yes", "no"], default="auto",
                   help="separately derived system (250.30). auto = infer from the connection; "
                        "pass 'no' for a Y-Y with a factory H0-X0 neutral link")
    args = p.parse_args()

    assumptions, flags = [], []

    # --- load -> demand kVA --------------------------------------------------
    cont_sec_amps = None
    if args.kva is not None:
        kva = args.kva
        assumptions.append(f"Transformer kVA given directly: {kva}")
    else:
        if args.load_kva is not None:
            demand_kva = args.load_kva
        elif args.load_kw is not None:
            demand_kva = args.load_kw / args.pf
            assumptions.append(f"Converted {args.load_kw} kW at PF {args.pf} -> {demand_kva:.1f} kVA")
            flags.append("Load given in kW: PF assumed - confirm it is not already apparent power (kVA).")
        else:
            demand_kva = kva_from_amps(args.load_amps, args.secondary_v, args.secondary_phase)
            assumptions.append(f"Load {args.load_amps:g}A at {args.secondary_v:g}V "
                               f"{args.secondary_phase}\u03c6 -> {demand_kva:.1f} kVA")
        cont_sec_amps = fla(demand_kva, args.secondary_v, args.secondary_phase)
        kva, target = select_kva(demand_kva, args.spare, args.secondary_phase)
        if args.spare == 0:
            assumptions.append(f"No extra spare (--spare 0): demand {demand_kva:.1f} kVA -> next std {kva} kVA")
        else:
            assumptions.append(f"{args.spare*100:.0f}% spare: {demand_kva:.1f} x {1+args.spare:.2f} "
                               f"= {target:.1f} kVA -> next std {kva} kVA")

    sec_ocpd = args.secondary_ocpd == "yes"
    assumptions.append("Secondary OCPD present" if sec_ocpd else "Primary-only protection")

    # --- FLA -----------------------------------------------------------------
    fla_p = fla(kva, args.primary_v, args.primary_phase)
    fla_s = fla(kva, args.secondary_v, args.secondary_phase)

    # --- PRIMARY OCPD (transformer protection, 450.3(B)) ---------------------
    op_amp, op_pct, op_note = primary_ocpd_max(fla_p, sec_ocpd, args.primary_basis)

    # --- SECONDARY OCPD ------------------------------------------------------
    if sec_ocpd:
        os_amp, os_note, os_flags = secondary_ocpd_size(fla_s, args.panel_bus, cont_sec_amps)
        flags.extend(os_flags)
    else:
        os_amp = os_note = None

    # --- termination temp (110.14(C)) ----------------------------------------
    # Keyed off the OCPD ratings (the circuit), not transformer FLA: 110.14(C)(1)
    # uses the 60C column for circuits <=100A unless terminations are listed 75C.
    if args.term_temp == "auto":
        circuit_amps = max(op_amp or 0, os_amp or (fla_s * 1.25))
        term = 60 if circuit_amps <= 100 else 75
        assumptions.append(f"Termination temp auto = {term}C (110.14(C): 60C if circuit <=100A by OCPD, "
                           f"else 75C). Override with --term-temp if gear is listed otherwise.")
    else:
        term = int(args.term_temp)
        assumptions.append(f"Termination temp forced {term}C")

    big = largest_ampacity(args.conductor, term)

    # --- PRIMARY CONDUCTOR (240.4 / 240.21(B)) -------------------------------
    pri_base_amp = fla_p * 1.25                                   # continuous feeder, 215.2
    pri_parallel = pri_base_amp > big
    pri_cond, pri_amp = size_conductor(pri_base_amp, args.conductor, term)

    if pri_parallel:
        flags.append(f"Primary feeder needs {pri_base_amp:.0f}A > largest first-pass single conductor "
                     f"({big}A {args.conductor.upper()}). Use PARALLEL sets per 310.10(G) and size by hand; "
                     f"the single-conductor value below is NOT valid. Primary OCPD held at the true "
                     f"{op_pct}% value.")
    elif args.primary_tap:
        pri_method = "240.21(B) primary tap (conductor NOT coupled to OCPD)"
        flags.append("Primary marked as a 240.21(B) TAP: primary conductor sized to 125% FLA only. "
                     "VERIFY against the actual upstream feeder OCPD and tap length (10-ft: ampacity "
                     ">= 1/10 of upstream OCPD and terminates in the transformer's primary OCPD; 25-ft: >= 1/3). "
                     "Cannot finalize a primary tap without the upstream feeder rating.")
    else:
        pri_method = "radial feeder (one device protects conductor 240.4 + transformer 450.3(B))"
        if op_amp is not None:
            while op_amp > max_ocpd_for_conductor(pri_cond, args.conductor, term):
                ranks = [r[0] for r in AMPACITY]
                i = ranks.index(pri_cond)
                if i + 1 >= len(ranks):
                    break
                pri_cond = ranks[i + 1]
                pri_amp = ampacity_of(pri_cond, args.conductor, term)
            if args.primary_basis == "min":
                op_amp = min(op_amp, max_ocpd_for_conductor(pri_cond, args.conductor, term))
    if pri_parallel:
        pri_method = "PARALLEL sets required (310.10(G)) - size by hand"

    if op_amp is None:
        flags.append(f"Primary OCPD max ({op_pct}% of {fla_p:.1f}A) is below the smallest standard breaker; "
                     f"this unit is normally protected by the upstream branch OCPD.")

    # --- SECONDARY CONDUCTOR (sized to the OCPD it lands in) -----------------
    if sec_ocpd:
        sec_target = os_amp
        sec_basis = f"sized to secondary OCPD {os_amp}A (240.21(C)/240.4(F); Mike Holt 4b)"
    else:
        sec_target = fla_s * 1.25
        sec_basis = "sized to 125% sec FLA (no secondary OCPD)"
    sec_parallel = sec_target > big
    sec_cond, sec_amp = size_conductor(sec_target, args.conductor, term)
    if sec_parallel:
        flags.append(f"Secondary feeder needs {sec_target:.0f}A > largest first-pass single conductor "
                     f"({big}A {args.conductor.upper()}). Use PARALLEL sets per 310.10(G) and size by hand.")
        sec_basis = "PARALLEL sets required (310.10(G)) - size by hand"

    # --- TAP RULE + ACTUAL AMPACITY FLOOR (240.21(C)) ------------------------
    tap_name, tap_note = "n/a", ""
    if sec_ocpd and args.sec_length is not None and op_amp is not None:
        ref_current = op_amp * args.primary_v / args.secondary_v
        if args.sec_length <= 10:
            tap_name, floor = "240.21(C)(2) 10-ft", ref_current / 10.0
        elif args.sec_length <= 25:
            tap_name, floor = "240.21(C)(6) 25-ft", ref_current / 3.0
        else:
            tap_name, floor = "240.21(C) >25ft / outside", ref_current
        load_floor = cont_sec_amps if cont_sec_amps is not None else fla_s
        need = max(load_floor, floor)
        ok = sec_amp >= need - 1e-9
        tap_note = (f"floor = max(load {load_floor:.0f}A, rule {floor:.0f}A) = {need:.0f}A; "
                    f"chosen {sec_cond} = {sec_amp}A {'OK' if ok else 'TOO SMALL'}; single OCPD")
        if not ok:
            flags.append(f"Secondary conductor {sec_cond} ({sec_amp}A) is below the {tap_name} floor "
                         f"({need:.0f}A). Upsize the secondary conductor.")
    elif sec_ocpd and args.sec_length is None:
        flags.append("Secondary length not given - cannot finalize the 240.21(C) tap rule. ASK the user.")

    # --- capacity mismatch: transformer nameplate vs panel bus ---------------
    if args.panel_bus is not None and fla_s < args.panel_bus - 1e-9:
        flags.append(f"Transformer secondary FLA ({fla_s:.0f}A) is BELOW the {args.panel_bus:g}A panel bus. "
                     f"If the panel is loaded past {fla_s:.0f}A it overloads the transformer (the panel main "
                     f"won't trip until {os_amp}A). Fine if design load stays under {fla_s:.0f}A; otherwise go "
                     f"up one transformer size.")

    # --- grounding (250.30) --------------------------------------------------
    gec = gec_size(sec_cond, args.conductor)
    sbj = gec

    # --- K factor ------------------------------------------------------------
    kf, kf_note = k_factor(args.nonlinear_pct)
    if args.nonlinear_pct is not None and args.nonlinear_pct >= 35:
        flags.append(f"Nonlinear {args.nonlinear_pct:.0f}% -> specify {kf} + 200% neutral bus and upsized neutral.")

    # --- installation (450.21) ----------------------------------------------
    if kva > 112.5:
        flags.append(f"{kva} kVA > 112.5 -> fire-resistant room min 1-hr (450.21(B)) unless an exception.")
    else:
        flags.append(f"{kva} kVA <= 112.5 -> 12 in from combustibles unless fire-rated barrier (450.21(A)).")

    # --- inrush --------------------------------------------------------------
    if not sec_ocpd:
        flags.append("Primary-only at 125%: high-efficiency/K-rated units can inrush 12-25x FLA and "
                     "nuisance-trip. Add a secondary OCPD to unlock 250% primary, or use a D-curve / "
                     "adjustable-instantaneous device set above 8-12x FLA.")
    if args.primary_basis in ("inrush", "max") and not args.primary_tap and sec_ocpd:
        flags.append(f"250% primary basis used: OCPD {op_amp}A drove the primary conductor up to {pri_cond} "
                     f"({pri_amp}A) so 240.4 is satisfied. On a radial feeder this only buys inrush margin - "
                     f"it does NOT save copper. If there is no inrush problem, use --primary-basis min.")

    # --- assemble structured result (single source of truth for the diagram) -
    def conn_label(conn, phase, volts, side):
        if conn:
            return conn
        if phase == 1:
            return "1Ø"
        # 3φ heuristics for typical commercial gear
        if side == "pri":
            return "Δ" if volts >= 277 else "Y"
        return "Y" if volts in (208, 480, 480.0, 208.0) else "Δ"

    pri_conn = conn_label(args.primary_conn, args.primary_phase, args.primary_v, "pri")
    sec_conn = conn_label(args.secondary_conn, args.secondary_phase, args.secondary_v, "sec")
    sec_v_label = ("208Y/120V" if args.secondary_v == 208 and args.secondary_phase == 3 else
                   "480Y/277V" if args.secondary_v == 480 and args.secondary_phase == 3 else
                   f"{args.secondary_v:g}V {sec_conn}")
    pri_v_label = f"{args.primary_v:g}V {pri_conn}"
    sds, sds_assumption, sds_flag = separately_derived(
        args.sds, pri_conn, sec_conn, args.primary_phase, args.secondary_phase)
    assumptions.append(sds_assumption)
    if sds_flag:
        flags.append(sds_flag)

    result = {
        "tag": args.tag, "source_tag": args.source_tag, "load_tag": args.load_tag,
        "kva": kva, "k_factor": kf,
        "primary": {"v_label": pri_v_label, "v": args.primary_v, "phase": args.primary_phase,
                    "conn": pri_conn, "fla": round(fla_p, 1),
                    "ocpd": op_amp, "ocpd_pct": op_pct, "ocpd_note": op_note,
                    "conductor": pri_cond, "conductor_amp": pri_amp,
                    "conductor_method": pri_method, "parallel": pri_parallel,
                    "material": args.conductor.upper(), "term": term, "tap": args.primary_tap},
        "secondary": {"v_label": sec_v_label, "v": args.secondary_v, "phase": args.secondary_phase,
                      "conn": sec_conn, "fla": round(fla_s, 1),
                      "ocpd": os_amp, "ocpd_note": os_note,
                      "conductor": sec_cond, "conductor_amp": sec_amp,
                      "conductor_basis": sec_basis, "parallel": sec_parallel,
                      "material": args.conductor.upper(), "term": term,
                      "panel_bus": args.panel_bus, "tap_rule": tap_name,
                      "cont_load": round(cont_sec_amps, 1) if cont_sec_amps is not None else None},
        "grounding": {"sbj": sbj if sds else None, "gec": gec if sds else None, "sds": sds},
        "install": (">112.5 kVA: 1-hr fire-rated room (450.21(B))" if kva > 112.5
                    else "<=112.5 kVA: 12 in from combustibles (450.21(A))"),
        "assumptions": assumptions, "flags": flags,
    }

    if args.format == "json":
        import json
        print(json.dumps(result, indent=2))
        return

    # --- print report --------------------------------------------------------
    print("=" * 66)
    print("TRANSFORMER SIZING REPORT (NEC 2023)")
    print("=" * 66)
    print(f"Rating:            {kva} kVA, {args.primary_phase}\u03c6 pri / {args.secondary_phase}\u03c6 sec")
    print(f"Voltage:           {args.primary_v:g}V -> {args.secondary_v:g}V")
    if kf:
        print(f"K-factor:          {kf}  ({kf_note})")
    print("-" * 66)
    print(f"Primary FLA:       {fla_p:.1f} A")
    print(f"Secondary FLA:     {fla_s:.1f} A")
    if cont_sec_amps is not None:
        print(f"Continuous load:   {cont_sec_amps:.1f} A (secondary)")
    print("-" * 66)
    op_disp = f"{op_amp} A" if op_amp is not None else "see flag"
    print(f"Primary OCPD:      {op_disp}   [{op_pct}% basis] {op_note}")
    if sec_ocpd:
        print(f"Secondary OCPD:    {os_amp} A   {os_note}")
    else:
        print("Secondary OCPD:    none (primary-only)")
    print("-" * 66)
    print(f"Primary feeder:    {pri_cond} {args.conductor.upper()} ({term}C amp {pri_amp}A)")
    print(f"                   basis: {pri_method}; conductor >=125% FLA ({pri_base_amp:.1f}A)")
    print(f"Secondary cond.:   {sec_cond} {args.conductor.upper()} ({term}C amp {sec_amp}A)")
    print(f"                   basis: {sec_basis}")
    if tap_name != "n/a":
        print(f"Tap rule:          {tap_name}")
        print(f"                   {tap_note}")
    print("-" * 66)
    if sds:
        print("GROUNDING (separately derived system, 250.30):")
        print(f"  System bonding jumper:   {sbj}  (Table 250.102(C)(1))")
        print(f"  Grounding electrode cond:{gec}  (Table 250.66)")
        print("  Bond N-G at ONE point (transformer OR secondary disconnect, not both)")
    else:
        print("GROUNDING (NOT separately derived -- 250.30 does NOT apply):")
        print("  No SBJ and no GEC at the transformer; the secondary neutral stays bonded")
        print("  to the supply system. Run an EGC with the secondary conductors (250.122).")
    print("=" * 66)
    print("ASSUMPTIONS:")
    for a in assumptions:
        print(f"  - {a}")
    print("FLAGS / VERIFY:")
    for f in flags:
        print(f"  ! {f}")
    print("=" * 66)
    print("NOTE: conductor sizes are FIRST-PASS. Verify against Table 310.16 with")
    print("ambient/CCC derating (310.15) and the actual termination temp before issue.")


if __name__ == "__main__":
    main()
