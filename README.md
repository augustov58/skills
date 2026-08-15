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
