#!/usr/bin/env python3
"""
Generator sizing engine — deterministic implementation of the four-constraint method.

Reads a JSON load list, computes running kW/kVA, worst-case motor-start transient,
applies derates and margin, and returns the required kW with the next standard size.

Usage:
    python3 size_generator.py load_list.json
    python3 size_generator.py --example   # writes example_load_list.json and runs it

This is the SINGLE SOURCE OF TRUTH for the arithmetic. The SKILL.md drives the intake;
this script does the math so results are reproducible and auditable.
"""
import copy
import json
import sys
import math

# ----- Deterministic constants (mirror references/, keep in sync) -----

NEMA_CODE_KVA_PER_HP = {
    "A": 1.6, "B": 3.3, "C": 3.8, "D": 4.25, "E": 4.75, "F": 5.3, "G": 5.9,
    "H": 6.7, "J": 7.5, "K": 8.5, "L": 9.5, "M": 10.6, "N": 11.8, "P": 13.25,
    "R": 15.0, "S": 17.0, "T": 19.0, "U": 21.2, "V": 23.0,
}
DEFAULT_CODE_LETTER = "G"  # standard NEMA Design B; use H if high-efficiency

START_METHOD_FACTOR = {
    "dol": 1.00, "direct": 1.00, "across-the-line": 1.00,
    "autotransformer-80": 0.64, "autotransformer-65": 0.42, "autotransformer-50": 0.25,
    "wye-delta": 0.33, "star-delta": 0.33,
    "part-winding": 0.65,
    "soft-starter": 0.40, "soft": 0.40,
    "vfd": 0.15,
}

def starting_pf(hp):
    if hp < 100:
        return 0.30
    if hp <= 1000:
        return 0.20
    return 0.15

# Max startable sKVA as a fraction of generator rated kVA at the dip target.
# Conservative planning factors; OEM motor-starting curve is authoritative.
DIP_STARTABLE_RATIO = {
    35: 0.85, 30: 0.75, 25: 0.70, 20: 0.65, 15: 0.45, 10: 0.30,
}


def dip_startable_ratio(dip_target_pct):
    """Ratio for a dip target, snapping to the next STRICTER tabulated row.

    An untabulated target must never silently fall back to the 20% factor: a
    tighter dip needs a SMALLER ratio (bigger alternator), not the default.
    Returns (ratio, note); note is None only on an exact table hit.
    """
    if dip_target_pct in DIP_STARTABLE_RATIO:
        return DIP_STARTABLE_RATIO[dip_target_pct], None
    stricter = [d for d in DIP_STARTABLE_RATIO if d <= dip_target_pct]
    if stricter:
        row = max(stricter)
        return DIP_STARTABLE_RATIO[row], (
            f"dip_target_pct {dip_target_pct}% is not tabulated; used the {row}% row "
            f"(ratio {DIP_STARTABLE_RATIO[row]}), the next stricter value. Confirm on the "
            f"OEM motor-starting curve.")
    row = min(DIP_STARTABLE_RATIO)
    return DIP_STARTABLE_RATIO[row], (
        f"dip_target_pct {dip_target_pct}% is BELOW the {row}% table floor, so ratio "
        f"{DIP_STARTABLE_RATIO[row]} is OPTIMISTIC at this target. Size against the OEM "
        f"motor-starting curve before issuing.")

STANDARD_SIZES_KW = [
    20, 25, 30, 35, 40, 50, 60, 80, 100, 125, 150, 175, 200, 230, 250, 300,
    350, 400, 450, 500, 600, 750, 800, 1000, 1250, 1500, 1750, 2000, 2250,
    2500, 2750, 3000,
]

GEN_PF = 0.8  # standard genset rating power factor


def motor_running_kw(hp, efficiency=0.90, load_factor=1.0):
    return hp * 0.746 / efficiency * load_factor


def next_standard_size(kw):
    for s in STANDARD_SIZES_KW:
        if s >= kw:
            return s
    return None  # exceeds catalog; needs paralleling


def size(loads, gen_pf=GEN_PF, dip_target_pct=20, altitude_ft=0, ambient_c=25,
         harmonic_load_fraction=0.0, spare_fraction=0.20, _mitigate=True):
    """
    loads: list of dicts. Each load:
      {
        "name": str,
        "category": "emergency"|"legally_required"|"optional"|"firepump",
        "kind": "motor"|"static",
        # motor:
        "hp": float, "voltage": int, "code_letter": str|None,
        "efficiency": float, "load_factor": float,
        "start_method": str, "pf_running": float,
        # static (lighting, resistive, electronic):
        "kw": float, "pf": float,
        "qty": int, "demand_factor": float,
        "on_generator": bool
      }
    """
    running_kw = 0.0
    running_kva = 0.0
    motors = []
    detail = []

    for ld in loads:
        if not ld.get("on_generator", True):
            continue
        qty = ld.get("qty", 1)
        df = ld.get("demand_factor", 1.0)

        if ld.get("kind") == "motor":
            hp = ld["hp"]
            eff = ld.get("efficiency", 0.90)
            lf = ld.get("load_factor", 1.0)
            pf_run = ld.get("pf_running", 0.85)
            rkw = motor_running_kw(hp, eff, lf) * qty * df
            rkva = rkw / pf_run
            running_kw += rkw
            running_kva += rkva

            cl = (ld.get("code_letter") or DEFAULT_CODE_LETTER).upper()
            kva_per_hp = NEMA_CODE_KVA_PER_HP.get(cl, NEMA_CODE_KVA_PER_HP[DEFAULT_CODE_LETTER])
            dol_skva = hp * kva_per_hp
            sm = (ld.get("start_method") or "dol").lower()
            factor = START_METHOD_FACTOR.get(sm, 1.00)
            applied_skva = dol_skva * factor
            motors.append({
                "name": ld.get("name", f"{hp}hp motor"),
                "hp": hp, "code_letter": cl, "kva_per_hp": kva_per_hp,
                "dol_skva": dol_skva, "start_method": sm, "factor": factor,
                "applied_skva": applied_skva, "running_kw": rkw, "running_kva": rkva,
                "category": ld.get("category", "optional"),
            })
            detail.append(f"{ld.get('name','motor')}: run {rkw:.1f} kW / {rkva:.1f} kVA; "
                          f"start {applied_skva:.0f} sKVA ({sm}, code {cl})")
        else:
            kw = ld.get("kw", 0.0) * qty * df
            pf = ld.get("pf", 1.0)
            kva = kw / pf if pf else kw
            running_kw += kw
            running_kva += kva
            detail.append(f"{ld.get('name','load')}: {kw:.1f} kW / {kva:.1f} kVA")

    # Worst-case start: largest applied_skva started LAST (on top of base running load,
    # excluding that motor's own running contribution).
    worst = None
    peak_kva = running_kva
    peak_kw = running_kw
    if motors:
        worst = max(motors, key=lambda m: m["applied_skva"])
        base_kva = running_kva - worst["running_kva"]
        base_kw = running_kw - worst["running_kw"]
        spf = starting_pf(worst["hp"])
        peak_kva = base_kva + worst["applied_skva"]
        peak_kw = base_kw + worst["applied_skva"] * spf

    # Constraint sizing
    ratio, dip_ratio_note = dip_startable_ratio(dip_target_pct)
    c_a_kw = running_kw / gen_pf                 # (a) running kW need (engine), as genset kW
    c_b_kw = running_kva * gen_pf                # (b) alternator thermal need, as genset kW
    min_gen_kva_for_start = (worst["applied_skva"] / ratio) if worst else 0.0
    c_c_kw = min_gen_kva_for_start * gen_pf      # (c) transient voltage-dip need
    c_d_kw = peak_kw                             # (d) engine block-load need

    # Spare/growth margin applies to RUNNING constraints (a, b) ONLY.
    # A transient-governed size already carries large running headroom;
    # compounding growth margin onto the dip/block-load number over-buys.
    required_running_kw = max(c_a_kw, c_b_kw) * (1.0 + spare_fraction)
    required_transient_kw = max(c_c_kw, c_d_kw)
    required_kw_pre_derate = max(required_running_kw, required_transient_kw)
    raw_vals = [c_a_kw, c_b_kw, c_c_kw, c_d_kw]
    governing = ["running_kW", "alternator_kVA", "voltage_dip", "block_load_kW"][
        raw_vals.index(max(raw_vals))]

    # Derates applied to OEM rating => we must UPSIZE required by 1/derate
    alt_derate = 1.0
    if altitude_ft > 500:
        alt_derate -= 0.03 * ((altitude_ft - 500) / 1000.0)
    # NOTE: derate threshold 40C is a simplification; some OEMs derate from 25-40C.
    # Hot-climate sites (e.g., FL summers ~35-38C) may see small OEM derates not modeled here.
    if ambient_c > 40:
        alt_derate -= 0.02 * ((ambient_c - 40) / 10.0)
    alt_derate = max(alt_derate, 0.5)

    harmonic_derate = 1.0
    if harmonic_load_fraction > 0.30:
        # oversize alternator ~ proportional to harmonic load above 30%
        harmonic_derate = 1.0 - 0.5 * (harmonic_load_fraction - 0.30)
        harmonic_derate = max(harmonic_derate, 0.7)

    effective_derate = alt_derate * harmonic_derate
    required_kw_derated = required_kw_pre_derate / effective_derate
    chosen = next_standard_size(required_kw_derated)

    # Wet-stacking check: chronic diesel loading below ~30% of rating
    load_factor_on_recommended = round(running_kw / chosen, 3) if chosen else None
    wet_stacking_warning = None
    if chosen and load_factor_on_recommended < 0.30:
        wet_stacking_warning = (
            f"Running load is only {load_factor_on_recommended*100:.0f}% of the recommended "
            f"{chosen} kW set (< 30%). Diesel wet-stacking risk: specify a permanent load bank "
            f"or load-bank connection (also needed for NFPA 110 testing), or revisit mitigation "
            f"options below to shrink the set.")

    # Mitigation what-ifs: when a transient constraint governs, show the size delta
    # from reduced-voltage starting on the worst motor. OEM curve still authoritative.
    mitigation_options = []
    if _mitigate and worst and governing in ("voltage_dip", "block_load_kW"):
        for alt_method in ("wye-delta", "soft-starter", "vfd"):
            if START_METHOD_FACTOR[alt_method] >= worst["factor"]:
                continue  # not an improvement over current method
            mod_loads = copy.deepcopy(loads)
            for ld in mod_loads:
                if ld.get("kind") == "motor" and ld.get("name", f"{ld.get('hp')}hp motor") == worst["name"]:
                    ld["start_method"] = alt_method
            res = size(mod_loads, gen_pf=gen_pf, dip_target_pct=dip_target_pct,
                       altitude_ft=altitude_ft, ambient_c=ambient_c,
                       harmonic_load_fraction=harmonic_load_fraction,
                       spare_fraction=spare_fraction, _mitigate=False)
            if res["recommended_standard_size_kw"] and chosen and \
               res["recommended_standard_size_kw"] < chosen:
                mitigation_options.append({
                    "option": f"Change '{worst['name']}' starting to {alt_method}",
                    "new_size_kw": res["recommended_standard_size_kw"],
                    "kw_saved": chosen - res["recommended_standard_size_kw"],
                    "new_governing_constraint": res["governing_constraint"],
                })
        if worst["factor"] >= 0.99:
            mitigation_options.append({
                "option": ("Stagger motor starts across ATS/step-load sequence so the worst "
                           "motor starts against a lighter bus (reduces block-load kW, not dip)"),
                "new_size_kw": None, "kw_saved": None,
                "new_governing_constraint": "requires step-sequence analysis",
            })
        mitigation_options.append({
            "option": ("Specify an oversized alternator frame (next frame up / low-X\u2033d winding) "
                       "on the same engine instead of a larger genset \u2014 validate on the OEM "
                       "motor-starting curve (GenSize / SpecSizer / Kohler sizing)"),
            "new_size_kw": None, "kw_saved": None,
            "new_governing_constraint": "OEM-curve dependent",
        })

    return {
        "running_kw": round(running_kw, 1),
        "running_kva": round(running_kva, 1),
        "worst_start_motor": worst["name"] if worst else None,
        "worst_applied_skva": round(worst["applied_skva"], 0) if worst else 0,
        "peak_transient_kva": round(peak_kva, 0),
        "peak_transient_kw": round(peak_kw, 0),
        "constraint_a_running_kw": round(c_a_kw, 1),
        "constraint_b_alternator_kw": round(c_b_kw, 1),
        "constraint_c_voltage_dip_kw": round(c_c_kw, 1),
        "constraint_d_block_load_kw": round(c_d_kw, 1),
        "governing_constraint": governing,
        "required_running_kw_with_spare": round(required_running_kw, 1),
        "required_transient_kw": round(required_transient_kw, 1),
        "required_kw_pre_derate": round(required_kw_pre_derate, 1),
        "altitude_derate": round(alt_derate, 3),
        "harmonic_derate": round(harmonic_derate, 3),
        "required_kw_after_derate": round(required_kw_derated, 1),
        "spare_fraction_applied_to_running_only": spare_fraction,
        "recommended_standard_size_kw": chosen,
        "load_factor_on_recommended": load_factor_on_recommended,
        "wet_stacking_warning": wet_stacking_warning,
        "mitigation_options": mitigation_options,
        "dip_target_pct": dip_target_pct,
        "dip_ratio_note": dip_ratio_note,
        "load_detail": detail,
        "note_paralleling": None if chosen else "Required kW exceeds 3000 kW catalog max; consider paralleling multiple sets.",
    }


EXAMPLE = {
    "params": {"gen_pf": 0.8, "dip_target_pct": 20, "altitude_ft": 100,
               "ambient_c": 35, "harmonic_load_fraction": 0.10, "spare_fraction": 0.20},
    "loads": [
        {"name": "Egress lighting", "category": "emergency", "kind": "static",
         "kw": 25, "pf": 0.95, "qty": 1, "demand_factor": 1.0, "on_generator": True},
        {"name": "Fire alarm + smoke control", "category": "emergency", "kind": "static",
         "kw": 15, "pf": 0.9, "qty": 1, "demand_factor": 1.0, "on_generator": True},
        {"name": "Elevator (egress)", "category": "emergency", "kind": "motor",
         "hp": 40, "voltage": 480, "code_letter": "H", "efficiency": 0.92,
         "load_factor": 1.0, "start_method": "vfd", "pf_running": 0.85,
         "qty": 1, "demand_factor": 1.0, "on_generator": True},
        {"name": "Chilled water pump", "category": "optional", "kind": "motor",
         "hp": 75, "voltage": 480, "code_letter": "G", "efficiency": 0.93,
         "load_factor": 0.9, "start_method": "wye-delta", "pf_running": 0.86,
         "qty": 1, "demand_factor": 1.0, "on_generator": True},
        {"name": "Cooling tower fan", "category": "optional", "kind": "motor",
         "hp": 30, "voltage": 480, "code_letter": "G", "efficiency": 0.90,
         "load_factor": 1.0, "start_method": "dol", "pf_running": 0.84,
         "qty": 2, "demand_factor": 1.0, "on_generator": True},
        {"name": "Receptacle / misc", "category": "optional", "kind": "static",
         "kw": 60, "pf": 0.9, "qty": 1, "demand_factor": 0.6, "on_generator": True},
    ],
}


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--example":
        with open("example_load_list.json", "w") as f:
            json.dump(EXAMPLE, f, indent=2)
        data = EXAMPLE
        print("Wrote example_load_list.json\n")
    elif len(sys.argv) >= 2:
        with open(sys.argv[1]) as f:
            data = json.load(f)
    else:
        print(__doc__)
        sys.exit(1)

    params = data.get("params", {})
    result = size(data["loads"], **params)
    print(json.dumps(result, indent=2))
    print("\n--- SUMMARY ---")
    print(f"Running load:        {result['running_kw']} kW / {result['running_kva']} kVA")
    print(f"Worst-start motor:   {result['worst_start_motor']} "
          f"({result['worst_applied_skva']:.0f} sKVA applied)")
    print(f"Peak transient:      {result['peak_transient_kva']:.0f} kVA / "
          f"{result['peak_transient_kw']:.0f} kW")
    print(f"Governing constraint: {result['governing_constraint']}")
    print(f"Running need + spare: {result['required_running_kw_with_spare']} kW | "
          f"Transient need (no spare): {result['required_transient_kw']} kW")
    print(f"Required (pre-derate): {result['required_kw_pre_derate']} kW")
    print(f"Derate factor:        {result['altitude_derate']*result['harmonic_derate']:.3f}")
    if result["recommended_standard_size_kw"]:
        print(f">>> RECOMMENDED SIZE:  {result['recommended_standard_size_kw']} kW (standby rating), "
              f"running load factor {result['load_factor_on_recommended']*100:.0f}%")
    else:
        print(f">>> RECOMMENDED SIZE:  exceeds the {STANDARD_SIZES_KW[-1]} kW catalog max "
              f"({result['required_kw_after_derate']} kW required) -- see note below")
    if result["dip_ratio_note"]:
        print(f"!!! DIP TARGET: {result['dip_ratio_note']}")
    if result["wet_stacking_warning"]:
        print(f"!!! WET STACKING: {result['wet_stacking_warning']}")
    if result["mitigation_options"]:
        print("--- MITIGATION OPTIONS (transient constraint governs) ---")
        for m in result["mitigation_options"]:
            if m["new_size_kw"]:
                print(f"  * {m['option']} -> {m['new_size_kw']} kW "
                      f"(saves {m['kw_saved']} kW; new governing: {m['new_governing_constraint']})")
            else:
                print(f"  * {m['option']}")
    if result["note_paralleling"]:
        print(f"!!! {result['note_paralleling']}")


if __name__ == "__main__":
    main()
