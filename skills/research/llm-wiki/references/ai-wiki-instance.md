# AI Wiki Instance

**Location:** `~/Obsidian Notes/AI Wiki/`
**Created:** 2026-04-20

## User Workflow
- YouTube Scrolls (`~/Obsidian Notes/YouTube Scrolls/`) are **immutable sources** — wiki references but never modifies
- AI Reads & Notes (`~/Obsidian Notes/AI Reads & Notes/`) are **immutable sources** — wiki references via `../AI Reads & Notes/...`
- Deep Research (`~/Obsidian Notes/Deep Research/`), when AI-relevant, is also an immutable source
- External papers/articles go to `raw/papers/` or `raw/articles/` (local copy, so the wiki stays useful if the original moves)
- No scoring rubric (unlike Crypto Wiki) — AI is exploratory, not investment-evaluated

## Schema Notes
- External vault sources use relative paths: `../YouTube Scrolls/`, `../AI Reads & Notes/`, `../Deep Research/`
- Tag taxonomy has 6 groups (~30 tags): Artifacts, People & Orgs, Techniques, Infrastructure, Meta
- Frontmatter supports optional `supersedes` / `supersededBy` / `contradictions` fields for lifecycle management
- `sources.md` is a flat index of every ingested source, grouped by type — update on every ingest

## Wiki-Specific Lint Extensions
Beyond the skill's 9 default checks, also verify:
- **Sources-index drift** — `sources.md` matches what's actually cited across pages
- **Supersession back-references** are bidirectional
- **Source files on disk** — `raw/` and `../` paths exist (skip `https://`)

## Relationship to CLAUDE.md (L1/L2)
Vault-root `CLAUDE.md` is L1 (always loaded). This wiki is L2 (on-demand). The skill consults `index.md` and `sources.md` at orientation rather than loading all pages upfront.

## Current State (as of 2026-04-21)
- 19 wiki pages (9 entities, 10 concepts)
- 12 sources ingested (9 papers, 2 YouTube scrolls, 1 URL collection)
- Dominant topic: RAG. Entity cluster: Lewis 2020 (original), DPR, REALM, RETRO (foundations); Self-RAG, CRAG, RAPTOR, FLARE (technique papers); Gao 2023 (survey). Concept cluster: re-ranking, agentic-rag, contextual-retrieval, self-rag, hyde, crag, hierarchical-rag, query-transformation, flare, rag (hub).

## Ingest Tooling Note
Prefer the `/tmp/arxiv_to_md.py` + `/tmp/rag-ingest-venv/` approach for arXiv papers — WebFetch summarizes via its underlying small model, producing truncated captures. The script uses curl + BeautifulSoup + markdownify, tries `arxiv.org/html/<id>` first and falls back to `ar5iv.labs.arxiv.org/html/<id>`, picks whichever returned more content. Saves as clean markdown to `raw/papers/`.
