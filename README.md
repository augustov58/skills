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
| [llm-wiki](skills/research/llm-wiki/) | research | Build and maintain a persistent, interlinked markdown knowledge base. Ingest sources, query compiled knowledge, and lint for consistency. Based on [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c1b7b1f6c58). |
| [write-a-skill](skills/productivity/write-a-skill/) | productivity | Create new agent skills with proper structure, progressive disclosure, and bundled resources. Use when you want to create, write, or build a new skill. |

The two electrical skills bundle Python helper scripts that run on the
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

> **On the code tables.** These scripts encode NEC 2023 tables and cite the
> governing section next to every number, but they produce a *first-pass*
> design: conductor sizes skip 310.15 derating, voltage drop, and parallel
> sets. Verify against your own copy of NFPA 70 before anything is issued or
> stamped. The scripts print an `ASSUMPTIONS` and a `FLAGS / VERIFY` block for
> exactly this reason — read them.

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
