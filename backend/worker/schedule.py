"""Celery Beat schedule — automatic data refresh.

Frequency tiers (designed to stay under FPL API rate limits):
- Every 5 min: bootstrap (1 API call — players, teams, GWs, statuses, prices)
- Every 5 min: fixtures (1 API call — scores, DGW/BGW flags)
- Every 30 min: transfer velocity (1 API call — reuses bootstrap data)
- Every 6 hours: understat xG (1 external call to understat.com)
- Daily: price snapshot, player history (~500 calls, rate-limited to 1/s)
- Daily: form cache recompute, predictions (DB only, no API calls)

Total API calls: ~600/day to FPL (576 from 5-min bootstrap
+fixtures, ~500 from daily history).
FPL rate limit: ~1 req/s = 86,400/day — we use <1%.

Live scores: fetched on-demand by /live/{gw_id} endpoint (every 60s).
"""

from celery.schedules import crontab

beat_schedule = {
    # ── Every 5 minutes — always fresh ──
    "sync-bootstrap": {
        "task": "worker.tasks.sync_bootstrap",
        "schedule": crontab(minute="*/5"),
    },
    "sync-fixtures": {
        "task": "worker.tasks.sync_fixtures",
        "schedule": crontab(minute="2,7,12,17,22,27,32,37,42,47,52,57"),
    },
    # ── Every 30 minutes — transfer velocity ──
    "sync-transfer-counts": {
        "task": "worker.tasks.sync_transfer_counts",
        "schedule": crontab(minute="5,35"),
    },
    # ── Every 6 hours — understat xG ──
    "sync-understat": {
        "task": "worker.tasks.sync_understat",
        "schedule": crontab(minute=20, hour="0,6,12,18"),
    },
    # ── Daily at 03:00 UTC — snapshots + heavy compute ──
    "sync-price-snapshot": {
        "task": "worker.tasks.sync_price_snapshot",
        "schedule": crontab(hour=3, minute=5),
    },
    "sync-player-history": {
        "task": "worker.tasks.sync_player_history",
        "schedule": crontab(hour=4, minute=5),
    },
    "recompute-form-cache": {
        "task": "worker.tasks.recompute_form_cache",
        "schedule": crontab(hour=4, minute=45),
    },
    # ── Daily at 05:00 UTC — predictions ──
    "backfill-actuals": {
        "task": "worker.tasks.backfill_actuals",
        "schedule": crontab(hour=5, minute=0),
    },
    "run-predictions": {
        "task": "worker.tasks.run_predictions",
        "schedule": crontab(hour=5, minute=15),
    },
}
