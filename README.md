# Sonarr Plus

A custom Home Assistant integration based on the core [Sonarr integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/sonarr), with extra actions for finding and searching for missing episodes. It installs side by side with the core integration under the domain `sonarr_plus`, so you add it as its own integration with its own Sonarr connection.

Everything from core is kept (sensors, calendar, `get_series`, `get_episodes`, `get_queue`, `get_diskspace`, `get_upcoming`, `get_wanted`). Added actions:

## `sonarr_plus.get_missing_episodes`

Returns monitored episodes without a file that aired in the last `days` days (1–3650, default 30). Sonarr's `wanted/missing` endpoint cannot filter by date, so the filter is applied against each episode's `airDateUtc`; episodes that have not aired yet are never returned.

| Field | Required | Description |
|---|---|---|
| `entry_id` | yes | Sonarr Plus config entry |
| `days` | no | Look-back window in days (default 30) |

Response: `count`, `episode_ids` (ready to pass to the search action) and `episodes` (details keyed by `Series SxxEyy`).

## `sonarr_plus.search_episodes`

Sends an `EpisodeSearch` command to Sonarr (the Sonarr `command` API) for the given episode IDs. Duplicate IDs are dropped.

| Field | Required | Description |
|---|---|---|
| `entry_id` | yes | Sonarr Plus config entry |
| `episode_ids` | yes | List of Sonarr episode IDs |

Response: `count` and `command` (`id`, `status`).

## Example: search everything missing from the last 30 days

```yaml
sequence:
  - action: sonarr_plus.get_missing_episodes
    data:
      entry_id: YOUR_ENTRY_ID
      days: 30
    response_variable: missing
  - condition: template
    value_template: "{{ missing.count > 0 }}"
  - action: sonarr_plus.search_episodes
    data:
      entry_id: YOUR_ENTRY_ID
      episode_ids: "{{ missing.episode_ids }}"
```

## Install

Copy `custom_components/sonarr_plus` into your Home Assistant `config/custom_components/` folder (or add the repo to HACS as a custom repository), restart, then add **Sonarr Plus** under Settings → Devices & services.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install pytest-homeassistant-custom-component aiopyarr==23.4.0
.venv/bin/pytest
```

Notes: the integration targets released Home Assistant (2026.8+, `voluptuous`; core `dev` has moved to `probatio`), so `async_setup_entry`/`async_migrate_entry`/`async_unload_entry` return `bool` (core `dev` has dropped that). `translations/en.json` is generated from `strings.json` with `[%key:...%]` references resolved, since custom integrations only load `translations/`.
