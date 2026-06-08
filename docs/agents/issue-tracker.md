# Issue tracker: Local Markdown

Issues and PRDs for this repo live as markdown files under `docs/`.

## Conventions

- PRDs: `docs/PRD-<slug>.md`
- Implementation issues: `docs/issues/<NNN>-<slug>.md`, numbered from `001`
- Each issue includes:
  - `## Type` — `AFK` (agent-ready code) or `HITL` (requires manual editor work)
  - `## Blocked by` — dependency links or `None`
  - `## Parent` — link to the PRD
  - `## What to build` — specification
  - `## Acceptance criteria` — checklist
- Triage state is recorded as a `Status:` line near the top of each issue file (see `triage-labels.md` for the role strings)
- Comments and conversation history append to the bottom of the file under a `## Comments` heading

## When a skill says "publish to the issue tracker"

Create a new file under `docs/issues/` (or a PRD under `docs/` if publishing a PRD).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.
