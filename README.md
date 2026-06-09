# skills

A collection of Claude Code skills.

## Contents

| Skill | Category | Description |
|-------|----------|-------------|
| [llm-wiki](research/llm-wiki/) | research | Karpathy's LLM Wiki — build and maintain a persistent, interlinked markdown knowledge base. Ingest sources, query compiled knowledge, and lint for consistency. |
| [transformer-sizing-design](electrical/transformer-sizing-design/) | electrical | Size and design a complete dry-type transformer installation per NEC 2023 — kVA selection, OCPD (Table 450.3(B)), secondary tap rules, SDS grounding, and installation clearances. Intake-driven, with a deterministic sizing calculator. |
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
