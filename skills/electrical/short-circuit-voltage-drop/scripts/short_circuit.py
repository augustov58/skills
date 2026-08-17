#!/usr/bin/env python3
"""
short_circuit.py - Deterministic point-to-point short-circuit calculator.

Single source of truth for the numbers in the short-circuit-voltage-drop skill.
Implements the Bussmann/Eaton SPD (2014) "Basic Point-to-Point Calculation
Procedure" exactly as printed, so every intermediate matches the handbook's own
worked examples (see scripts/verify_spd.py).

Encodes:
  * Step 1-3  Transformer FLA, multiplier 100/%Z, let-through I_s.c. at the
    secondary terminals, with the Note 2 impedance-tolerance factor (0.9 for the
    high-end worst case, 1.1 for the low end) and the Note 3 utility-voltage
    factor.  Both are OFF by default except the 0.9, which is what the handbook
    uses in every printed example and what an interrupting-rating check needs.
  * Step 4-6  The "f" factor and multiplier M = 1/(1+f) carried point to point
    down the system, with separate 3-phase / 1-phase L-L / 1-phase L-N forms.
    The 1-phase forms use 2 x L (current flows out and back) where the 3-phase
    form uses 1.732 x L.
  * Step 6A  Motor contribution, 4 x total motor FLA, added at every fault
    location -- NOT attenuated by the conductor run, because the motors are
    downstream of it.
  * Steps A-C  Fault at the secondary of a downstream transformer when the
    available fault at its PRIMARY is known.
  * Note 5    At a 1-phase center-tapped transformer's terminals the L-N bolted
    fault is 1.5 x the L-L fault, so L-N is the governing case there.
  * SPD Table 3  Other fault types as a percent of the 3-phase bolted value.

It prints a structured report plus ASSUMPTIONS and FLAGS / VERIFY blocks so the
calling agent can read them back.  Hand-calculation is discouraged: the "f"
factor compounds down the cascade and a single wrong C value moves every
downstream number.

USAGE
  # one conductor run from a transformer secondary
  python3 short_circuit.py --kva 1500 --percent-z 3.5 --secondary-v 480 \
      --length-ft 25 --size 500 --conductor cu --per-phase 6 --motor-fla 1804.3

  # a multi-point cascade (X1, X2, X3 ...) from a JSON one-line description
  python3 short_circuit.py --system system.json
  python3 short_circuit.py --example        # writes example_system.json and runs it

  # from a known available fault instead of a transformer
  #   --available-fault 45000 --secondary-v 480
  # 1-phase center-tapped:
  #   --phase 1 --secondary-v 240 --fault-type ln
  # low-end worst case (minimum fault, for a series-rating or GF study):
  #   --z-tolerance low --utility low

All flags: --help
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spd_tables as T

CALC_VERSION = "1.0.0-spd-2014-point-to-point (2026-08-16)"

# The SPD procedure prints 1.732, not sqrt(3), and carries that value through
# every worked example. Using math.sqrt(3) shifts results by about 0.03% and
# stops the output from matching the printed handbook, so the handbook constant
# is used deliberately.
SQRT3_SPD = 1.732


# ---- helpers ------------------------------------------------------------------

def transformer_fla(kva, voltage, phase):
    """SPD Step 1 -- transformer full-load amps at the stated voltage."""
    if phase == 3:
        return kva * 1000.0 / (voltage * SQRT3_SPD)
    return kva * 1000.0 / voltage


def f_factor(current, length_ft, c, per_phase, voltage, phase, fault_type):
    """SPD Step 4 -- the "f" factor for one conductor run.

    3-phase uses 1.732 x L; both 1-phase forms use 2 x L because the fault
    current traverses the run twice (out on one conductor, back on the other).
    `voltage` is the voltage of the fault loop: L-L for 3-phase and 1-phase L-L,
    L-N for a 1-phase line-to-neutral fault.
    """
    if fault_type == "3phase":
        numerator = SQRT3_SPD * length_ft * current
    else:
        numerator = 2.0 * length_ft * current
    return numerator / (c * per_phase * voltage)


def multiplier_m(f):
    """SPD Step 5 -- M = 1/(1+f)."""
    return 1.0 / (1.0 + f)


def xfmr_f_factor(i_primary, v_primary, percent_z_adj, kva, phase):
    """SPD Step A -- "f" through a transformer whose primary fault is known.

    3-phase carries the 1.732; 1-phase does not. The printed formula shows 1.73
    but every worked example carries 1.732, so 1.732 is used.
    """
    if phase == 3:
        return (i_primary * v_primary * SQRT3_SPD * percent_z_adj) / (100000.0 * kva)
    return (i_primary * v_primary * percent_z_adj) / (100000.0 * kva)


def fault_loop_voltage(secondary_v, phase, fault_type):
    """Voltage that belongs in the f-factor denominator for this fault type."""
    if fault_type == "ln":
        # A 120/240 center-tapped secondary is entered as 240; the L-N loop is
        # half that. A voltage already entered as L-N is passed through.
        return secondary_v / 2.0 if secondary_v >= 200 else secondary_v
    return secondary_v


# ---- the cascade engine -------------------------------------------------------

def run_system(system, assumptions, flags):
    """Walk the one-line from the source through each segment.

    Returns a list of fault-point dicts, one per node, X1 first.
    """
    src = system["source"]
    phase = int(src.get("phase", 3))
    fault_type = system.get("fault_type", "3phase")
    sec_v = float(src["secondary_voltage"])

    if fault_type == "3phase" and phase != 3:
        raise ValueError(
            "fault_type '3phase' needs a 3-phase source; got phase=%d. Use "
            "fault_type 'll' or 'ln' for a single-phase system." % phase
        )
    if fault_type in ("ll", "ln") and phase != 1:
        raise ValueError(
            "fault_type '%s' is the SPD single-phase procedure; got phase=%d. "
            "For a 3-phase wye system the SPD handbook gives no L-N method -- "
            "use the 3-phase bolted value and SPD Table 3 (25-125%%), which this "
            "script prints under OTHER FAULT TYPES." % (fault_type, phase)
        )

    loop_v = fault_loop_voltage(sec_v, phase, fault_type)
    z_tol = src.get("z_tolerance", "high")
    util = src.get("utility_voltage", "nominal")
    z_factor = T.Z_TOLERANCE[z_tol]
    util_factor = T.UTILITY_VOLTAGE[util]

    points = []

    # ---- X1: the source terminals (SPD Steps 1-3, or a given available fault) --
    if src["type"] == "transformer":
        kva = float(src["kva"])
        pct_z = float(src["percent_z"])
        fla = transformer_fla(kva, sec_v, phase)
        mult = 100.0 / (pct_z * z_factor)
        i_x1 = fla * mult * util_factor
        basis = ("%.1f kVA / %.0fV %dph: FLA %.1f A x (100 / %.3f%%Z) "
                 % (kva, sec_v, phase, fla, pct_z * z_factor))
        if fault_type == "ln":
            i_x1 = i_x1 * T.LN_TERMINAL_FAULT_MULT
            basis += "x 1.5 (Note 5, L-N at center-tapped terminals)"
            assumptions.append(
                "L-N fault at the transformer terminals taken as 1.5 x the L-L "
                "fault (SPD Note 5). This applies to a 1-phase CENTER-TAPPED "
                "transformer only."
            )
        points.append({
            "tag": src.get("tag", "X1"),
            "kind": "source",
            "fla": round(fla, 1),
            "multiplier": round(mult, 3),
            "isc": round(i_x1, 0),
            "basis": basis.strip(),
            "voltage": sec_v,
            "motor_applies": True,
        })
    elif src["type"] == "known_fault":
        i_x1 = float(src["available_fault"])
        fla = None
        points.append({
            "tag": src.get("tag", "X1"),
            "kind": "source",
            "fla": None,
            "multiplier": None,
            "isc": round(i_x1, 0),
            "basis": "given available fault current at %.0fV" % sec_v,
            "voltage": sec_v,
            "motor_applies": True,
        })
        assumptions.append(
            "Source fault current taken as given (%.0f A at %.0fV). The utility "
            "letter governs; %%Z tolerance and utility-voltage factors are NOT "
            "applied on top of a stated available fault."
            % (i_x1, sec_v)
        )
    else:
        raise ValueError("source.type must be 'transformer' or 'known_fault'")

    if src["type"] == "transformer":
        if z_tol == "high":
            assumptions.append(
                "Transformer %Z reduced 10% (x0.9) for the HIGH-end worst case "
                "(SPD Note 2, UL 1561 +/-10% tolerance on 25 kVA and larger). "
                "This is the value to check interrupting ratings against. Use "
                "--z-tolerance low for the minimum-fault case."
            )
        elif z_tol == "low":
            assumptions.append(
                "Transformer %Z raised 10% (x1.1) for the LOW-end worst case "
                "(SPD Note 2). Use this for ground-fault pickup and series "
                "ratings, NOT for interrupting ratings."
            )
        else:
            assumptions.append(
                "Transformer %Z used at nameplate with no tolerance factor. SPD "
                "Note 2 expects x0.9 for the maximum-fault case; the number "
                "below is therefore NOT the worst case."
            )
        if util != "nominal":
            assumptions.append(
                "Utility voltage variation factor %.3f applied (SPD Note 3)."
                % util_factor
            )

    # ---- motor contribution (SPD Step 6A) -------------------------------------
    motor = system.get("motor_contribution") or {}
    motor_fla = motor.get("motor_fla")
    if motor_fla is None and motor.get("fraction_of_source_fla") is not None:
        if fla is None:
            raise ValueError(
                "motor_contribution.fraction_of_source_fla needs a transformer "
                "source to compute FLA from; give motor_fla directly instead"
            )
        motor_fla = fla * float(motor["fraction_of_source_fla"])
    motor_mult = float(motor.get("multiplier", T.MOTOR_CONTRIBUTION_MULT))
    i_motor = (float(motor_fla) * motor_mult) if motor_fla else 0.0
    if i_motor:
        assumptions.append(
            "Motor contribution %.0f A = %.1f A motor FLA x %.0f (SPD Step 6A). "
            "It is added at EVERY fault point undiminished, because the motors "
            "sit downstream of the conductor runs."
            % (i_motor, float(motor_fla), motor_mult)
        )
        if motor_mult < 4:
            flags.append(
                "Motor multiplier %.1f is below the 4-6 range SPD Step 6A calls "
                "commonly accepted. Confirm the source of that figure." % motor_mult
            )

    # ---- downstream segments (Steps 4-6, or Steps A-C at a transformer) -------
    current = i_x1
    crossed_transformer = False   # upstream motors do not contribute past one
    for seg in system.get("segments", []):
        kind = seg.get("type", "conductor")

        if kind == "transformer":
            kva = float(seg["kva"])
            pct_z = float(seg["percent_z"])
            seg_phase = int(seg.get("phase", phase))
            v_pri = float(seg["primary_voltage"])
            v_sec = float(seg["secondary_voltage"])
            seg_z_factor = T.Z_TOLERANCE[seg.get("z_tolerance", z_tol)]
            pct_z_adj = pct_z * seg_z_factor
            f = xfmr_f_factor(current, v_pri, pct_z_adj, kva, seg_phase)
            m = multiplier_m(f)
            new_current = (v_pri / v_sec) * m * current
            points.append({
                "tag": seg.get("tag", "X%d" % (len(points) + 1)),
                "kind": "transformer",
                "f": round(f, 4),
                "m": round(m, 4),
                "isc": round(new_current, 0),
                "basis": ("%.1f kVA %.0f/%.0fV, %.3f%%Z adj -- SPD Steps A-C "
                          "through the transformer" % (kva, v_pri, v_sec, pct_z_adj)),
                "voltage": v_sec,
                "motor_applies": False,
            })
            crossed_transformer = True
            if i_motor:
                flags.append(
                    "Motor contribution from the UPSTREAM system STOPS at "
                    "transformer %s -- it is a different voltage, so it is NOT "
                    "added at %s or anything downstream of it. Motors on the "
                    "%.0fV secondary must be counted in a separate run."
                    % (seg.get("tag", "?"), seg.get("tag", "?"), v_sec)
                )
            current = new_current
            loop_v = fault_loop_voltage(v_sec, seg_phase, fault_type)
            continue

        if kind == "busway":
            c = T.busway_c(seg["ampacity"], seg.get("conductor", "cu"),
                           seg.get("busway_type", "feeder"))
            per_phase = 1
            label = "%s A %s busway, %s" % (
                seg["ampacity"], seg.get("busway_type", "feeder"),
                seg.get("conductor", "cu").upper())
            if int(seg["ampacity"]) >= 3000:
                flags.append(
                    "Busway at %s A is at the top of SPD Table 5, which is a "
                    "survey average across manufacturers. At this rating confirm "
                    "the C value against the actual busway submittal."
                    % seg["ampacity"]
                )
        else:
            c = T.c_value(seg.get("conductor", "cu"), seg["size"],
                          seg.get("conduit", "steel"),
                          seg.get("arrangement", "single"),
                          seg.get("voltage_class", "600"))
            per_phase = int(seg.get("per_phase", 1))
            label = "%s %s, %d per phase, %s conduit, %s" % (
                seg.get("conductor", "cu").upper(),
                T.normalize_size(seg["size"]), per_phase,
                seg.get("conduit", "steel"), seg.get("arrangement", "single"))

        length = float(seg["length_ft"])
        f = f_factor(current, length, c, per_phase, loop_v, phase, fault_type)
        m = multiplier_m(f)
        new_current = current * m
        points.append({
            "tag": seg.get("tag", "X%d" % (len(points) + 1)),
            "kind": "conductor",
            "f": round(f, 4),
            "m": round(m, 4),
            "isc": round(new_current, 0),
            "c_value": c,
            "motor_applies": not crossed_transformer,
            "basis": "%.0f ft, %s, C=%d" % (length, label, c),
            "voltage": loop_v if fault_type != "ln" else loop_v * 2,
        })
        if length > 500:
            flags.append(
                "Segment %s is %.0f ft. Long runs make the point-to-point result "
                "sensitive to the actual routed length -- confirm it against the "
                "as-built, not the plan dimension."
                % (seg.get("tag", "?"), length)
            )
        current = new_current

    # Attach motor contribution and totals. The contribution applies only on the
    # motors' own voltage level -- past a transformer it is a different system and
    # adding it there overstates the fault.
    for pt in points:
        applies = i_motor if pt.get("motor_applies", True) else 0.0
        pt["motor_contribution"] = round(applies, 0)
        pt["isc_total"] = round(pt["isc"] + applies, 0)

    return points, i_motor


# ---- example ------------------------------------------------------------------

EXAMPLE = {
    "project": "Example one-line -- service to a 208V branch panel",
    "fault_type": "3phase",
    "source": {
        "type": "transformer",
        "tag": "X1 service",
        "kva": 1500,
        "phase": 3,
        "secondary_voltage": 480,
        "percent_z": 3.5,
        "z_tolerance": "high",
        "utility_voltage": "nominal"
    },
    "motor_contribution": {"fraction_of_source_fla": 0.5, "multiplier": 4},
    "segments": [
        {
            "tag": "X2 MDP",
            "type": "conductor",
            "length_ft": 25,
            "size": "500",
            "conductor": "cu",
            "per_phase": 6,
            "conduit": "steel",
            "arrangement": "single",
            "voltage_class": "600"
        },
        {
            "tag": "X3 MCC-1",
            "type": "conductor",
            "length_ft": 120,
            "size": "4/0",
            "conductor": "al",
            "per_phase": 2,
            "conduit": "nonmagnetic",
            "arrangement": "cable",
            "voltage_class": "600"
        },
        {
            "tag": "X4 busway tap",
            "type": "busway",
            "length_ft": 80,
            "ampacity": 1000,
            "busway_type": "feeder",
            "conductor": "cu"
        },
        {
            "tag": "X5 panel LP-1",
            "type": "transformer",
            "kva": 75,
            "phase": 3,
            "primary_voltage": 480,
            "secondary_voltage": 208,
            "percent_z": 2.4,
            "z_tolerance": "high"
        }
    ]
}


# ---- main ---------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="SPD 2014 point-to-point short-circuit calculator")
    p.add_argument("--version", action="version",
                   version="%(prog)s " + CALC_VERSION)

    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--kva", type=float,
                   help="source transformer kVA (needs --percent-z)")
    g.add_argument("--available-fault", type=float,
                   help="known available fault current (A) at the source, per the "
                        "utility letter or an upstream study")
    g.add_argument("--system", metavar="FILE",
                   help="JSON one-line description for a multi-point cascade; "
                        "schema = the EXAMPLE block in this script")
    g.add_argument("--example", action="store_true",
                   help="write example_system.json into the CWD and run it")

    p.add_argument("--percent-z", type=float, default=None,
                   help="transformer nameplate %%Z. Omit to look up SPD Table 1 by "
                        "kVA and voltage (less accurate -- prefer the nameplate)")
    p.add_argument("--secondary-v", type=float, default=None,
                   help="source voltage, L-L (480, 240, 208...)")
    p.add_argument("--phase", type=int, choices=[1, 3], default=3)
    p.add_argument("--fault-type", choices=["3phase", "ll", "ln"], default=None,
                   help="3phase (default on a 3-phase source); ll or ln for the "
                        "SPD single-phase center-tapped procedure")
    p.add_argument("--z-tolerance", choices=["high", "nameplate", "low"],
                   default="high",
                   help="high = %%Z x0.9, the MAXIMUM fault (SPD Note 2) and what "
                        "interrupting ratings are checked against. low = %%Z x1.1 "
                        "for the minimum fault. Default high.")
    p.add_argument("--utility", choices=["nominal", "high", "low", "high_120v",
                                         "low_120v"],
                   default="nominal",
                   help="utility voltage variation factor (SPD Note 3). Default "
                        "nominal = no adjustment.")

    p.add_argument("--length-ft", type=float, default=None,
                   help="conductor run length from the source to the fault point")
    p.add_argument("--size", default=None,
                   help="conductor size (14 ... 1000; 1/0 or 0 both accepted)")
    p.add_argument("--conductor", choices=["cu", "al"], default="cu")
    p.add_argument("--per-phase", type=int, default=1,
                   help="conductors per phase (parallel sets). Multiplies C.")
    p.add_argument("--conduit", choices=["steel", "nonmagnetic"], default="steel",
                   help="steel = magnetic (EMT/RMC/IMC); nonmagnetic = PVC, "
                        "aluminum, fibre")
    p.add_argument("--arrangement", choices=["single", "cable"], default="single",
                   help="single = three single conductors in a raceway; cable = "
                        "three-conductor cable (SPD Table 4 columns)")
    p.add_argument("--voltage-class", choices=["600", "5k", "15k"], default="600")

    p.add_argument("--motor-fla", type=float, default=None,
                   help="total connected motor FLA downstream, for the SPD Step 6A "
                        "contribution")
    p.add_argument("--motor-fraction", type=float, default=None,
                   help="motor load as a fraction of source FLA, if the motor "
                        "total is not known (1.0 = the SPD example's 100%% motor "
                        "load assumption)")
    p.add_argument("--motor-mult", type=float, default=T.MOTOR_CONTRIBUTION_MULT,
                   help="motor contribution multiplier, 4 to 6 (default 4)")

    p.add_argument("--device-air", type=float, default=None,
                   help="interrupting rating (A) of the device at the LAST fault "
                        "point, to check against 110.9")
    p.add_argument("--format", choices=["report", "json"], default="report")
    args = p.parse_args()

    assumptions, flags = [], []

    # ---- build the system dict from whichever entry path was used -------------
    if args.example:
        with open("example_system.json", "w") as fh:
            json.dump(EXAMPLE, fh, indent=2)
        system = EXAMPLE
        print("Wrote example_system.json\n")
    elif args.system:
        with open(args.system) as fh:
            system = json.load(fh)
    else:
        if args.secondary_v is None:
            p.error("--secondary-v is required unless --system or --example is used")
        fault_type = args.fault_type or ("3phase" if args.phase == 3 else "ll")
        if args.kva is not None:
            pct_z = args.percent_z
            if pct_z is None:
                pct_z = lookup_percent_z(args.kva, args.secondary_v, args.phase,
                                         assumptions, flags)
            source = {"type": "transformer", "tag": "X1", "kva": args.kva,
                      "phase": args.phase, "secondary_voltage": args.secondary_v,
                      "percent_z": pct_z, "z_tolerance": args.z_tolerance,
                      "utility_voltage": args.utility}
        else:
            source = {"type": "known_fault", "tag": "X1",
                      "available_fault": args.available_fault,
                      "phase": args.phase, "secondary_voltage": args.secondary_v}
        segments = []
        if args.length_ft is not None:
            if args.size is None:
                p.error("--size is required when --length-ft is given")
            segments.append({"tag": "X2", "type": "conductor",
                             "length_ft": args.length_ft, "size": args.size,
                             "conductor": args.conductor,
                             "per_phase": args.per_phase, "conduit": args.conduit,
                             "arrangement": args.arrangement,
                             "voltage_class": args.voltage_class})
        elif args.size is not None:
            p.error("--length-ft is required when --size is given")
        motor = {}
        if args.motor_fla is not None:
            motor["motor_fla"] = args.motor_fla
        elif args.motor_fraction is not None:
            motor["fraction_of_source_fla"] = args.motor_fraction
        if motor:
            motor["multiplier"] = args.motor_mult
        system = {"fault_type": fault_type, "source": source,
                  "segments": segments, "motor_contribution": motor}

    # A bad table lookup or an unsupported fault type is a user error, not a
    # crash. Print the reason, which always names the fix, and exit non-zero.
    try:
        points, i_motor = run_system(system, assumptions, flags)
    except (ValueError, KeyError) as exc:
        sys.stderr.write("ERROR: %s\n" % exc)
        sys.exit(2)

    # ---- 110.9 check at the last point ---------------------------------------
    last = points[-1]
    if args.device_air is not None:
        if args.device_air < last["isc_total"]:
            flags.append(
                "110.9 VIOLATION: device interrupting rating %.0f A is BELOW the "
                "%.0f A available at %s. The device must be rated at or above the "
                "available fault current, or be part of a listed series "
                "combination (240.86)."
                % (args.device_air, last["isc_total"], last["tag"])
            )
        else:
            assumptions.append(
                "Device interrupting rating %.0f A >= %.0f A available at %s "
                "(110.9 satisfied at that point)."
                % (args.device_air, last["isc_total"], last["tag"])
            )

    # ---- standing flags -------------------------------------------------------
    fault_type = system.get("fault_type", "3phase")
    if fault_type == "3phase":
        flags.append(
            "3-phase BOLTED fault only. Arcing faults are lower (SPD Table 3: 89% "
            "of bolted, 74% L-L) and are the values an incident-energy study "
            "needs -- this script is not an arc-flash calculation (110.16 / "
            "IEEE 1584)."
        )
    flags.append(
        "Conductor impedance only. Cable terminations, bus stabs, CT windings and "
        "the transformer's own X/R split are not modeled, so the result is "
        "slightly HIGH -- conservative for interrupting ratings, optimistic for a "
        "minimum-fault ground-fault study."
    )
    flags.append(
        "110.24 requires the available fault current and the calculation date to "
        "be field-marked at service equipment, and re-verified when the supply "
        "changes. Record which transformer %Z and utility figure this run used."
    )

    result = {
        "project": system.get("project"),
        "fault_type": fault_type,
        "source": system["source"],
        "motor_contribution_a": round(i_motor, 0),
        "points": points,
        "other_fault_types_at_last_point": other_fault_types(last["isc_total"])
        if fault_type == "3phase" else None,
        "assumptions": assumptions,
        "flags": flags,
    }

    if args.format == "json":
        print(json.dumps(result, indent=2))
        return

    # ---- print report ---------------------------------------------------------
    print("=" * 66)
    print("SHORT-CIRCUIT REPORT (SPD 2014 point-to-point)")
    print("=" * 66)
    if system.get("project"):
        print("Project:           %s" % system["project"])
    print("Fault type:        %s" % {"3phase": "three-phase bolted",
                                     "ll": "1-phase line-to-line",
                                     "ln": "1-phase line-to-neutral"}[fault_type])
    print("-" * 66)
    for pt in points:
        print("%-18s %s A symmetrical RMS" % (pt["tag"] + ":", fmt_a(pt["isc"])))
        print("                   %s" % pt["basis"])
        if pt.get("f") is not None:
            print("                   f = %.4f  ->  M = 1/(1+f) = %.4f"
                  % (pt["f"], pt["m"]))
        if pt["motor_contribution"]:
            print("                   + %s A motor  =  %s A TOTAL"
                  % (fmt_a(pt["motor_contribution"]), fmt_a(pt["isc_total"])))
    print("-" * 66)
    print("Governing value:   %s A at %s (use for interrupting ratings, 110.9)"
          % (fmt_a(points[0]["isc_total"]), points[0]["tag"]))
    if fault_type == "3phase":
        print("-" * 66)
        print("OTHER FAULT TYPES at %s (SPD Table 3, %% of 3-phase bolted):"
              % last["tag"])
        for name, (lo, hi, note) in T.FAULT_TYPE_PERCENT.items():
            if name == "three_phase_bolted":
                continue
            label = name.replace("_", " ")
            if lo == hi:
                print("  %-26s %s A   (%s)"
                      % (label, fmt_a(last["isc_total"] * lo / 100.0), note))
            else:
                print("  %-26s %s - %s A   (%s)"
                      % (label, fmt_a(last["isc_total"] * lo / 100.0),
                         fmt_a(last["isc_total"] * hi / 100.0), note))
    print("=" * 66)
    print("ASSUMPTIONS:")
    for a in assumptions:
        print("  - %s" % a)
    print("FLAGS / VERIFY:")
    for f in flags:
        print("  ! %s" % f)
    if not flags:
        print("  (none -- every check in this script passed)")
    print("=" * 66)
    print("NOTE: point-to-point is a first-pass method. A study that must be")
    print("stamped, or any system with generators, large motor plants, or")
    print("network transformers, needs a per-unit or symmetrical-components")
    print("calculation (IEEE 141/242) -- not this.")


def lookup_percent_z(kva, voltage, phase, assumptions, flags):
    """SPD Table 1 %Z fallback when no nameplate is available."""
    label = None
    for (v_label, ph) in T.TRANSFORMER_Z:
        if ph != phase:
            continue
        if phase == 1 and abs(voltage - 240) < 1:
            label = v_label
        elif phase == 3 and abs(voltage - 208) < 1 and v_label == "120/208":
            label = v_label
        elif phase == 3 and abs(voltage - 480) < 1 and v_label == "277/480":
            label = v_label
    if label is None:
        raise ValueError(
            "no SPD Table 1 row for %.0fV %d-phase -- pass --percent-z from the "
            "nameplate" % (voltage, phase)
        )
    table = T.TRANSFORMER_Z[(label, phase)]
    if kva not in table:
        near = min(table, key=lambda k: abs(k - kva))
        flags.append(
            "%.1f kVA is not a row in SPD Table 1; used the %s kVA row (%.2f%%Z). "
            "Get the nameplate %%Z -- Table 1 spans 1.0%% to 4.0%% and the fault "
            "current is inversely proportional to it."
            % (kva, near, table[near][1])
        )
        kva = near
    pct_z = table[kva][1]
    assumptions.append(
        "%%Z taken from SPD Table 1 (%s, %s kVA) = %.2f%%, NOT a nameplate. UL "
        "1561 allows +/-10%% on the nameplate itself, so this is a planning "
        "number -- replace it before issuing." % (label, kva, pct_z)
    )
    return pct_z


def other_fault_types(i_3phase):
    """SPD Table 3 -- other fault types as a percent of the 3-phase bolted value."""
    out = {}
    for name, (lo, hi, note) in T.FAULT_TYPE_PERCENT.items():
        out[name] = {"low_a": round(i_3phase * lo / 100.0, 0),
                     "high_a": round(i_3phase * hi / 100.0, 0),
                     "note": note}
    return out


def fmt_a(amps):
    """Amperes with a thousands separator, no decimals -- the SPD display style."""
    return "{:,.0f}".format(amps)


if __name__ == "__main__":
    main()
