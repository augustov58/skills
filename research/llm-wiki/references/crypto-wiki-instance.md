# Crypto Wiki Instance

**Location:** `~/Obsidian Notes/Crypto Wiki/`
**Created:** 2026-04-18

## User Workflow
- Deep Research files (`~/Obsidian Notes/Deep Research/`) are **immutable sources** — wiki references but never modifies
- New sources (tweets, blogs, papers) go to `raw/` and enrich wiki pages
- Wiki builds structured knowledge ON TOP of existing notes
- Not yet populated with entity pages

## Schema Notes
- External sources use relative paths: `../Deep Research/`, `../Crypto Research/`
- Symlink fallback for Obsidian compatibility: `vault-links/Deep Research/` → `../Deep Research/`
- 12-category tag taxonomy specific to crypto
- Scoring rubric for project evaluation (12 categories)

## Gateway Note
- opencode-go provider returning HTTP 401 intermittently, causing gateway fallback to GLM-4.7
- Gateway restart (`hermes gateway restart`) resolved it temporarily
- Model config: `~/.hermes/config.yaml` or `.claude.json`
