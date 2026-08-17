#!/usr/bin/env python3
"""
voltage_drop.py - Deterministic volt-loss calculator and wire-size selector.

Single source of truth for the voltage-drop numbers in the
short-circuit-voltage-drop skill. Implements the Bussmann/Eaton SPD (2014)
"Ratings of Conductors and Tables to Determine Volt Loss" method (Tables A and
B) exactly as printed, so the output matches the handbook's own worked examples
(see scripts/verify_spd.py).

Encodes:
  * The volt-loss formula:  volt loss = feet x amperes x table figure
    / 1,000,000 / conductors-per-phase.  The table figure already carries the
    conductor's AC resistance AND reactance at the stated power factor, which is
    why a steel raceway and a PVC raceway give different answers for the same
    wire -- the usual "2 x K x I x L / cmil" shortcut cannot show that.
  * Reverse selection ("How to Select Size of Wire"): smallest conductor whose
    figure is at or below permissible_volt_loss x 1,000,000 / (feet x amperes),
    then re-checked against ampacity so the answer satisfies BOTH constraints.
  * Ampacity from the same table row (NEC Table 310.16, 60/75/90C columns), with
    310.15(B)(1) ambient correction, 310.15(C)(1) conductor-count adjustment,
    110.14(C) termination-temperature limiting, and the 240.4(D) small-conductor
    OCPD cap.
  * Power factors between the tabulated 100/90/80/70/60% columns are linearly
    interpolated and the interpolation is stated in ASSUMPTIONS.

Voltage drop is NOT a mandatory NEC limit in general -- 210.19 and 215.2 carry it
as Informational Notes (3% branch / 5% total, advisory).  It IS mandatory for
sensitive electronic equipment (647.4(D): 1.5% branch, 2.5% total) and for fire
pumps (695.7).  The script defaults to the advisory 3% and says so.

It prints a structured report plus ASSUMPTIONS and FLAGS / VERIFY blocks so the
calling agent can read them back.

USAGE
  # drop on a known conductor
  python3 voltage_drop.py --amps 40 --length-ft 180 --voltage 240 --phase 3 \
      --size 6 --conductor cu --conduit steel --pf 0.8

  # pick the smallest conductor that holds 3% and still carries the load
  python3 voltage_drop.py --amps 40 --length-ft 180 --voltage 240 --phase 3 \
      --select --limit-percent 3

  # feeder + branch budget: charge 1.8% already spent upstream
  #   --upstream-percent 1.8 --limit-percent 5
  # derating:
  #   --ambient-c 45 --ccc 6 --term-temp 75

All flags: --help
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spd_tables as T

CALC_VERSION = "1.0.0-spd-2014-volt-loss (2026-08-16)"

PF_COLUMNS = (60, 70, 80, 90, 100)  # ascending, for interpolation


# ---- helpers ------------------------------------------------------------------

def volt_loss_figure(material, conduit, size, phase, pf_percent, assumptions):
    """SPD Table A/B figure for this conductor at this power factor.

    Interpolates linearly between the tabulated 100/90/80/70/60% columns. The
    figures are NOT monotonic in power factor -- for large conductors reactance
    dominates and the figure RISES as PF falls, while for small conductors
    resistance dominates and it falls. Interpolation handles both; picking the
    "nearest column" the way the printed instructions do would be off by up to
    10% of the figure.
    """
    row = T.VOLT_LOSS[material][conduit][size]
    col = row["three_phase"] if phase == 3 else row["single_phase"]
    if pf_percent in col:
        return float(col[pf_percent])
    lower = max(c for c in PF_COLUMNS if c <= pf_percent)
    upper = min(c for c in PF_COLUMNS if c >= pf_percent)
    span = upper - lower
    frac = (pf_percent - lower) / span
    figure = col[lower] + (col[upper] - col[lower]) * frac
    assumptions.append(
        "PF %.2f is between the tabulated %d%% and %d%% columns; the volt-loss "
        "figure was linearly interpolated to %.1f (SPD Tables A/B tabulate only "
        "100/90/80/70/60%%)." % (pf_percent / 100.0, lower, upper, figure)
    )
    return figure


def volt_loss(figure, length_ft, amps, per_phase):
    """SPD volt-loss formula. Returns volts lost, line-to-line."""
    return length_ft * amps * figure / 1000000.0 / per_phase


def line_to_neutral(volts_ll, phase):
    """SPD "Line-to-Neutral" note -- divide by 1.73 (3-phase) or 2 (1-phase).

    Reported for information only. On a BALANCED circuit the percent drop is
    identical either way, because the reference voltage divides by the same
    factor (VL_LL/V_LL == VL_LN/V_LN). Quoting the L-N volts against the L-L
    nominal voltage is the classic way to under-report a drop by half.
    """
    return volts_ll / (1.732 if phase == 3 else 2.0)


def ampacity_check(material, conduit, size, term_temp, ambient_c, ccc,
                   insulation_temp, assumptions, flags):
    """Return (allowed_amps, detail) after 310.15 derating and the 110.14(C) cap.

    Correction and adjustment are applied to the ampacity of the conductor's own
    INSULATION rating (90C for THHN/XHHW-2), then the result is limited by the
    termination temperature column. That is the 110.14(C) two-step; doing it in
    the other order throws away the 90C headroom the code allows for derating
    and under-sizes the conductor.
    """
    amps60, amps75, amps90 = T.VOLT_LOSS[material][conduit][size]["ampacity"]
    by_temp = {60: amps60, 75: amps75, 90: amps90}
    base = by_temp[insulation_temp]
    a_factor = T.ambient_factor(ambient_c, insulation_temp)
    c_factor = T.ccc_factor(ccc)
    derated = base * a_factor * c_factor
    term_cap = by_temp[term_temp]
    allowed = min(derated, term_cap)
    detail = ("%dC base %d A x %.2f ambient x %.2f count = %.1f A, limited by the "
              "%dC termination column %d A (110.14(C))"
              % (insulation_temp, base, a_factor, c_factor, derated,
                 term_temp, term_cap))
    if derated < term_cap:
        detail = ("%dC base %d A x %.2f ambient x %.2f count = %.1f A "
                  "(below the %dC termination cap of %d A, so derating governs)"
                  % (insulation_temp, base, a_factor, c_factor, derated,
                     term_temp, term_cap))
    return allowed, detail


def small_conductor_cap(material, size):
    """NEC 240.4(D) OCPD ceiling for 14/12/10 AWG, or None if the rule is silent."""
    return T.SMALL_CONDUCTOR_LIMIT.get((material, size))


# ---- main ---------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="SPD 2014 volt-loss calculator and wire-size selector")
    p.add_argument("--version", action="version",
                   version="%(prog)s " + CALC_VERSION)

    p.add_argument("--amps", type=float, required=True,
                   help="circuit load current (A). For a continuous load this "
                        "should be the ACTUAL load, not 125%% of it -- 125%% sizes "
                        "the OCPD and conductor ampacity (210.19/215.2), it does "
                        "not increase the current that causes the drop.")
    p.add_argument("--length-ft", type=float, required=True,
                   help="one-way circuit length in feet (the formula doubles it "
                        "internally for single-phase)")
    p.add_argument("--voltage", type=float, required=True,
                   help="circuit nominal voltage the percentage is taken against "
                        "(480, 240, 208, 120...)")
    p.add_argument("--phase", type=int, choices=[1, 3], default=3)
    p.add_argument("--conductor", choices=["cu", "al"], default="cu")
    p.add_argument("--conduit", choices=["steel", "nonmagnetic"], default="steel",
                   help="steel = magnetic (EMT/RMC/IMC); nonmagnetic = PVC, "
                        "aluminum, fibre. Changes the AC resistance and the "
                        "reactance, so it changes the answer.")
    p.add_argument("--pf", type=float, default=0.9,
                   help="load power factor, 0.60 to 1.00 (default 0.9 mixed "
                        "commercial). Motor-heavy loads run 0.8 or below.")
    p.add_argument("--per-phase", type=int, default=1,
                   help="conductors per phase (parallel sets)")

    m = p.add_mutually_exclusive_group(required=True)
    m.add_argument("--size", default=None,
                   help="conductor size to evaluate (14 ... 1000; 1/0 or 0 both "
                        "accepted)")
    m.add_argument("--select", action="store_true",
                   help="pick the smallest conductor meeting --limit-percent AND "
                        "the ampacity requirement")

    p.add_argument("--limit-percent", type=float, default=3.0,
                   help="permissible voltage drop for THIS circuit, percent. "
                        "Default 3.0 -- the 210.19/215.2 Informational Note value, "
                        "which is advisory, not mandatory. Use 1.5 for 647.4(D) "
                        "sensitive electronic equipment.")
    p.add_argument("--upstream-percent", type=float, default=0.0,
                   help="voltage drop already spent upstream, percent, for the "
                        "combined feeder+branch check against --total-limit")
    p.add_argument("--total-limit-percent", type=float, default=5.0,
                   help="permissible combined feeder + branch drop, percent "
                        "(default 5.0, the 215.2 Informational Note value)")

    p.add_argument("--term-temp", type=int, choices=[60, 75], default=75,
                   help="termination temperature column per 110.14(C). 60 is "
                        "required for equipment rated 100 A or less unless the "
                        "gear is listed otherwise.")
    p.add_argument("--insulation-temp", type=int, choices=[60, 75, 90], default=90,
                   help="conductor insulation rating that derating starts from "
                        "(90 for THHN/THWN-2/XHHW-2). Default 90.")
    p.add_argument("--ambient-c", type=int, default=30,
                   help="ambient temperature C (default 30, the table basis)")
    p.add_argument("--ccc", type=int, default=3,
                   help="current-carrying conductors in the raceway (default 3, "
                        "no adjustment)")
    p.add_argument("--ocpd", type=float, default=None,
                   help="overcurrent device rating (A), to check the 240.4(D) "
                        "small-conductor cap")
    p.add_argument("--format", choices=["report", "json"], default="report")
    args = p.parse_args()

    assumptions, flags = [], []

    if not 0.60 <= args.pf <= 1.00:
        p.error("--pf must be between 0.60 and 1.00 (SPD Tables A/B stop at 60%); "
                "got %.2f" % args.pf)
    pf_percent = round(args.pf * 100, 4)

    material = args.conductor
    conduit = args.conduit
    available = [s for s in T.SIZE_ORDER if s in T.VOLT_LOSS[material][conduit]]

    # ---- select or evaluate ---------------------------------------------------
    permissible_volts = args.voltage * args.limit_percent / 100.0
    if args.select:
        chosen = None
        rejected = []
        for size in available:
            fig = volt_loss_figure(material, conduit, size, args.phase, pf_percent,
                                   [])
            vd = volt_loss(fig, args.length_ft, args.amps, args.per_phase)
            amp_ok, amp_detail = ampacity_check(
                material, conduit, size, args.term_temp, args.ambient_c, args.ccc,
                args.insulation_temp, assumptions, flags)
            amp_ok = amp_ok * args.per_phase
            cap = small_conductor_cap(material, size)
            ocpd_ok = True
            if args.ocpd is not None and cap is not None and args.ocpd > cap:
                ocpd_ok = False
            if vd <= permissible_volts and amp_ok >= args.amps and ocpd_ok:
                chosen = size
                break
            reason = []
            if vd > permissible_volts:
                reason.append("%.2f%% drop" % (vd / args.voltage * 100))
            if amp_ok < args.amps:
                reason.append("%.0f A ampacity" % amp_ok)
            if not ocpd_ok:
                reason.append("240.4(D) caps OCPD at %d A" % cap)
            rejected.append("%s (%s)" % (size, ", ".join(reason)))
        if chosen is None:
            flags.append(
                "No single conductor in SPD Table %s meets both the %.1f%% drop "
                "limit and the %.0f A load at %d per phase. Add parallel sets "
                "(--per-phase), raise the limit, or shorten the run."
                % ("A" if material == "cu" else "B", args.limit_percent, args.amps,
                   args.per_phase)
            )
            print("\n".join("  x %s" % r for r in rejected))
            sys.exit(1)
        size = chosen
        assumptions.append(
            "Size selected by walking SPD Table %s from the smallest conductor up "
            "and taking the first that satisfies BOTH the %.1f%% drop limit and "
            "the derated ampacity. Sizes rejected on the way: %s."
            % ("A" if material == "cu" else "B", args.limit_percent,
               "; ".join(rejected) if rejected else "none")
        )
    else:
        size = T.normalize_size(args.size)
        if size not in T.VOLT_LOSS[material][conduit]:
            p.error("SPD Table %s has no %s row for %s -- aluminum starts at 12 AWG"
                    % ("A" if material == "cu" else "B", size, material.upper()))

    # ---- the numbers ----------------------------------------------------------
    figure = volt_loss_figure(material, conduit, size, args.phase, pf_percent,
                              assumptions)
    vd_volts = volt_loss(figure, args.length_ft, args.amps, args.per_phase)
    vd_percent = vd_volts / args.voltage * 100.0
    total_percent = vd_percent + args.upstream_percent
    allowed, amp_detail = ampacity_check(
        material, conduit, size, args.term_temp, args.ambient_c, args.ccc,
        args.insulation_temp, assumptions, flags)
    allowed_total = allowed * args.per_phase

    # ---- assumptions ----------------------------------------------------------
    assumptions.append(
        "Volt loss from SPD Table %s (%s, %s raceway), which carries the "
        "conductor's AC resistance and reactance at the stated PF -- not a "
        "resistance-only approximation."
        % ("A" if material == "cu" else "B", material.upper(), conduit)
    )
    assumptions.append(
        "Load current %.1f A taken as the actual running current. If this is a "
        "continuous load, 125%% (%.1f A) sizes the OCPD and ampacity but NOT the "
        "drop -- the drop is caused by the real current."
        % (args.amps, args.amps * 1.25)
    )
    if args.ambient_c == 30 and args.ccc <= 3:
        assumptions.append(
            "No ampacity derating: 30C ambient and 3 or fewer current-carrying "
            "conductors (the Table 310.16 basis)."
        )
    assumptions.append(
        "%.1f%% limit is the 210.19(A)/215.2(A) Informational Note value. Those "
        "notes are ADVISORY, not enforceable -- an AHJ, an owner spec, or "
        "647.4(D)/695.7 can impose a stricter mandatory limit."
        % args.limit_percent
    )

    # ---- flags ----------------------------------------------------------------
    if vd_percent > args.limit_percent:
        flags.append(
            "%.2f%% drop EXCEEDS the %.1f%% limit by %.2f points. Go up a size, "
            "add a parallel set, shorten the run, or move the source closer."
            % (vd_percent, args.limit_percent, vd_percent - args.limit_percent)
        )
    if args.upstream_percent and total_percent > args.total_limit_percent:
        flags.append(
            "Combined drop %.2f%% (%.2f%% upstream + %.2f%% here) exceeds the "
            "%.1f%% total limit. The branch alone passes; the feeder budget does "
            "not." % (total_percent, args.upstream_percent, vd_percent,
                      args.total_limit_percent)
        )
    if allowed_total < args.amps:
        flags.append(
            "AMPACITY FAIL: %s %s carries %.0f A after derating but the load is "
            "%.0f A. The voltage-drop answer is irrelevant until the conductor "
            "can carry the load (310.14)."
            % (material.upper(), size, allowed_total, args.amps)
        )
    cap = small_conductor_cap(material, size)
    if cap is not None:
        if args.ocpd is not None and args.ocpd > cap:
            flags.append(
                "240.4(D) VIOLATION: %s %s is capped at a %d A overcurrent device "
                "regardless of its ampacity; %.0f A was given."
                % (material.upper(), size, cap, args.ocpd)
            )
        else:
            flags.append(
                "240.4(D): %s %s may not be protected above %d A whatever the "
                "ampacity table shows." % (material.upper(), size, cap)
            )
    if args.term_temp == 75 and args.ocpd is not None and args.ocpd <= 100:
        flags.append(
            "110.14(C)(1)(a): equipment rated 100 A or less is a 60C termination "
            "unless the gear AND the lugs are listed for 75C. --term-temp 75 was "
            "used with a %.0f A device -- confirm the listing or rerun at 60."
            % args.ocpd
        )
    if args.pf >= 0.99:
        flags.append(
            "PF 1.0 uses the 100% column, which is nearly resistance-only. Real "
            "loads are rarely unity; at 0.85 the drop on large conductors is "
            "substantially higher because reactance dominates."
        )
    if args.per_phase > 1:
        flags.append(
            "Parallel sets are only permitted at 1/0 AWG and larger (310.10(G)), "
            "must be the same length, material and terminated identically, and "
            "each set counts toward the raceway conductor count for 310.15(C)(1)."
        )

    result = {
        "conductor": "%s %s" % (material.upper(), size),
        "conduit": conduit,
        "per_phase": args.per_phase,
        "amps": args.amps,
        "length_ft": args.length_ft,
        "voltage": args.voltage,
        "phase": args.phase,
        "pf": args.pf,
        "table_figure": round(figure, 1),
        "volt_loss_v": round(vd_volts, 3),
        "volt_loss_line_to_neutral_v": round(line_to_neutral(vd_volts, args.phase), 3),
        "volt_drop_percent": round(vd_percent, 2),
        "limit_percent": args.limit_percent,
        "within_limit": vd_percent <= args.limit_percent,
        "upstream_percent": args.upstream_percent,
        "total_percent": round(total_percent, 2),
        "total_limit_percent": args.total_limit_percent,
        "ampacity_allowed_a": round(allowed_total, 1),
        "ampacity_basis": amp_detail,
        "ampacity_ok": allowed_total >= args.amps,
        "small_conductor_ocpd_cap_a": cap,
        "voltage_at_load_v": round(args.voltage - vd_volts, 1),
        "assumptions": assumptions,
        "flags": flags,
    }

    if args.format == "json":
        print(json.dumps(result, indent=2))
        return

    print("=" * 66)
    print("VOLTAGE DROP REPORT (SPD 2014 volt-loss method)")
    print("=" * 66)
    print("Conductor:         %s %s, %d per phase, %s raceway"
          % (material.upper(), size, args.per_phase, conduit))
    print("Circuit:           %.0f A, %.0f ft, %gV %dph, PF %.2f"
          % (args.amps, args.length_ft, args.voltage, args.phase, args.pf))
    print("-" * 66)
    print("Table figure:      %.1f   (SPD Table %s, %s raceway, %d-phase column)"
          % (figure, "A" if material == "cu" else "B", conduit, args.phase))
    print("Volt loss:         %.3f V   = %.0f ft x %.0f A x %.1f / 1,000,000%s"
          % (vd_volts, args.length_ft, args.amps, figure,
             "" if args.per_phase == 1 else " / %d" % args.per_phase))
    print("Voltage drop:      %.2f%%   (limit %g%%) -> %s"
          % (vd_percent, args.limit_percent,
             "OK" if vd_percent <= args.limit_percent else "EXCEEDS"))
    if args.upstream_percent:
        print("Combined drop:     %.2f%%   (%.2f%% upstream + %.2f%% here; "
              "limit %.1f%%) -> %s"
              % (total_percent, args.upstream_percent, vd_percent,
                 args.total_limit_percent,
                 "OK" if total_percent <= args.total_limit_percent else "EXCEEDS"))
    print("  line-to-neutral: %.3f V   (SPD divides by %s; the PERCENT drop is"
          % (line_to_neutral(vd_volts, args.phase),
             "1.73" if args.phase == 3 else "2"))
    print("                     unchanged -- do not quote this against %gV)"
          % args.voltage)
    print("Voltage at load:   %.1f V" % (args.voltage - vd_volts))
    print("-" * 66)
    print("Ampacity:          %.1f A available vs %.0f A load -> %s"
          % (allowed_total, args.amps,
             "OK" if allowed_total >= args.amps else "TOO SMALL"))
    print("                   %s" % amp_detail)
    if args.per_phase > 1:
        print("                   x %d parallel sets" % args.per_phase)
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
    print("NOTE: SPD Tables A/B are 60 Hz, lagging PF, and assume a balanced")
    print("circuit at the conductor's operating temperature. Harmonic-rich loads")
    print("and long parallel runs need a per-unit or manufacturer calculation.")


if __name__ == "__main__":
    main()
