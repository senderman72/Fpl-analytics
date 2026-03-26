# FPL Analytics Platform — Build Plan

## Overview

Build a full-stack FPL analytics platform incrementally across 4 phases.
Each phase ends with something working end-to-end.

---

## Phase 1 — FPL Data Foundation

### Step 0: Project Scaffolding ✅

- [x] Git init, .gitignore, .env.example, .python-version
- [x] Docker Compose (Postgres 16 + Redis 7)
- [x] backend/pyproject.toml with all dependencies (uv)
- [x] FastAPI app factory with /health endpoint
- [x] Async SQLAlchemy engine + session + Base
- [x] Redis client, rate limiter stub
- [x] Celery app + worker/beat stubs
- [x] Alembic initialized (async template, reads config from Settings)
- [x] Pre-commit config (Ruff, trailing whitespace)
- [x] Smoke test (GET /health)

### Step 1: SQLAlchemy Models + First Migration ✅

All 8 models defined in `backend/app/models/` with indexes from the tech plan:

- [x] `team.py` — teams (20 PL teams with FPL strength ratings)
- [x] `player.py` — players (price, status, position, Understat ID)
- [x] `gameweek.py` — gameweeks (GW 1–38, deadlines, DGW/BGW flags)
- [x] `fixture.py` — fixtures (FDR, scores, kickoff times) + `idx_fixtures_gw`
- [x] `player_gw_stats.py` — player_gw_stats (points, BPS, ICT) + `idx_pgw_player_gw`, `idx_pgw_gw`
- [x] `player_gw_xg.py` — player_gw_xg (xG/xA/xGI from Understat) + `idx_xg_player_gw`
- [x] `player_prices.py` — player_prices (daily price log) + `idx_prices_player`
- [x] `player_form_cache.py` — player_form_cache (rolling 4/6/10 GW stats) + `idx_form_player`
- [x] `alembic/env.py` updated to import all models
- [x] `models/__init__.py` re-exports all models

**Remaining**: Run `uv run alembic revision --autogenerate -m "add core models"` + `uv run alembic upgrade head` once Docker (Postgres) is running.

### Step 2: FPL Bootstrap Ingestion ✅

- [x] `app/services/fpl_client.py` — async httpx client (fetch_bootstrap, fetch_fixtures, fetch_live_gw, fetch_player_summary)
- [x] `worker/normaliser.py` — normalise_team, normalise_player, normalise_gameweek (maps FPL API fields to DB columns)
- [x] `worker/tasks.py::sync_bootstrap` — fetches /bootstrap-static/, upserts teams + players + gameweeks via INSERT ON CONFLICT
- [x] `app/core/database.py` — added sync engine + session factory for Celery workers (psycopg2)
- [x] Tested: 20 teams, 825 players, 38 gameweeks ingested from live FPL API

### Step 3: Fixture Ingestion + Player History + Price Snapshots ✅

- [x] `sync_fixtures` — 380 fixtures ingested, DGW/BGW flags auto-detected
- [x] `sync_player_history` — 22,792 player GW stat rows (rate-limited 1 req/s, active players only)
- [x] `sync_price_snapshot` — 825 daily price snapshots
- [x] `app/core/rate_limiter.py` — reusable rate limiters (FPL 1/s, Understat 1/s, FBref 1/3s)
- [x] Unique constraints added for idempotent upserts on `player_gw_stats` and `player_prices`
- [x] All tasks verified against live FPL API + local Postgres

---

## Phase 2 — Understat xG Pipeline ✅

**Note:** Understat no longer serves per-match xG via scraping. Adapted to use their internal POST API for season-level stats, which gives all the xG metrics needed for the decision endpoints.

### Steps 5-7: Understat Client + Matching + Form Cache ✅

- [x] `app/services/understat_client.py` — POST API client for `/main/getPlayersStats/`
- [x] `app/models/player_gw_xg.py` → renamed to `PlayerSeasonXG` (season-level xG per player)
- [x] `worker/normaliser.py::match_understat_to_fpl` — fuzzy matching with rapidfuzz (partial_ratio, multi-team support)
- [x] `worker/normaliser.py::normalise_understat_season` — maps Understat data to DB columns
- [x] `UNDERSTAT_TEAM_MAP` — maps Understat team names to FPL short names
- [x] `sync_understat` task — 465 players matched, understat_id stored on players table
- [x] `recompute_form_cache` task — 2,352 rows (784 players × 3 windows: 4/6/10 GW)
- [x] Season xG/xA/npxG/xGChain/xGBuildup stored, per-90 rates computed in form cache

---

## Phase 3 — FastAPI + Decision Endpoints ✅

### Steps 8-10: All Endpoints Implemented ✅

**Schemas** (`app/schemas/`):
- [x] `common.py` — `APIResponse[T]` envelope with data + meta
- [x] `player.py` — PlayerSummary, PlayerDetail, PlayerGWHistory, PlayerFixture
- [x] `gameweek.py` — GameweekOut, FixtureOut
- [x] `decision.py` — BuyCandidate, CaptainPick, ChipAdvice, DifferentialPick, PredictionOut

**Player endpoints** (`app/api/players.py`):
- [x] `GET /players` — filterable by position, team, search; sortable by form/cost/xGI/PPG
- [x] `GET /players/{id}` — full profile with form cache + season xG from Understat
- [x] `GET /players/{id}/history` — GW-by-GW stats
- [x] `GET /players/{id}/fixtures` — upcoming fixtures with FDR and DGW flags

**Gameweek/fixture endpoints** (`app/api/gameweeks.py`):
- [x] `GET /gameweeks` — all 38 GWs with DGW/BGW flags
- [x] `GET /fixtures` — filterable by GW, team, finished status

**Decision endpoints** (`app/api/decisions.py`):
- [x] `GET /decisions/buys` — ranked by composite (xGI/90 40%, PPM 30%, form 30%, FDR penalty)
- [x] `GET /decisions/captains` — ranked by ceiling 40%, form 30%, BPS 20%, home/DGW bonus
- [x] `GET /decisions/chips` — DGW/BGW calendar with chip recommendations
- [x] `GET /decisions/differentials` — low-ownership (<5%) high-xGI players

**Predictions** (`app/api/predictions.py` + `app/services/points_model.py`):
- [x] `GET /predictions/gw/{gw}` — ridge regression, 10 features, trained on 22k+ GW samples
- [x] Model auto-trains on first request, R² reported in logs

### Steps 11-12: Live GW + Caching (deferred to Phase 4)

- [ ] `sync_live_gw` Celery task + WebSocket endpoint
- [ ] Redis caching with TTLs
- [ ] Integration tests

---

## Phase 4 — Frontend (Astro + SolidJS) ✅

### Steps 13-14: Astro Scaffold + Core Pages ✅

**Stack**: Astro 6 SSR + SolidJS islands + UnoCSS + @astrojs/node adapter

**API layer** (`src/api/`):
- [x] `client.ts` — generic `get<T>()` and `post<T>()` with server/client URL switching
- [x] `players.ts`, `gameweeks.ts`, `decisions.ts`, `predictions.ts` — typed endpoint wrappers
- [x] `src/pages/api/[...path].ts` — catch-all proxy (hides API_URL from browser)

**Pages**:
- [x] `/` — Dashboard: current GW, next deadline, season progress bar, top 5 captain picks, top 5 form players
- [x] `/players` — SolidJS island with position filter, search, sort (form/xGI/price/mins)
- [x] `/players/:id` — Player profile: season stats, form, Understat xG, FDR fixture strip, GW history table
- [x] `/decisions/buy-sell` — Top 30 ranked buy candidates with composite scoring
- [x] `/decisions/captain` — Captain rankings with ceiling, BPS, home/DGW context
- [x] `/decisions/chips` — Visual DGW/BGW calendar with chip recommendations
- [x] `/predictions` — Ridge regression predicted points for next GW

**Shared**: `src/lib/types.ts` (all TypeScript types), FPL-themed dark UI with UnoCSS

### Remaining (future)

- [ ] Live GW tracker (WebSocket + SolidJS `client:only` island)
- [ ] ApexCharts visualisations (xGI timeline, ceiling chart, price sparklines)
- [ ] Deploy to Railway (backend) + Vercel (frontend)
- [ ] Sentry error tracking
- [ ] README with architecture diagram
