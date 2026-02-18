# Changelog

All notable changes to the Mootoshi pipeline.

---

## 2026-02-17 — DRAFT Episode Numbering System

**Problem:** Episode counter incremented at script generation, not on successful publish. After 2 scripts and 0 published episodes, counter was already at 3.

**Root Cause:** `_increment_episode_counter()` was called inside `generate_episode()`. Counter drifted with every script generation attempt, even failed/abandoned ones.

**Fixes:**
- `_get_next_episode_id()` now returns `DRAFT-EP-{num:03d}` format (no counter increment)
- Removed `_increment_episode_counter()` from `engine.py` entirely
- Added `assign_episode_number()` — called only after successful Google Drive upload in `video_preview.py`
- Variant filenames use draft prefix: `draft-ep-001_v1`, `draft-ep-001_v2`
- Real `EP001` format assigned at publish time and saved to `state["current_episode"]`
- Reset `data/episodes/index.json` counter to 1 (no episodes have been published)
- Reset `data/pipeline_state.json` to idle

**Tests:** 8 new tests in `tests/test_episode_numbering.py`. Full suite: 435 passed, 0 failed.

---

## 2026-02-17 — Video Generation Timeout Increase

**Problem:** Video generation timed out on variant 1/3 after 25 minutes.

**Root Cause:** `PER_VARIANT_TIMEOUT` was 1500s (25 min). After 12 cps pacing fix tripled frame count per scene, each scene takes ~8-15 min on VPS. 3 scenes × 15 min = 45 min > 25 min timeout.

**Fix:** Increased `PER_VARIANT_TIMEOUT` from 1500 to 3600 (60 min per variant).

---

## 2025-02-17 — Pipeline Reliability Fixes (Silent Failure Elimination)

**Problem:** Pipeline silently failed at every stage. Discord showed nothing. Google Drive upload never executed. No monitoring or alerting worked.

**Root Cause:** `asyncio.create_task` fire-and-forget pattern swallowed all exceptions in background tasks. Combined with `notify_error`'s `except Exception: pass`, every failure was invisible.

**Fixes:**
- All `asyncio.create_task` calls replaced with `safe_task()` wrapper (`src/bot/tasks.py`)
- `notify_error()` / `notify_startup()` now print to stdout when alerting fails
- `continuity/engine.py` `_load_json()` returns `{}` for missing files instead of crashing
- Startup recovery detects stuck pipeline states and rolls back (`src/bot/recovery.py`)
- Moved `log_episode()` after Drive upload so continuity failures can't block publishing

**Tests:** 23 new tests in `tests/test_pipeline_reliability.py`. Full suite: 427 passed, 0 failed.

---

## 2025-02-17 — Text Pacing Overhaul

**Problem:** Video dialogue was too fast to read.

**Root Cause:** Integer division `30 // 20 = 1` gave 1 frame per char = 30 chars/sec instead of intended 20.

**Fixes:**
- Typewriter speed set to 12 chars/sec with float division
- Text hold time increased from 0.5s to 2.0s
- Scenes auto-extend if dialogue needs more time than script allocated
- Audio blip timing synced to 12 cps

---

## 2025-02-17 — Positioning & Asset Fixes

**Fixes:**
- Characters floating in sky — all positions verified at ground level (y=1050-1480)
- Storyboard renderer used raw position names instead of `resolve_scene_positions()`
- `door_burst.wav` and `menu_select.wav` created from existing SFX
- `VALID_SFX` / `VALID_MUSIC` in validator wired up with actual validation
- Audio mixer logs warnings for missing SFX instead of silent skip

---

## 2025-02-17 — Test & Deploy Fixes

**Fixes:**
- `test_missing_folder_id` leaking real env vars — added `GOOGLE_DRIVE_FOLDER_ID: ""` to patch dict
- `requests` missing from `requirements.txt` — broke publisher on VPS
