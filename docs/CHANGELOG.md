# Changelog

All notable changes to the Mootoshi pipeline.

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
