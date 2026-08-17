"""Fixed data tables for point-to-point short-circuit and volt-loss calculations.

Source: Eaton/Bussmann "Selecting Protective Devices" (SPD) handbook, 2014 edition,
pages 241-245. Transcribed verbatim except where noted in ERRATA below.

This module holds data only -- no calculation logic. short_circuit.py and
voltage_drop.py both import from here so the two calculators can never disagree
about a "C" value or an ampacity.

Tables included
  TRANSFORMER_Z          SPD Table 1  - typical %Z by kVA / voltage / phase
  XFMR_1PH_IMPEDANCE     SPD p.241    - 1-phase X/R, %Z range, L-N multipliers
  C_VALUES               SPD Table 4  - conductor "C" constants
  BUSWAY_C               SPD Table 5  - busway "C" constants
  FAULT_TYPE_PERCENT     SPD Table 3  - other fault types as % of 3-phase bolted
  VOLT_LOSS              SPD Tables A/B - ampacity + volt-loss figures
  AMBIENT_CORRECTION     NEC Table 310.15(B)(1) (2023) / 310.15(B)(2)(a) (2014)
  CCC_ADJUSTMENT         NEC Table 310.15(C)(1) (2023) / 310.15(B)(3)(a) (2014)

ERRATA -- deliberate departures from the printed page
  1. The printed "Direct Current" volt-loss column diverges between the Steel and
     Non-Magnetic blocks at exactly three of the 41 size rows:
         Cu 12 AWG   Steel 3860  Non-Magnetic 3464
         Cu 3 AWG    Steel  490  Non-Magnetic  470
         Al 3/0      Steel  259  Non-Magnetic  252
     DC resistance cannot depend on the raceway and the other 38 rows agree
     exactly, so all three are print errors. DC volt loss is stored once per
     size, taken from the Steel column. See references/tables-and-errata.md.
"""

# --------------------------------------------------------------------------
# Conductor size handling
# --------------------------------------------------------------------------
# Canonical size keys use the "1/0" style. SPD Table 4 prints "1/0"; SPD Tables
# A and B print "0". Both spellings are accepted on input.

SIZE_ALIASES = {
    "0": "1/0", "00": "2/0", "000": "3/0", "0000": "4/0",
    "1/0": "1/0", "2/0": "2/0", "3/0": "3/0", "4/0": "4/0",
    "250 kcmil": "250", "300 kcmil": "300", "350 kcmil": "350",
    "400 kcmil": "400", "500 kcmil": "500", "600 kcmil": "600",
    "750 kcmil": "750", "1000 kcmil": "1000",
    "#14": "14", "#12": "12", "#10": "10", "#8": "8", "#6": "6",
    "#4": "4", "#3": "3", "#2": "2", "#1": "1",
}

# Ascending order, smallest conductor first. Used for wire-size selection.
SIZE_ORDER = [
    "14", "12", "10", "8", "6", "4", "3", "2", "1",
    "1/0", "2/0", "3/0", "4/0",
    "250", "300", "350", "400", "500", "600", "750", "1000",
]


def normalize_size(size):
    """Map a user-entered conductor size onto a canonical SIZE_ORDER key."""
    s = str(size).strip().upper().replace("KCMIL", "").replace("AWG", "").strip()
    s = s.replace(" ", "")
    if s in SIZE_ALIASES:
        return SIZE_ALIASES[s]
    lowered = str(size).strip().lower()
    if lowered in SIZE_ALIASES:
        return SIZE_ALIASES[lowered]
    if s in SIZE_ORDER:
        return s
    raise ValueError(
        "unknown conductor size %r -- expected one of: %s"
        % (size, ", ".join(SIZE_ORDER))
    )


# --------------------------------------------------------------------------
# SPD Table 1 -- Short-circuit currents available from various size transformers
# --------------------------------------------------------------------------
# Keyed (voltage_label, phase) -> {kVA: (full_load_amps, percent_Z)}.
# %Z here is the NAMEPLATE value; apply the tolerance factor separately.
# Note per SPD: UL-listed transformers 25 kVA and larger carry a +/-10% impedance
# tolerance, so these are starting points only -- always prefer the nameplate.

TRANSFORMER_Z = {
    ("120/240", 1): {
        25: (104, 1.5), 37.5: (156, 1.5), 50: (208, 1.5),
        75: (313, 1.5), 100: (417, 1.6), 167: (696, 1.6),
    },
    ("120/208", 3): {
        45: (125, 1.0), 75: (208, 1.0), 112.5: (312, 1.11),
        150: (416, 1.07), 225: (625, 1.12), 300: (833, 1.11),
        500: (1388, 1.24), 750: (2082, 3.50), 1000: (2776, 3.50),
        1500: (4164, 3.50), 2000: (5552, 4.00), 2500: (6940, 4.00),
    },
    ("277/480", 3): {
        75: (90, 1.00), 112.5: (135, 1.00), 150: (181, 1.20),
        225: (271, 1.20), 300: (361, 1.20), 500: (602, 1.30),
        750: (903, 3.50), 1000: (1204, 3.50), 1500: (1806, 3.50),
        2000: (2408, 4.00), 2500: (3011, 4.00),
    },
}

# --------------------------------------------------------------------------
# SPD p.241 -- Impedance data for single-phase transformers
# --------------------------------------------------------------------------
# kVA -> (suggested X/R for calculation, %Z low, %Z high, L-N mult for %X,
#         L-N mult for %R).
# The L-N multipliers are on the HALF-WINDING kVA base (one-half nameplate kVA
# divided by secondary line-to-neutral voltage). On a FULL-winding base the
# equivalent multipliers quoted on SPD p.239 are 1.2 x %X and 1.5 x %R -- the
# same numbers doubled.

XFMR_1PH_IMPEDANCE = {
    25.0: (1.1, 1.2, 6.0, 0.6, 0.75),
    37.5: (1.4, 1.2, 6.5, 0.6, 0.75),
    50.0: (1.6, 1.2, 6.4, 0.6, 0.75),
    75.0: (1.8, 1.2, 6.6, 0.6, 0.75),
    100.0: (2.0, 1.3, 5.7, 0.6, 0.75),
    167.0: (2.5, 1.4, 6.1, 1.0, 0.75),
    250.0: (3.6, 1.9, 6.8, 1.0, 0.75),
    333.0: (4.7, 2.4, 6.0, 1.0, 0.75),
    500.0: (5.5, 2.2, 5.4, 1.0, 0.75),
}

# SPD p.239 -- half-winding adjustment on a FULL-winding %R/%X basis, used when
# a line-to-neutral fault is computed from full-winding nameplate %R and %X.
HALF_WINDING_R_MULT = 1.5
HALF_WINDING_X_MULT = 1.2

# SPD Note 5 -- at the terminals of a 1-phase center-tapped transformer the
# line-to-neutral bolted fault exceeds the line-to-line fault.
LN_TERMINAL_FAULT_MULT = 1.5

# SPD Notes 2 and 3 -- worst-case adjustment factors.
Z_TOLERANCE = {"high": 0.9, "nameplate": 1.0, "low": 1.1}
UTILITY_VOLTAGE = {"high": 1.1, "high_120v": 1.058, "nominal": 1.0,
                   "low": 0.9, "low_120v": 0.942}

# SPD Step 6A -- practical estimate of motor short-circuit contribution.
MOTOR_CONTRIBUTION_MULT = 4  # 4 to 6 commonly accepted; 4 is the SPD default

# --------------------------------------------------------------------------
# SPD Table 3 -- Various types of short-circuit currents as a percent of the
# three-phase bolted fault (typical)
# --------------------------------------------------------------------------

FAULT_TYPE_PERCENT = {
    "three_phase_bolted": (100, 100, "100%"),
    "line_to_line_bolted": (87, 87, "87%"),
    "line_to_ground_bolted": (25, 125, "25-125% (100% near transformer, 50% otherwise)"),
    "line_to_neutral_bolted": (25, 125, "25-125% (100% near transformer, 50% otherwise)"),
    "three_phase_arcing": (89, 89, "89% (maximum)"),
    "line_to_line_arcing": (74, 74, "74% (maximum)"),
    "line_to_ground_arcing": (38, 38, "38% (minimum)"),
}

# --------------------------------------------------------------------------
# SPD Table 4 -- "C" values for conductors
# --------------------------------------------------------------------------
# C_VALUES[material][arrangement][conduit][voltage_class][size]
#   material     : "cu" | "al"
#   arrangement  : "single" (three single conductors) | "cable" (3-conductor cable)
#   conduit      : "steel" (magnetic) | "nonmagnetic" (PVC, aluminum, fibre)
#   voltage_class: "600" | "5k" | "15k"
# A value of None means the SPD table prints a dash for that combination.
#
# Rows are written as size -> (steel_600, steel_5k, steel_15k,
#                              nonmag_600, nonmag_5k, nonmag_15k)
# for the two arrangements, then expanded below. This keeps the transcription
# in the same visual order as the printed page so it can be proofread.

_C_RAW = {
    ("cu", "single"): {
        "14": (389, None, None, 389, None, None),
        "12": (617, None, None, 617, None, None),
        "10": (981, None, None, 982, None, None),
        "8": (1557, 1551, None, 1559, 1555, None),
        "6": (2425, 2406, 2389, 2430, 2418, 2407),
        "4": (3806, 3751, 3696, 3826, 3789, 3753),
        "3": (4774, 4674, 4577, 4811, 4745, 4679),
        "2": (5907, 5736, 5574, 6044, 5926, 5809),
        "1": (7293, 7029, 6759, 7493, 7307, 7109),
        "1/0": (8925, 8544, 7973, 9317, 9034, 8590),
        "2/0": (10755, 10062, 9390, 11424, 10878, 10319),
        "3/0": (12844, 11804, 11022, 13923, 13048, 12360),
        "4/0": (15082, 13606, 12543, 16673, 15351, 14347),
        "250": (16483, 14925, 13644, 18594, 17121, 15866),
        "300": (18177, 16293, 14769, 20868, 18975, 17409),
        "350": (19704, 17385, 15678, 22737, 20526, 18672),
        "400": (20566, 18235, 16366, 24297, 21786, 19731),
        "500": (22185, 19172, 17492, 26706, 23277, 21330),
        "600": (22965, 20567, 17962, 28033, 25204, 22097),
        "750": (24137, 21387, 18889, 29735, 26453, 23408),
        "1000": (25278, 22539, 19923, 31491, 28083, 24887),
    },
    ("cu", "cable"): {
        "14": (389, None, None, 389, None, None),
        "12": (617, None, None, 617, None, None),
        "10": (982, None, None, 982, None, None),
        "8": (1559, 1557, None, 1560, 1558, None),
        "6": (2431, 2425, 2415, 2433, 2428, 2421),
        "4": (3830, 3812, 3779, 3838, 3823, 3798),
        "3": (4820, 4785, 4726, 4833, 4803, 4762),
        "2": (5989, 5930, 5828, 6087, 6023, 5958),
        "1": (7454, 7365, 7189, 7579, 7507, 7364),
        "1/0": (9210, 9086, 8708, 9473, 9373, 9053),
        "2/0": (11245, 11045, 10500, 11703, 11529, 11053),
        "3/0": (13656, 13333, 12613, 14410, 14119, 13462),
        "4/0": (16392, 15890, 14813, 17483, 17020, 16013),
        "250": (18311, 17851, 16466, 19779, 19352, 18001),
        "300": (20617, 20052, 18319, 22525, 21938, 20163),
        "350": (22646, 21914, 19821, 24904, 24126, 21982),
        "400": (24253, 23372, 21042, 26916, 26044, 23518),
        "500": (26980, 25449, 23126, 30096, 28712, 25916),
        "600": (28752, 27975, 24897, 32154, 31258, 27766),
        "750": (31051, 30024, 26933, 34605, 33315, 29735),
        "1000": (33864, 32689, 29320, 37197, 35749, 31959),
    },
    ("al", "single"): {
        "14": (237, None, None, 237, None, None),
        "12": (376, None, None, 376, None, None),
        "10": (599, None, None, 599, None, None),
        "8": (951, 950, None, 952, 951, None),
        "6": (1481, 1476, 1472, 1482, 1479, 1476),
        "4": (2346, 2333, 2319, 2350, 2342, 2333),
        "3": (2952, 2928, 2904, 2961, 2945, 2929),
        "2": (3713, 3670, 3626, 3730, 3702, 3673),
        "1": (4645, 4575, 4498, 4678, 4632, 4580),
        "1/0": (5777, 5670, 5493, 5838, 5766, 5646),
        "2/0": (7187, 6968, 6733, 7301, 7153, 6986),
        "3/0": (8826, 8467, 8163, 9110, 8851, 8627),
        "4/0": (10741, 10167, 9700, 11174, 10749, 10387),
        "250": (12122, 11460, 10849, 12862, 12343, 11847),
        "300": (13910, 13009, 12193, 14923, 14183, 13492),
        "350": (15484, 14280, 13288, 16813, 15858, 14955),
        "400": (16671, 15355, 14188, 18506, 17321, 16234),
        "500": (18756, 16828, 15657, 21391, 19503, 18315),
        "600": (20093, 18428, 16484, 23451, 21718, 19635),
        "750": (21766, 19685, 17686, 25976, 23702, 21437),
        "1000": (23478, 21235, 19006, 28779, 26109, 23482),
    },
    ("al", "cable"): {
        "14": (237, None, None, 237, None, None),
        "12": (376, None, None, 376, None, None),
        "10": (599, None, None, 599, None, None),
        "8": (952, 951, None, 952, 952, None),
        "6": (1482, 1480, 1478, 1482, 1481, 1479),
        "4": (2351, 2347, 2339, 2353, 2350, 2344),
        "3": (2963, 2955, 2941, 2966, 2959, 2949),
        "2": (3734, 3719, 3693, 3740, 3725, 3709),
        "1": (4686, 4664, 4618, 4699, 4682, 4646),
        "1/0": (5852, 5820, 5717, 5876, 5852, 5771),
        "2/0": (7327, 7271, 7109, 7373, 7329, 7202),
        "3/0": (9077, 8981, 8751, 9243, 9164, 8977),
        "4/0": (11185, 11022, 10642, 11409, 11277, 10969),
        "250": (12797, 12636, 12115, 13236, 13106, 12661),
        "300": (14917, 14698, 13973, 15495, 15300, 14659),
        "350": (16795, 16490, 15541, 17635, 17352, 16501),
        "400": (18462, 18064, 16921, 19588, 19244, 18154),
        "500": (21395, 20607, 19314, 23018, 22381, 20978),
        "600": (23633, 23196, 21349, 25708, 25244, 23295),
        "750": (26432, 25790, 23750, 29036, 28262, 25976),
        "1000": (29865, 29049, 26608, 32938, 31920, 29135),
    },
}

C_VALUES = {}
for (_mat, _arr), _rows in _C_RAW.items():
    _by_mat = C_VALUES.setdefault(_mat, {}).setdefault(_arr, {})
    _by_mat["steel"] = {}
    _by_mat["nonmagnetic"] = {}
    for _size, _cells in _rows.items():
        _by_mat["steel"][_size] = {"600": _cells[0], "5k": _cells[1], "15k": _cells[2]}
        _by_mat["nonmagnetic"][_size] = {"600": _cells[3], "5k": _cells[4], "15k": _cells[5]}


def c_value(material, size, conduit="steel", arrangement="single", voltage_class="600"):
    """Return the SPD Table 4 "C" constant, or raise ValueError with the reason."""
    mat = material.strip().lower()
    if mat in ("copper", "cu"):
        mat = "cu"
    elif mat in ("aluminum", "aluminium", "al"):
        mat = "al"
    else:
        raise ValueError("conductor material must be cu or al, got %r" % material)

    arr = arrangement.strip().lower()
    if arr in ("single", "three single conductors", "3sc"):
        arr = "single"
    elif arr in ("cable", "three-conductor cable", "3cc", "mc", "tray"):
        arr = "cable"
    else:
        raise ValueError("arrangement must be single or cable, got %r" % arrangement)

    cond = conduit.strip().lower()
    if cond in ("steel", "magnetic", "emt", "rmc", "imc"):
        cond = "steel"
    elif cond in ("nonmagnetic", "non-magnetic", "pvc", "aluminum", "fibre", "fiber"):
        cond = "nonmagnetic"
    else:
        raise ValueError("conduit must be steel or nonmagnetic, got %r" % conduit)

    vc = str(voltage_class).strip().lower().replace("v", "").replace("kv", "k")
    if vc in ("600", "0.6k", ".6k"):
        vc = "600"
    elif vc in ("5k", "5"):
        vc = "5k"
    elif vc in ("15k", "15"):
        vc = "15k"
    else:
        raise ValueError("voltage_class must be 600, 5k or 15k, got %r" % voltage_class)

    key = normalize_size(size)
    val = C_VALUES[mat][arr][cond][key][vc]
    if val is None:
        raise ValueError(
            "SPD Table 4 has no C value for %s %s AWG/kcmil at %s -- that size is "
            "not manufactured or not tabulated in that voltage class"
            % (mat.upper(), key, vc)
        )
    return val


# --------------------------------------------------------------------------
# SPD Table 5 -- "C" values for busway
# --------------------------------------------------------------------------
# ampacity -> {"plug_in": (cu, al), "feeder": (cu, al), "high_impedance": cu}

BUSWAY_C = {
    225: {"plug_in": (28700, 23000), "feeder": (18700, 12000), "high_impedance": None},
    400: {"plug_in": (38900, 34700), "feeder": (23900, 21300), "high_impedance": None},
    600: {"plug_in": (41000, 38300), "feeder": (36500, 31300), "high_impedance": None},
    800: {"plug_in": (46100, 57500), "feeder": (49300, 44100), "high_impedance": None},
    1000: {"plug_in": (69400, 89300), "feeder": (62900, 56200), "high_impedance": 15600},
    1200: {"plug_in": (94300, 97100), "feeder": (76900, 69900), "high_impedance": 16100},
    1350: {"plug_in": (119000, 104200), "feeder": (90100, 84000), "high_impedance": 17500},
    1600: {"plug_in": (129900, 120500), "feeder": (101000, 90900), "high_impedance": 19200},
    2000: {"plug_in": (142900, 135100), "feeder": (134200, 125000), "high_impedance": 20400},
    2500: {"plug_in": (143800, 156300), "feeder": (180500, 166700), "high_impedance": 21700},
    3000: {"plug_in": (144900, 175400), "feeder": (204100, 188700), "high_impedance": 23800},
    4000: {"plug_in": (None, None), "feeder": (277800, 256400), "high_impedance": None},
}


def busway_c(ampacity, material="cu", busway_type="feeder"):
    """Return the SPD Table 5 busway "C" constant for the tabulated ampacity."""
    amp = int(ampacity)
    if amp not in BUSWAY_C:
        raise ValueError(
            "SPD Table 5 has no busway row for %s A -- tabulated ampacities are %s"
            % (amp, ", ".join(str(a) for a in sorted(BUSWAY_C)))
        )
    bt = busway_type.strip().lower().replace("-", "_").replace(" ", "_")
    mat = "cu" if material.strip().lower() in ("cu", "copper") else "al"
    if bt in ("high_impedance", "highz", "high_z"):
        val = BUSWAY_C[amp]["high_impedance"]
        if val is None:
            raise ValueError("no high-impedance busway C value tabulated at %s A" % amp)
        if mat == "al":
            raise ValueError("SPD Table 5 tabulates high-impedance busway for copper only")
        return val
    if bt not in ("plug_in", "plugin", "feeder"):
        raise ValueError("busway_type must be plug_in, feeder or high_impedance")
    if bt == "plugin":
        bt = "plug_in"
    return BUSWAY_C[amp][bt][0 if mat == "cu" else 1]


# --------------------------------------------------------------------------
# SPD Tables A and B -- Ratings & Volt Loss
# --------------------------------------------------------------------------
# VOLT_LOSS[material][conduit][size] = {
#     "ampacity": (60C, 75C, 90C),
#     "dc": <volt loss>,
#     "three_phase": {100: v, 90: v, 80: v, 70: v, 60: v},
#     "single_phase": {100: v, 90: v, 80: v, 70: v, 60: v},
# }
#
# Volt-loss figures are in "volt loss per 1,000,000 (foot x ampere)" units:
#     volt loss = feet x amperes x figure / 1,000,000 / conductors_per_phase
# All figures are LINE-TO-LINE. Three-phase figures are the average of the
# three phases. Divide by 1.732 (3-phase) or 2 (1-phase) for line-to-neutral.
#
# Ampacities are NEC Table 310.16 (2023) / 310.15(B)(16) (2014) values, 30 C
# ambient, not more than three current-carrying conductors. Sizes flagged
# SMALL_CONDUCTOR_LIMIT are additionally capped by NEC 240.4(D).
#
# Rows: size -> (amp60, amp75, amp90, dc, 3ph100, 3ph90, 3ph80, 3ph70, 3ph60,
#                1ph100, 1ph90, 1ph80, 1ph70, 1ph60)

_VL_RAW = {
    ("cu", "steel"): {
        "14": (20, 20, 25, 6140, 5369, 4887, 4371, 3848, 3322, 6200, 5643, 5047, 4444, 3836),
        "12": (25, 25, 30, 3860, 3464, 3169, 2841, 2508, 2172, 4000, 3659, 3281, 2897, 2508),
        "10": (30, 35, 40, 2420, 2078, 1918, 1728, 1532, 1334, 2400, 2214, 1995, 1769, 1540),
        "8": (40, 50, 55, 1528, 1350, 1264, 1148, 1026, 900, 1560, 1460, 1326, 1184, 1040),
        "6": (55, 65, 75, 982, 848, 812, 745, 673, 597, 980, 937, 860, 777, 690),
        "4": (70, 85, 95, 616, 536, 528, 491, 450, 405, 620, 610, 568, 519, 468),
        "3": (85, 100, 110, 490, 433, 434, 407, 376, 341, 500, 501, 470, 434, 394),
        "2": (95, 115, 130, 388, 346, 354, 336, 312, 286, 400, 409, 388, 361, 331),
        "1": (110, 130, 150, 308, 277, 292, 280, 264, 245, 320, 337, 324, 305, 283),
        "1/0": (125, 150, 170, 244, 207, 228, 223, 213, 200, 240, 263, 258, 246, 232),
        "2/0": (145, 175, 195, 193, 173, 196, 194, 188, 178, 200, 227, 224, 217, 206),
        "3/0": (165, 200, 225, 153, 136, 162, 163, 160, 154, 158, 187, 188, 184, 178),
        "4/0": (195, 230, 260, 122, 109, 136, 140, 139, 136, 126, 157, 162, 161, 157),
        "250": (215, 255, 290, 103, 93, 123, 128, 129, 128, 108, 142, 148, 149, 148),
        "300": (240, 285, 320, 86, 77, 108, 115, 117, 117, 90, 125, 133, 135, 135),
        "350": (260, 310, 350, 73, 67, 98, 106, 109, 109, 78, 113, 122, 126, 126),
        "400": (280, 335, 380, 64, 60, 91, 99, 103, 104, 70, 105, 114, 118, 120),
        "500": (320, 380, 430, 52, 50, 81, 90, 94, 96, 58, 94, 104, 109, 111),
        "600": (335, 420, 475, 43, 43, 75, 84, 89, 92, 50, 86, 97, 103, 106),
        "750": (400, 475, 535, 34, 36, 68, 78, 84, 88, 42, 79, 91, 97, 102),
        "1000": (455, 545, 615, 26, 31, 62, 72, 78, 82, 36, 72, 84, 90, 95),
    },
    ("cu", "nonmagnetic"): {
        "14": (20, 20, 25, 6140, 5369, 4876, 4355, 3830, 3301, 6200, 5630, 5029, 4422, 3812),
        "12": (25, 25, 30, 3860, 3464, 3158, 2827, 2491, 2153, 4000, 3647, 3264, 2877, 2486),
        "10": (30, 35, 40, 2420, 2078, 1908, 1714, 1516, 1316, 2400, 2203, 1980, 1751, 1520),
        "8": (40, 50, 55, 1528, 1350, 1255, 1134, 1010, 882, 1560, 1449, 1310, 1166, 1019),
        "6": (55, 65, 75, 982, 848, 802, 731, 657, 579, 980, 926, 845, 758, 669),
        "4": (70, 85, 95, 616, 536, 519, 479, 435, 388, 620, 599, 553, 502, 448),
        "3": (85, 100, 110, 490, 433, 425, 395, 361, 324, 500, 490, 456, 417, 375),
        "2": (95, 115, 130, 388, 329, 330, 310, 286, 259, 380, 381, 358, 330, 300),
        "1": (110, 130, 150, 308, 259, 268, 255, 238, 219, 300, 310, 295, 275, 253),
        "1/0": (125, 150, 170, 244, 207, 220, 212, 199, 185, 240, 254, 244, 230, 214),
        "2/0": (145, 175, 195, 193, 173, 188, 183, 174, 163, 200, 217, 211, 201, 188),
        "3/0": (165, 200, 225, 153, 133, 151, 150, 145, 138, 154, 175, 173, 167, 159),
        "4/0": (195, 230, 260, 122, 107, 127, 128, 125, 121, 124, 147, 148, 145, 140),
        "250": (215, 255, 290, 103, 90, 112, 114, 113, 110, 104, 129, 132, 131, 128),
        "300": (240, 285, 320, 86, 76, 99, 103, 104, 102, 88, 114, 119, 120, 118),
        "350": (260, 310, 350, 73, 65, 89, 94, 95, 94, 76, 103, 108, 110, 109),
        "400": (280, 335, 380, 64, 57, 81, 87, 89, 89, 66, 94, 100, 103, 103),
        "500": (320, 380, 430, 52, 46, 71, 77, 80, 82, 54, 82, 90, 93, 94),
        "600": (335, 420, 475, 43, 39, 65, 72, 76, 77, 46, 75, 83, 87, 90),
        "750": (400, 475, 535, 34, 32, 58, 65, 70, 72, 38, 67, 76, 80, 83),
        "1000": (455, 545, 615, 26, 25, 51, 59, 63, 66, 30, 59, 68, 73, 77),
    },
    ("al", "steel"): {
        "12": (20, 20, 25, 6360, 5542, 5039, 4504, 3963, 3419, 6400, 5819, 5201, 4577, 3948),
        "10": (25, 30, 35, 4000, 3464, 3165, 2836, 2502, 2165, 4000, 3654, 3275, 2889, 2500),
        "8": (30, 40, 45, 2520, 2251, 2075, 1868, 1656, 1441, 2600, 2396, 2158, 1912, 1663),
        "6": (40, 50, 60, 1616, 1402, 1310, 1188, 1061, 930, 1620, 1513, 1372, 1225, 1074),
        "4": (55, 65, 75, 1016, 883, 840, 769, 692, 613, 1020, 970, 888, 799, 708),
        "3": (65, 75, 85, 796, 692, 668, 615, 557, 497, 800, 771, 710, 644, 574),
        "2": (75, 90, 100, 638, 554, 541, 502, 458, 411, 640, 625, 580, 529, 475),
        "1": (85, 100, 115, 506, 433, 432, 405, 373, 338, 500, 499, 468, 431, 391),
        "1/0": (100, 120, 135, 402, 346, 353, 334, 310, 284, 400, 407, 386, 358, 328),
        "2/0": (115, 135, 150, 318, 277, 290, 277, 260, 241, 320, 335, 320, 301, 278),
        "3/0": (130, 155, 175, 259, 225, 241, 234, 221, 207, 260, 279, 270, 256, 239),
        "4/0": (150, 180, 205, 200, 173, 194, 191, 184, 174, 200, 224, 221, 212, 201),
        "250": (170, 205, 230, 169, 148, 173, 173, 168, 161, 172, 200, 200, 194, 186),
        "300": (190, 230, 255, 141, 124, 150, 152, 150, 145, 144, 174, 176, 173, 168),
        "350": (210, 250, 280, 121, 109, 135, 139, 138, 134, 126, 156, 160, 159, 155),
        "400": (225, 270, 305, 106, 95, 122, 127, 127, 125, 110, 141, 146, 146, 144),
        "500": (260, 310, 350, 85, 77, 106, 112, 113, 113, 90, 122, 129, 131, 130),
        "600": (285, 340, 385, 71, 65, 95, 102, 105, 106, 76, 110, 118, 121, 122),
        "750": (320, 385, 435, 56, 53, 84, 92, 96, 98, 62, 97, 107, 111, 114),
        "1000": (375, 445, 500, 42, 43, 73, 82, 87, 89, 50, 85, 95, 100, 103),
    },
    ("al", "nonmagnetic"): {
        "12": (20, 20, 25, 6360, 5542, 5029, 4490, 3946, 3400, 6400, 5807, 5184, 4557, 3926),
        "10": (25, 30, 35, 4000, 3464, 3155, 2823, 2486, 2147, 4000, 3643, 3260, 2871, 2480),
        "8": (30, 40, 45, 2520, 2251, 2065, 1855, 1640, 1423, 2600, 2385, 2142, 1894, 1643),
        "6": (40, 50, 60, 1616, 1402, 1301, 1175, 1045, 912, 1620, 1502, 1357, 1206, 1053),
        "4": (55, 65, 75, 1016, 883, 831, 756, 677, 596, 1020, 959, 873, 782, 668),
        "3": (65, 75, 85, 796, 692, 659, 603, 543, 480, 800, 760, 696, 627, 555),
        "2": (75, 90, 100, 638, 554, 532, 490, 443, 394, 640, 615, 566, 512, 456),
        "1": (85, 100, 115, 506, 433, 424, 394, 360, 323, 500, 490, 455, 415, 373),
        "1/0": (100, 120, 135, 402, 346, 344, 322, 296, 268, 400, 398, 372, 342, 310),
        "2/0": (115, 135, 150, 318, 277, 281, 266, 247, 225, 320, 325, 307, 285, 260),
        "3/0": (130, 155, 175, 259, 225, 234, 223, 209, 193, 260, 270, 258, 241, 223),
        "4/0": (150, 180, 205, 200, 173, 186, 181, 171, 160, 200, 215, 209, 198, 185),
        "250": (170, 205, 230, 169, 147, 163, 160, 153, 145, 170, 188, 185, 177, 167),
        "300": (190, 230, 255, 141, 122, 141, 140, 136, 130, 142, 163, 162, 157, 150),
        "350": (210, 250, 280, 121, 105, 125, 125, 123, 118, 122, 144, 145, 142, 137),
        "400": (225, 270, 305, 106, 93, 114, 116, 114, 111, 108, 132, 134, 132, 128),
        "500": (260, 310, 350, 85, 74, 96, 100, 100, 98, 86, 111, 115, 115, 114),
        "600": (285, 340, 385, 71, 62, 85, 90, 91, 91, 72, 98, 104, 106, 105),
        "750": (320, 385, 435, 56, 50, 73, 79, 82, 82, 58, 85, 92, 94, 95),
        "1000": (375, 445, 500, 42, 39, 63, 70, 73, 75, 46, 73, 81, 85, 86),
    },
}

_PF_COLUMNS = (100, 90, 80, 70, 60)

VOLT_LOSS = {}
for (_mat, _cond), _rows in _VL_RAW.items():
    _dest = VOLT_LOSS.setdefault(_mat, {})[_cond] = {}
    for _size, _c in _rows.items():
        _dest[_size] = {
            "ampacity": (_c[0], _c[1], _c[2]),
            "dc": _c[3],
            "three_phase": dict(zip(_PF_COLUMNS, _c[4:9])),
            "single_phase": dict(zip(_PF_COLUMNS, _c[9:14])),
        }

# NEC 240.4(D) -- small-conductor overcurrent protection limits. The SPD tables
# mark these sizes with an asterisk. Keyed (material, size) -> max OCPD amps.
SMALL_CONDUCTOR_LIMIT = {
    ("cu", "14"): 15, ("cu", "12"): 20, ("cu", "10"): 30,
    ("al", "12"): 15, ("al", "10"): 25,
}

# --------------------------------------------------------------------------
# Ampacity correction / adjustment
# --------------------------------------------------------------------------
# NEC Table 310.15(B)(1) (2023) -- ambient temperature correction, 30 C base.
# (low_C, high_C) -> {60: f, 75: f, 90: f}; None where the NEC table has a dash.

AMBIENT_CORRECTION = [
    ((10, 15), {60: 1.29, 75: 1.20, 90: 1.15}),
    ((16, 20), {60: 1.22, 75: 1.15, 90: 1.12}),
    ((21, 25), {60: 1.15, 75: 1.11, 90: 1.08}),
    ((26, 30), {60: 1.00, 75: 1.00, 90: 1.00}),
    ((31, 35), {60: 0.91, 75: 0.94, 90: 0.96}),
    ((36, 40), {60: 0.82, 75: 0.88, 90: 0.91}),
    ((41, 45), {60: 0.71, 75: 0.82, 90: 0.87}),
    ((46, 50), {60: 0.58, 75: 0.75, 90: 0.82}),
    ((51, 55), {60: 0.41, 75: 0.67, 90: 0.76}),
    ((56, 60), {60: None, 75: 0.58, 90: 0.71}),
    ((61, 65), {60: None, 75: 0.47, 90: 0.65}),
    ((66, 70), {60: None, 75: 0.33, 90: 0.58}),
    ((71, 75), {60: None, 75: None, 90: 0.50}),
    ((76, 80), {60: None, 75: None, 90: 0.41}),
]

# NEC Table 310.15(C)(1) (2023) / 310.15(B)(3)(a) (2014) -- adjustment for more
# than three current-carrying conductors. (low, high) -> factor.
CCC_ADJUSTMENT = [
    ((4, 6), 0.80),
    ((7, 9), 0.70),
    ((10, 20), 0.50),
    ((21, 30), 0.45),
    ((31, 40), 0.40),
    ((41, 9999), 0.35),
]


def ambient_factor(ambient_c, temp_rating):
    """Return the NEC ambient correction factor, or raise if not permitted."""
    for (lo, hi), factors in AMBIENT_CORRECTION:
        if lo <= ambient_c <= hi:
            f = factors[temp_rating]
            if f is None:
                raise ValueError(
                    "NEC ambient correction table has no factor for %d C insulation "
                    "at %d C ambient -- that insulation cannot be used there"
                    % (temp_rating, ambient_c)
                )
            return f
    if ambient_c < 10:
        return AMBIENT_CORRECTION[0][1][temp_rating]
    raise ValueError("ambient temperature %d C is beyond the NEC table" % ambient_c)


def ccc_factor(count):
    """Return the NEC adjustment factor for `count` current-carrying conductors."""
    if count <= 3:
        return 1.0
    for (lo, hi), f in CCC_ADJUSTMENT:
        if lo <= count <= hi:
            return f
    raise ValueError("current-carrying conductor count %d out of range" % count)
