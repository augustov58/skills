# skills

A collection of Claude Code skills.

## Contents

| Skill | Category | Description |
|-------|----------|-------------|
| [llm-wiki](research/llm-wiki/) | research | Karpathy's LLM Wiki — build and maintain a persistent, interlinked markdown knowledge base. Ingest sources, query compiled knowledge, and lint for consistency. |
| [generator-sizing](electrical/generator-sizing/) | electrical | Size emergency, standby, or optional generators (gensets) per NEC 700/701/702 and NFPA 110 — code classification, the four-constraint method (running kW, alternator kVA, voltage dip, block load), motor-start analysis, and fuel-tank sizing. Intake-driven, with a deterministic sizing script. |
| [transformer-sizing-design](electrical/transformer-sizing-design/) | electrical | Size and design a complete dry-type transformer installation per NEC 2023 — kVA selection, OCPD↔conductor coupling (Table 450.3(B) / 240.4), panel-bus cap, secondary tap rules, SDS grounding, and installation clearances. Intake-driven, with a deterministic sizing calculator and a one-line/riser SVG generator. |
| [write-a-skill](productivity/write-a-skill/) | productivity | Create new agent skills with proper structure, progressive disclosure, and bundled resources. Use when user wants to create, write, or build a new skill. |

## Layout

Skills are organized by category. Each skill is a directory containing a
`SKILL.md` (with YAML frontmatter defining `name` and `description`) plus any
supporting `references/`.

## Installing a skill

Copy a skill directory into your Claude Code skills path, e.g.:

```bash
cp -r research/llm-wiki ~/.claude/skills/
```
