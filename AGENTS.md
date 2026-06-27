# Agent Coordination Notes

This repo is a hackathon prototype for the Cyanite audio-first recommendation workflow. Before changing behavior, read:

- `PRD-night.md` for the current product workflow.
- `docs/team-responsibilities.md` for responsibility boundaries.

## Responsibility Boundary Warning

If a requested change touches any of these areas, warn the user that it may overlap with the Prompt / Refill Ranking / Explainability owner before implementing broad changes:

- LLM prompt templates that compile the whiteboard context and user profile into the free-text query sent to Cyanite search.
- Candidate refill ranking after like / dislike feedback, including similar-by-ID expansion and prompt-aligned reordering.
- Explanation prompt templates that combine liked-track Cyanite tags, the current whiteboard prompt context, and the user's natural-language taste profile.

Small integration hooks are fine, but avoid redesigning those owned components without coordination.

## Git / Commit Workflow

Use small, feature-level commits. After finishing each small feature or coherent documentation update, create a commit instead of accumulating unrelated work.

Commit messages should use:

1. A short, simple summary line.
2. A more detailed explanatory paragraph in the commit body when the change needs context.

Before committing:

1. Check whether teammates have pushed new work.
2. Pull the latest `origin/main` and rebase or otherwise integrate it before creating the local commit.
3. If any conflict appears, stop and ask the project owner to resolve or decide the conflict strategy. Do not guess or silently choose one side.
4. After the conflict is resolved, continue with the commit.

Do not force-push or rewrite shared history unless the project owner explicitly asks for it.
