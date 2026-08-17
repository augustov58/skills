#!/usr/bin/env python3
"""
verify_spd.py - Regression check against the printed SPD 2014 worked examples.

The tables in spd_tables.py are ~1,400 hand-transcribed numbers. A single wrong
"C" value or volt-loss figure produces an answer that looks entirely plausible,
so the only real defense is reproducing the handbook's own published results.

Every case below is a number PRINTED in the SPD handbook, not a number this
project computed. Cases cover:
  * System A, 3-phase, faults X1 / X2 / X3            (SPD p.238)
  * System B, 3-phase, faults X1 / X2 / X3            (SPD p.238)
  * System B, fault X4 through a downstream transformer with a known primary
    fault -- SPD Steps A-C                            (SPD p.238)
  * System A, 1-phase center-tapped, L-L at X1/X2/X3  (SPD p.240)
  * System A, 1-phase center-tapped, L-N at X1/X2/X3  (SPD p.240)
  * Volt loss, 6 AWG Cu, 180 ft, 40 A, 80% PF         (SPD p.243)
  * Wire selection for a 5.5 V permissible loss       (SPD p.243)

Tolerances are per-case because the handbook rounds intermediate values before
printing them. Anything above 0.5% of the printed value is a real disagreement,
not rounding.

USAGE
  python3 verify_spd.py            # run every case, exit 1 on any failure
  python3 verify_spd.py --verbose  # also show the passing cases' arithmetic
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spd_tables as T
import short_circuit as SC
import voltage_drop as VD

# (name, printed_value, computed_value_fn, tolerance_percent)
# Tolerance is a percentage of the printed value.
DEFAULT_TOL = 0.5


def sc_case(system):
    """Run a system dict through the engine and return {tag: total amps}."""
    points, _motor = SC.run_system(system, [], [])
    return {p["tag"]: p for p in points}


def system_a_3ph():
    return {
        "fault_type": "3phase",
        "source": {"type": "transformer", "tag": "X1", "kva": 1500, "phase": 3,
                   "secondary_voltage": 480, "percent_z": 3.5,
                   "z_tolerance": "high", "utility_voltage": "nominal"},
        "motor_contribution": {"fraction_of_source_fla": 1.0, "multiplier": 4},
        "segments": [
            {"tag": "X2", "length_ft": 25, "size": "500", "conductor": "cu",
             "per_phase": 6, "conduit": "steel", "arrangement": "single"},
            {"tag": "X3", "length_ft": 50, "size": "500", "conductor": "cu",
             "per_phase": 1, "conduit": "steel", "arrangement": "single"},
        ],
    }


def system_b_3ph():
    return {
        "fault_type": "3phase",
        "source": {"type": "transformer", "tag": "X1", "kva": 1000, "phase": 3,
                   "secondary_voltage": 480, "percent_z": 3.5,
                   "z_tolerance": "high", "utility_voltage": "nominal"},
        "segments": [
            {"tag": "X2", "length_ft": 30, "size": "500", "conductor": "cu",
             "per_phase": 4, "conduit": "nonmagnetic", "arrangement": "single"},
            {"tag": "X3", "length_ft": 20, "size": "2/0", "conductor": "cu",
             "per_phase": 2, "conduit": "nonmagnetic", "arrangement": "single"},
            {"tag": "X4", "type": "transformer", "kva": 225, "phase": 3,
             "primary_voltage": 480, "secondary_voltage": 208, "percent_z": 1.2,
             "z_tolerance": "high"},
        ],
    }


def system_a_1ph(fault_type):
    return {
        "fault_type": fault_type,
        "source": {"type": "transformer", "tag": "X1", "kva": 75, "phase": 1,
                   "secondary_voltage": 240, "percent_z": 1.4,
                   "z_tolerance": "high", "utility_voltage": "nominal"},
        "segments": [
            {"tag": "X2", "length_ft": 25, "size": "500", "conductor": "cu",
             "per_phase": 1, "conduit": "steel", "arrangement": "single"},
            {"tag": "X3", "length_ft": 50, "size": "3", "conductor": "cu",
             "per_phase": 1, "conduit": "steel", "arrangement": "single"},
        ],
    }


def build_cases():
    cases = []

    a = sc_case(system_a_3ph())
    cases.append(("System A p.238  X1 I_s.c.", 57279, a["X1"]["isc"], DEFAULT_TOL))
    cases.append(("System A p.238  X1 motor contribution", 7217,
                  a["X1"]["motor_contribution"], DEFAULT_TOL))
    cases.append(("System A p.238  X1 total", 64496, a["X1"]["isc_total"],
                  DEFAULT_TOL))
    cases.append(("System A p.238  X2 f", 0.0388, a["X2"]["f"], 1.0))
    cases.append(("System A p.238  X2 M", 0.9626, a["X2"]["m"], DEFAULT_TOL))
    cases.append(("System A p.238  X2 I_s.c.", 55137, a["X2"]["isc"], DEFAULT_TOL))
    cases.append(("System A p.238  X2 total", 62354, a["X2"]["isc_total"],
                  DEFAULT_TOL))
    cases.append(("System A p.238  X3 f", 0.4484, a["X3"]["f"], 1.0))
    cases.append(("System A p.238  X3 M", 0.6904, a["X3"]["m"], DEFAULT_TOL))
    cases.append(("System A p.238  X3 I_s.c.", 38067, a["X3"]["isc"], DEFAULT_TOL))
    cases.append(("System A p.238  X3 total", 45284, a["X3"]["isc_total"],
                  DEFAULT_TOL))

    b = sc_case(system_b_3ph())
    cases.append(("System B p.238  X1 I_s.c.", 38184, b["X1"]["isc"], DEFAULT_TOL))
    cases.append(("System B p.238  X2 f", 0.0387, b["X2"]["f"], 1.0))
    cases.append(("System B p.238  X2 I_s.c.", 36761, b["X2"]["isc"], DEFAULT_TOL))
    cases.append(("System B p.238  X3 f", 0.1161, b["X3"]["f"], 1.0))
    cases.append(("System B p.238  X3 I_s.c.", 32937, b["X3"]["isc"], DEFAULT_TOL))
    cases.append(("System B p.238  X4 f (Step A, thru xfmr)", 1.3144, b["X4"]["f"],
                  1.0))
    cases.append(("System B p.238  X4 M (Step B)", 0.4321, b["X4"]["m"],
                  DEFAULT_TOL))
    cases.append(("System B p.238  X4 I_s.c. (Step C)", 32842, b["X4"]["isc"],
                  DEFAULT_TOL))

    ll = sc_case(system_a_1ph("ll"))
    cases.append(("1-phase p.240  L-L X1", 24802, ll["X1"]["isc"], DEFAULT_TOL))
    cases.append(("1-phase p.240  L-L X2 f", 0.2329, ll["X2"]["f"], 1.0))
    cases.append(("1-phase p.240  L-L X2", 20116, ll["X2"]["isc"], DEFAULT_TOL))
    cases.append(("1-phase p.240  L-L X3 f", 1.7557, ll["X3"]["f"], 1.0))
    cases.append(("1-phase p.240  L-L X3", 7300, ll["X3"]["isc"], DEFAULT_TOL))

    ln = sc_case(system_a_1ph("ln"))
    cases.append(("1-phase p.240  L-N X1 (Note 5, 1.5x)", 37202, ln["X1"]["isc"],
                  DEFAULT_TOL))
    cases.append(("1-phase p.240  L-N X2 f", 0.6987, ln["X2"]["f"], 1.0))
    cases.append(("1-phase p.240  L-N X2", 21900, ln["X2"]["isc"], DEFAULT_TOL))
    cases.append(("1-phase p.240  L-N X3", 4540, ln["X3"]["isc"], DEFAULT_TOL))

    # ---- volt loss, SPD p.243 -------------------------------------------------
    # "6 AWG copper wire, one per phase, in 180 feet of steel conduit -- 3 phase,
    #  40 amp load at 80% power factor." Printed table figure 745, printed volt
    #  loss 5.364 V, printed 2.23% on 240V.
    fig = VD.volt_loss_figure("cu", "steel", "6", 3, 80, [])
    cases.append(("Volt loss p.243  Table A figure, 6 AWG Cu steel 3ph 80%", 745,
                  fig, 0.01))
    vl = VD.volt_loss(fig, 180, 40, 1)
    cases.append(("Volt loss p.243  volts lost", 5.364, vl, 0.01))
    cases.append(("Volt loss p.243  percent on 240V", 2.23, vl / 240 * 100, 0.5))

    # "How to Select Size of Wire": 180 ft, 40 A, permissible 5.5 V ->
    # 5.5 x 1,000,000 / 7200 = 764; nearest not above = 745 = 6 AWG.
    target = 5.5 * 1000000 / (180 * 40 * 1)
    cases.append(("Wire select p.243  figure ceiling", 764, target, 0.2))
    picked = None
    for size in T.SIZE_ORDER:
        if size not in T.VOLT_LOSS["cu"]["steel"]:
            continue
        f = VD.volt_loss_figure("cu", "steel", size, 3, 80, [])
        if f <= target:
            picked = size
            break
    cases.append(("Wire select p.243  chosen size (6 AWG)", 6,
                  float(picked) if picked and picked.isdigit() else -1, 0.01))

    # ---- a few raw table spot-checks against the printed page -----------------
    cases.append(("Table 4  Cu 500 kcmil single steel 600V C", 22185,
                  T.c_value("cu", "500", "steel", "single", "600"), 0.01))
    cases.append(("Table 4  Cu 2/0 single nonmagnetic 600V C", 11424,
                  T.c_value("cu", "2/0", "nonmagnetic", "single", "600"), 0.01))
    cases.append(("Table 4  Cu 3 AWG single steel 600V C", 4774,
                  T.c_value("cu", "3", "steel", "single", "600"), 0.01))
    cases.append(("Table 4  Al 4/0 cable nonmagnetic 15kV C", 10969,
                  T.c_value("al", "4/0", "nonmagnetic", "cable", "15k"), 0.01))
    cases.append(("Table 5  1000 A feeder busway Cu C", 62900,
                  T.busway_c(1000, "cu", "feeder"), 0.01))
    cases.append(("Table 1  1500 kVA 277/480 3ph %Z", 3.50,
                  T.TRANSFORMER_Z[("277/480", 3)][1500][1], 0.01))
    cases.append(("Table B  Al 250 kcmil steel 3ph 90% figure", 173,
                  VD.volt_loss_figure("al", "steel", "250", 3, 90, []), 0.01))

    return cases


def main():
    p = argparse.ArgumentParser(
        description="Regression check against the printed SPD 2014 examples")
    p.add_argument("--verbose", action="store_true",
                   help="show passing cases too, not just failures")
    args = p.parse_args()

    cases = build_cases()
    failures = []
    print("=" * 78)
    print("SPD 2014 REGRESSION CHECK -- computed vs PRINTED handbook values")
    print("=" * 78)
    for name, printed, computed, tol_pct in cases:
        delta = abs(computed - printed)
        limit = abs(printed) * tol_pct / 100.0
        ok = delta <= limit
        if not ok:
            failures.append(name)
        if args.verbose or not ok:
            print("%-4s %-52s printed %-12s computed %-12s (%.3f%% off)"
                  % ("PASS" if ok else "FAIL", name,
                     fmt(printed), fmt(computed),
                     100.0 * delta / abs(printed) if printed else 0.0))
    print("-" * 78)
    print("%d cases, %d passed, %d FAILED" %
          (len(cases), len(cases) - len(failures), len(failures)))
    if failures:
        print("=" * 78)
        print("A failure means spd_tables.py disagrees with the printed handbook.")
        print("Fix the table, not the tolerance.")
        sys.exit(1)
    print("=" * 78)


def fmt(v):
    if isinstance(v, float) and abs(v) < 100:
        return "%.4f" % v
    return "{:,.0f}".format(v)


if __name__ == "__main__":
    main()
