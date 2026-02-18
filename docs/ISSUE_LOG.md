# Issue Log

All diagnosed issues, their root causes, and resolution status.

---

## Resolved Issues

### ISS-009: Video generation timeout too tight after pacing fix (2026-02-17)
**Severity:** High — variant 1/3 killed before completion
**Root Cause:** `PER_VARIANT_TIMEOUT = 1500` (25 min) was set before the 12 cps pacing fix tripled frame count. 3 scenes × 15 min = 45 min > 25 min.
**Fix:** Increased to `PER_VARIANT_TIMEOUT = 3600` (60 min per variant).
**Status:** RESOLVED

### ISS-008: Episode counter increments at script gen, not publish (2026-02-17)
**Severity:** High — counter drifts with every script attempt, real EP numbers never match
**Root Cause:** `_increment_episode_counter()` called inside `generate_episode()`. Every script gen (including failures/abandons) consumed a number. 2 scripts, 0 publishes → counter at 3.
**Fix:** Removed `_increment_episode_counter()`. Scripts use `DRAFT-EP-XXX` format. Real `EP001` assigned by `assign_episode_number()` only after successful Google Drive upload.
**Status:** RESOLVED

### ISS-007: data/episodes/index.json and data/continuity/ may not exist (2025-02-17)
**Severity:** High — crashes pipeline on fresh VPS deploy
**Root Cause:** Multiple `json.load()` / `open()` calls assume files exist
**Fix:** `_load_json()` returns `{}` for missing files. `log_episode_to_index()` already created dirs with `os.makedirs(exist_ok=True)`.
**Status:** RESOLVED

### ISS-006: TikTok and Instagram publishers are stubs (2025-02-17)
**Severity:** Low — informational only
**Root Cause:** By design — only YouTube + Google Drive are implemented
**Fix:** N/A. `platforms.yaml` has `tiktok: enabled: false` and `instagram: enabled: false`.
**Status:** KNOWN / BY DESIGN

### ISS-005: No startup recovery from crashed states (2025-02-17)
**Severity:** Critical — pipeline permanently stuck after any VPS restart
**Root Cause:** `on_ready()` never checked `pipeline_state.json` for in-flight states
**Fix:** `src/bot/recovery.py` — `recover_stuck_state()` called from `on_ready()`. Maps `script_generating` → `idle`, `video_generating` → `script_review`, `publishing` → `video_review`.
**Status:** RESOLVED

### ISS-004: continuity JSON files crash on missing files (2025-02-17)
**Severity:** Critical — blocks entire publish path (Drive upload, platform publish, episode logging)
**Root Cause:** `_load_json()` did `open(path, "r")` with no existence check. On fresh VPS, continuity files don't exist.
**Fix:** Added `if not os.path.exists(path): return {}` to `_load_json()`.
**Status:** RESOLVED

### ISS-003: platforms.yaml FileNotFoundError (2025-02-17)
**Severity:** Medium — crashes platform publisher if config missing
**Root Cause:** `_load_platform_config()` has no error handling for missing file
**Fix:** Covered by safe_task wrapper — exception is now caught and reported. Config file exists in repo.
**Status:** RESOLVED (mitigated)

### ISS-002: notify_error silently swallows its own errors (2025-02-17)
**Severity:** Critical — alerting failures were completely invisible
**Root Cause:** `except Exception: pass` in both `notify_error()` and `notify_startup()`
**Fix:** Changed to `except Exception as e: print(f"[Alerting] Failed to send error alert: {e}")`. Still never raises.
**Status:** RESOLVED

### ISS-001: asyncio.create_task swallows exceptions (2025-02-17)
**Severity:** Critical — THE root cause of all silent failures
**Root Cause:** `asyncio.create_task` fire-and-forget pattern. Python logs unhandled task exceptions to stderr but doesn't surface them. Nobody calls `task.exception()` or `task.result()`.
**Affected:** `idea_selection.py` (script gen), `script_review.py` (video gen, script revision), `video_preview.py` (metadata/publish, custom variant), `bot.py` (weekly analytics)
**Fix:** `src/bot/tasks.py` — `safe_task()` wrapper that catches exceptions and sends to stdout + Discord channel + #errors.
**Status:** RESOLVED

---

## Pre-existing Issues (resolved same day)

### Text too fast to read (2025-02-17)
**Root Cause:** Integer division `30 // 20 = 1` → 30 cps instead of 20 cps
**Fix:** Float division, 12 cps, 2s hold time, auto-extend scenes
**Status:** RESOLVED

### Characters floating in sky (2025-02-17)
**Root Cause:** Y positions too high. Storyboard renderer not using `resolve_scene_positions()`.
**Fix:** Ground-level positions (y=1050-1480). Wired up position resolver.
**Status:** RESOLVED

### Missing SFX assets (2025-02-17)
**Root Cause:** `door_burst.wav` and `menu_select.wav` referenced but not on disk
**Fix:** Created from existing SFX files
**Status:** RESOLVED

### test_missing_folder_id leaking real env vars (2025-02-17)
**Root Cause:** `patch.dict` without `clear=True` let real `GOOGLE_DRIVE_FOLDER_ID` leak through
**Fix:** Added `"GOOGLE_DRIVE_FOLDER_ID": ""` to patch dict
**Status:** RESOLVED

### requests module missing on VPS (2025-02-17)
**Root Cause:** `requests` not in `requirements.txt`
**Fix:** Added `requests>=2.31.0`
**Status:** RESOLVED
