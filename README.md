# skills

A collection of Claude Code skills.

## Contents

| Skill | Category | Description |
|-------|----------|-------------|
| [llm-wiki](research/llm-wiki/) | research | Karpathy's LLM Wiki — build and maintain a persistent, interlinked markdown knowledge base. Ingest sources, query compiled knowledge, and lint for consistency. |

## Layout

Skills are organized by category. Each skill is a directory containing a
`SKILL.md` (with YAML frontmatter defining `name` and `description`) plus any
supporting `references/`.

## Installing a skill

Copy a skill directory into your Claude Code skills path, e.g.:

```bash
cp -r research/llm-wiki ~/.claude/skills/
```
