# skills

Agent skills for Claude Code and other coding agents — with a focus on
electrical engineering design work.

## Install

```bash
npx skills@latest add augustov58/skills
```

This opens an interactive menu, lets you pick which skills you want, and
installs them for whichever agents you select. It works with Claude Code,
Codex, Cursor, opencode, and others.

Install a specific skill without the menu:

```bash
npx skills@latest add augustov58/skills --skill generator-sizing
```

Install for your user account instead of the current project:

```bash
npx skills@latest add augustov58/skills --global
```

Later, to update or remove:

```bash
npx skills update
npx skills remove --skill generator-sizing
```

## Install manually

The installer is a convenience, not a requirement — a skill is just a folder
with a `SKILL.md` in it. To install by hand, clone and copy the folders you
want:

```bash
git clone https://github.com/augustov58/skills.git
cd skills
cp -r skills/electrical/generator-sizing ~/.claude/skills/
```

Copy into `~/.claude/skills/` to make a skill available everywhere, or into
`.claude/skills/` inside a project to scope it to that project. Restart your
agent afterwards so it picks up the new skill.

Other agents read from their own directories — `~/.codex/skills/`,
`~/.cursor/skills/`, `~/.config/opencode/skills/`. The folder you copy is
identical in every case.

## Skills

| Skill | Category | Description |
|-------|----------|-------------|
| [generator-sizing](skills/electrical/generator-sizing/) | electrical | Size emergency, standby, or optional generators (gensets) per NEC 700/701/702 and NFPA 110 — code classification, the four-constraint method (running kW, alternator kVA, voltage dip, block load), motor-start analysis, and fuel-tank sizing. Intake-driven, with a deterministic sizing script. |
| [transformer-sizing-design](skills/electrical/transformer-sizing-design/) | electrical | Size and design a complete dry-type transformer installation per NEC 2023 — kVA selection, OCPD↔conductor coupling (Table 450.3(B) / 240.4), panel-bus cap, secondary tap rules, SDS grounding, and installation clearances. Intake-driven, with a deterministic sizing calculator and a one-line/riser SVG generator. |
| [short-circuit-voltage-drop](skills/electrical/short-circuit-voltage-drop/) | electrical | Available fault current point-to-point (Bussmann/Eaton SPD method) and steady-state voltage drop — interrupting-rating checks (110.9), 110.24 field marking, 240.86 series ratings, and volt-loss wire selection with the ampacity check built in. Intake-driven, with a deterministic calculator and a regression harness that reproduces the handbook's own printed examples. |
| [llm-wiki](skills/research/llm-wiki/) | research | Build and maintain a persistent, interlinked markdown knowledge base. Ingest sources, query compiled knowledge, and lint for consistency. Based on [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c1b7b1f6c58). |
| [write-a-skill](skills/productivity/write-a-skill/) | productivity | Create new agent skills with proper structure, progressive disclosure, and bundled resources. Use when you want to create, write, or build a new skill. |

The three electrical skills bundle Python helper scripts that run on the
standard library alone — no `pip install` needed.

## Calculator flags

The skills drive their scripts for you — you don't normally type these. They're
documented because each one changes a **code outcome**, so if you run the
calculator by hand, or you're checking a number the agent produced, these are
the switches that moved it. `--help` lists the full set.

### `size_transformer.py`

Sizing basis — pick exactly one:

| Flag | Meaning |
|------|---------|
| `--load-kva 65` | demand load in kVA |
| `--load-kw 60 --pf 0.9` | demand in kW; PF is asked for, never assumed silently |
| `--load-amps 180` | a panel total, interpreted at the secondary voltage |
| `--kva 75` | a known transformer size — skips selection |

Grounding and bonding:

| Flag | Default | Meaning |
|------|---------|---------|
| `--sds auto\|yes\|no` | `auto` | Separately derived system (250.30). `auto` infers from the winding connection. A Y-Y with a factory H0-X0 neutral link is **not** an SDS — pass `no`. |
| `--electrode rod\|plate\|ufer\|ring\|water\|steel` | *unspecified* | Applies the 250.66(A)/(B)/(C) caps. A 2 AWG table GEC drops to 6 AWG on a rod, 4 AWG on a Ufer. Default applies **no cap** and shows the full table value. |
| `--ring-size "2 AWG"` | — | Required by 250.66(C) when `--electrode ring`. |
| `--egc-baseline load\|ocpd` | `load` | Baseline for the 250.122(B) proportional EGC increase. `load` is the conservative reading; `ocpd` treats an OCPD-driven upsize as no increase. The 2020/2023 text deleted the baseline phrase and the sources genuinely split — the report says which position produced the number. |

Protection and conductors:

| Flag | Default | Meaning |
|------|---------|---------|
| `--secondary-ocpd yes\|no` | `yes` | With `no`, the secondary is supply-side its whole length and carries a bonding jumper per 250.102(C), not a 250.122 EGC. |
| `--primary-basis min\|inrush\|max` | `min` | `min` = 125% of primary FLA. Table 450.3(B) raises the ceiling to 250% when secondary protection exists, but that's a maximum, not a target — going there forces the primary conductor up to match (240.4) for no benefit unless you have real inrush trips. |
| `--panel-bus 225` | — | Caps the secondary OCPD at the panel bus rating (408.36). |
| `--sec-length 8` | — | Transformer-to-first-OCPD run in feet; selects the 240.21(C) tap rule. |
| `--conductor cu\|al` | `cu` | Conductor material. |
| `--term-temp auto\|60\|75` | `auto` | 110.14(C): 60 °C column at or below 100 A, 75 °C above. |
| `--format report\|json` | `report` | `json` feeds `draw_riser.py`. |

```bash
python3 size_transformer.py --load-kva 65 --primary-v 480 --secondary-v 208 \
  --secondary-ocpd yes --panel-bus 225 --spare 0 --sec-length 8 --electrode ufer
```

### `size_generator.py`

No flags — it takes a JSON load list, or `--example` to write a starter file.

```bash
python3 size_generator.py --example
python3 size_generator.py load_list.json
```

Tunables go in the JSON `params` block: `gen_pf`, `dip_target_pct`,
`altitude_ft`, `ambient_c`, `harmonic_load_fraction`, `spare_fraction`. A
`dip_target_pct` that isn't a tabulated value snaps to the next **stricter**
row and says so, rather than silently using a looser planning factor.

### `short_circuit.py`

Source — pick exactly one:

| Flag | Meaning |
|------|---------|
| `--kva 1500 --percent-z 3.5` | a transformer. `--percent-z` should come off the **nameplate** — omit it and the script falls back to SPD Table 1 and says so. Fault current is *inversely* proportional to %Z, and Table 1 spans 1.0%–4.0%, so the fallback can be off by a factor of three. |
| `--available-fault 45000` | a known fault current from the utility letter or an upstream study. |
| `--system system.json` | a multi-point cascade down a one-line. Use this whenever there is more than one fault point — doing them as separate runs means re-typing the upstream current by hand. |
| `--example` | writes `example_system.json` into the current directory and runs it. |

The switches that move the answer:

| Flag | Default | Meaning |
|------|---------|---------|
| `--z-tolerance high\|nameplate\|low` | `high` | `high` = %Z × 0.9, the **maximum** fault (SPD Note 2, UL 1561 ±10% tolerance) — what interrupting and withstand ratings are checked against. `low` = %Z × 1.1, the **minimum** fault — what ground-fault pickup and series ratings need. These are different questions; run both when a series rating is in play. |
| `--conduit steel\|nonmagnetic` | `steel` | Steel is magnetic and raises both AC resistance and reactance. 500 kcmil Cu at 600 V is C=22,185 in steel and C=26,706 in PVC — a 20% swing, and the most common quiet error. |
| `--arrangement single\|cable` | `single` | Three single conductors in a raceway vs a three-conductor cable. Separate columns in SPD Table 4. |
| `--per-phase 6` | `1` | Parallel sets. Multiplies C. |
| `--fault-type 3phase\|ll\|ln` | `3phase` | The 1φ forms use `2 × L` where the 3φ form uses `1.732 × L` — a 15% swing. `ln` is the center-tapped single-phase procedure only; the script refuses it on a 3φ wye rather than inventing a method. |
| `--motor-fla 1804` | none | SPD Step 6A, `4 × motor FLA`, added at **every** fault point undiminished — the motors sit downstream of the run. It stops at a transformer, which is a different voltage. |
| `--device-air 65000` | — | Checks the device's interrupting rating against the available fault (110.9). |

```bash
python3 short_circuit.py --kva 1500 --percent-z 3.5 --secondary-v 480 \
  --length-ft 25 --size 500 --per-phase 6 --motor-fla 1804 --device-air 65000
```

### `voltage_drop.py`

| Flag | Default | Meaning |
|------|---------|---------|
| `--size 6` / `--select` | — | Evaluate one conductor, or walk the table from the smallest up and return the first that satisfies **both** the drop limit and the derated ampacity. |
| `--limit-percent 3` | `3.0` | The 210.19(A)/215.2(A) Informational Note value, which is **advisory, not enforceable**. Use `1.5` for 647.4(D) sensitive electronic equipment, which *is* mandatory. |
| `--upstream-percent 1.8 --total-limit-percent 5` | `0` / `5.0` | Charges drop already spent upstream against a combined feeder + branch budget. |
| `--pf 0.9` | `0.9` | Load power factor, 0.60–1.00. Values between the tabulated 100/90/80/70/60% columns are interpolated and the interpolation is stated. Below 0.60 is off the table and is rejected rather than extrapolated. |
| `--ambient-c 45 --ccc 6` | `30` / `3` | 310.15(B)(1) ambient correction and 310.15(C)(1) conductor-count adjustment. |
| `--term-temp 60\|75` | `75` | 110.14(C). Derating starts from the conductor's own insulation rating and is *then* capped by the termination column — doing it the other way under-sizes the conductor. |
| `--ocpd 25` | — | Checks the 240.4(D) small-conductor cap. |

```bash
python3 voltage_drop.py --amps 200 --length-ft 300 --voltage 208 --conductor al \
  --select --limit-percent 3 --ambient-c 45 --ccc 6
```

### `verify_spd.py`

The SPD tables are roughly 1,800 hand-transcribed numbers, and a single wrong
one produces an answer that looks entirely plausible. This harness reproduces
every worked example the handbook prints — 40 assertions, worst deviation
0.22%, which is the handbook's own display rounding.

```bash
python3 verify_spd.py            # exits 1 on any failure
python3 verify_spd.py --verbose  # show the arithmetic for passing cases too
```

Run it after any edit to `spd_tables.py`. A failure means the table disagrees
with the printed handbook — fix the table, not the tolerance.

> **On the code tables.** These scripts encode NEC 2023 tables and cite the
> governing section next to every number, but they produce a *first-pass*
> design: the sizing scripts' conductor sizes skip 310.15 derating, voltage
> drop, and parallel sets. `short-circuit-voltage-drop` additionally works from
> the Bussmann/Eaton SPD 2014 handbook, which prints the pre-2020 Article 310
> numbering, and point-to-point is a first-pass hand method — not an arc-flash
> study and not a substitute for a modeled one. Verify against your own copy of
> NFPA 70 before anything is issued or stamped. The scripts print an
> `ASSUMPTIONS` and a `FLAGS / VERIFY` block for exactly this reason — read
> them.

## Layout

```
skills/
└── <category>/
    └── <skill-name>/
        ├── SKILL.md        # required: YAML frontmatter with name + description
        ├── references/     # optional: material the skill reads on demand
        └── scripts/        # optional: deterministic helpers the skill runs
```

Everything lives under the top-level `skills/` directory. That placement is
what the installer looks for: it searches a fixed set of known folders, and
`skills/` is one of them, searched three levels deep. Categories placed at the
repository root are only found by a fallback that stops firing as soon as any
skill is discovered through the normal path.

Two rules follow from that, for anyone adding to this repo:

- Never put a `SKILL.md` at the repository root. It short-circuits discovery
  and hides everything else.
- Keep skills at `skills/<category>/<name>/SKILL.md`.

## License

MIT — see [LICENSE](LICENSE). The `llm-wiki` skill implements a pattern
described by [Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c1b7b1f6c58);
the implementation here is original.
