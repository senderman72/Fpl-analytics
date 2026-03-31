"""Celery Beat schedule — automatic data refresh.

Live scores: NOT scheduled — fetched on-demand by the /live/{gw_id} endpoint
when the frontend polls during active matches (every 60s).

Daily (2 API calls):
- sync_bootstrap: prices, ownership, transfers, statuses (1 API call)
- sync_price_snapshot: copies prices to history table (0 API calls)

Weekly on Tuesday 04:00 UTC (after Monday GWs finish):
- sync_fixtures: scores, DGW/BGW flags (1 API call)
- sync_player_history: GW stats for all players (~500 calls at 1/s)
- sync_understat: season xG/xA (1 API call)
- recompute_form_cache: rolling form windows (0 API calls, DB only)

Ridge regression model retrains lazily after form cache updates.
"""

from celery.schedules import crontab

beat_schedule = {
    # ── Daily at 03:00 UTC ──
    "sync-bootstrap": {
        "task": "worker.tasks.sync_bootstrap",
        "schedule": crontab(hour=3, minute=0),
    },
    "sync-price-snapshot": {
        "task": "worker.tasks.sync_price_snapshot",
        "schedule": crontab(hour=3, minute=5),
    },
    "sync-transfer-counts": {
        "task": "worker.tasks.sync_transfer_counts",
        "schedule": crontab(hour="6,8,10,12,14,16,18,20,22", minute=15),
    },
    # ── Weekly on Tuesday at 04:00 UTC ──
    "sync-fixtures": {
        "task": "worker.tasks.sync_fixtures",
        "schedule": crontab(hour=4, minute=0, day_of_week=2),
    },
    "sync-player-history": {
        "task": "worker.tasks.sync_player_history",
        "schedule": crontab(hour=4, minute=5, day_of_week=2),
    },
    "sync-understat": {
        "task": "worker.tasks.sync_understat",
        "schedule": crontab(hour=4, minute=30, day_of_week=2),
    },
    "recompute-form-cache": {
        "task": "worker.tasks.recompute_form_cache",
        "schedule": crontab(hour=4, minute=45, day_of_week=2),
    },
}
