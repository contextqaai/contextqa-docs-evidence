# Hosted review console — validation receipt, 2026-11-19

Scope: local checks of the React console, hosted API and repository agent after the changes listed below. These checks ran in an isolated Linux validation environment with a copy of the working tree, not on the operator's workstation. No remote CI, deployment, push, ContextQA execution or paid model call happened.

## Changes covered

- React test fixture now supplies the full manifest (`environment`, `application_url`, `instructions`, `sections`). No type cast.
- Review context panel: the global `aside` sidebar rule also matched the panel's `<aside>`, so the panel was fixed over the sidebar on desktop and tablet and hidden on mobile. Sidebar rules are now scoped to `.sidebar`, and the conflicting panel rules are consolidated (sections own their padding; three columns at ≤1200 px; one column at ≤720 px).
- Content health: raw audit JSON is replaced by grouped results (missing coverage, stale articles, broken relative links), counts, scope notes, retry, and actions that open intake with the affected path filled in. Contributors do not see the actions.
- Agent proposal questions use the review ingestion limits (≤200 questions, ≤500 characters each). Before, a 501–1,000 character question passed `validate` and then failed at `submit`.
- `.gitignore` keeps `.env.hosted.example` (it contains placeholders only).
- Dockerfile: health check, `--app-dir /app`, unbuffered output. Compose: `restart: unless-stopped`, `DEV_SUBJECT`, and an opt-in `provision-kan` profile that mounts `examples/kan-pr15` read-only instead of baking it into the image.
- CI workflow: new `web` (test, build, audit) and `hosted` (PostgreSQL 17 service, Python 3.12) jobs are **proposed, not applied**. Remote tools cannot write `.github/workflows/`, so the full proposed file is at `outputs/proposed-ci/test.yml` in the workspace. Copy it over `.github/workflows/test.yml` after review.
- Favicon link (removed the only browser console error).

## Results

| Check | Result |
|---|---|
| `python3 -m unittest discover -s tests` (Python 3.13) | 131 passed (1 new agent bounds test) |
| `npm run test:ai` | 10 passed |
| `npm run test:ui` (legacy UI helpers) | 4 passed |
| `npm test --prefix apps/web` | 6 passed (3 new: health groups, contributor view, intake prefill) |
| `npm run build --prefix apps/web` | passed |
| `npm audit --prefix apps/web` | 0 vulnerabilities |
| Hosted suite, real PostgreSQL 16, Python 3.12 from `requirements-hosted.lock` | 11 passed |
| Image-equivalent layout (clean 3.12 venv, `/app`-style tree, `--app-dir`) | migrate ×2 idempotent, provision OK, health-check command OK, unauthenticated API 401, production refuses development auth |
| Browser (Chrome, development auth, provisioned Kan workspace) | inbox, review and health at 1440, 1024 and 390 px; no console errors; article import from a health finding reduced missing coverage 3 → 2 and showed the new article's broken links |

## Not verified

- `docker build` / `docker compose up`: Docker Hub was blocked by the validation environment's network allowlist.
- Real OIDC provider, remote CI, deployed instance, Kan base/head commit fetch, fresh ContextQA run, paid drafting.
- The operator's own local PostgreSQL runtime and the app on `127.0.0.1:8080` were not reached from this session.
