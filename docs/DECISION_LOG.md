# Decision Log

Architectural and design decisions made during development.

---

## D-009: Increase PER_VARIANT_TIMEOUT to 60 minutes (2026-02-17)

**Context:** After the 12 cps pacing fix, each scene generates ~3x more frames. On the 1GB VPS, Pillow frame-by-frame rendering takes 8-15 min per scene. With 3 scenes, a single variant can take 45+ minutes.

**Decision:** Increased `PER_VARIANT_TIMEOUT` from 1500 (25 min) to 3600 (60 min). 3 variants × 60 min = 3 hours max total generation time.

**Trade-off:** Longer before a truly stuck generation is detected. Acceptable because safe_task + notify_error now surface actual errors immediately — the timeout is only a last-resort safety net.

---

## D-008: DRAFT episode numbering — assign on publish, not generation (2026-02-17)

**Context:** Episode counter incremented during `generate_episode()`. Every script attempt (including failures, edits, and abandoned episodes) consumed a number. After 2 scripts and 0 publishes, counter was at 3.

**Decision:** Two-phase numbering:
1. Script generation: `_get_next_episode_id()` returns `DRAFT-EP-{num:03d}` — peeks at counter without incrementing
2. Publish: `assign_episode_number()` returns `EP{num:03d}` and increments counter — called only after successful Google Drive upload

**Alternative considered:** Assigning the number before upload and rolling back on failure. Rejected because rollback logic adds complexity and the single-process pipeline ensures no race conditions with the peek-then-assign approach.

---

## D-007: Move continuity logging after Drive upload (2025-02-17)

**Context:** `log_episode()` was called before Drive upload in `_generate_metadata_and_schedule()`. If continuity files were missing or corrupted, it crashed the entire function before Drive upload could execute.

**Decision:** Move continuity logging + episode index logging to after Drive upload and platform publishing. Wrap each in its own try/except so failures are non-blocking.

**Trade-off:** If continuity logging fails, the episode still publishes but won't be tracked in the timeline/gags/growth files. This is acceptable — a published video with missing continuity data is better than a blocked publish.

---

## D-006: safe_task wrapper over asyncio.create_task (2025-02-17)

**Context:** Every background task (script gen, video gen, metadata/publish) used bare `asyncio.create_task`. Python's default behavior for unhandled exceptions in tasks is to log to stderr and set `Task.exception()` — but nobody checks it. Result: silent failures.

**Decision:** Created `safe_task()` in `src/bot/tasks.py` as a drop-in replacement. Catches all exceptions and: (1) prints to stdout for journalctl, (2) sends to originating Discord channel, (3) sends to #errors via notify_error.

**Alternative considered:** Adding `.add_done_callback()` to each task. Rejected because it requires more boilerplate at every call site and doesn't provide the error_channel routing.

---

## D-005: Startup recovery for stuck pipeline states (2025-02-17)

**Context:** When the VPS restarts (systemctl restart, crash, deploy), any in-flight background task is killed. The pipeline state file still says `video_generating` or `publishing`, but nothing is running. The pipeline is permanently stuck until `!reset`.

**Decision:** `on_ready()` calls `recover_stuck_state()` which maps in-flight states to the last human-interaction state:
- `script_generating` → `idle` (re-generate ideas)
- `video_generating` → `script_review` (re-approve script)
- `publishing` → `video_review` (re-approve video)

Human-waiting states (`ideas_posted`, `script_review`, `video_review`) are left alone.

**Trade-off:** Any partial progress from the interrupted task is lost. For video generation, this means re-rendering all variants. Acceptable given the alternative (permanently stuck pipeline).

---

## D-004: notify_error prints on failure instead of silent pass (2025-02-17)

**Context:** `notify_error()` had `except Exception: pass`. If Discord API was down or channel IDs were wrong, alerting failures were completely invisible — not in logs, not in Discord, nowhere.

**Decision:** Changed to `except Exception as e: print(f"[Alerting] ...")`. Still never raises (alerting must not crash the bot), but now failures appear in journalctl.

---

## D-003: _load_json returns {} for missing files (2025-02-17)

**Context:** `continuity/engine.py` `_load_json()` crashed with `FileNotFoundError` when timeline.json, running_gags.json, or character_growth.json didn't exist. On a fresh VPS deploy, these files don't exist yet.

**Decision:** Return empty dict `{}` when file doesn't exist. The calling functions (get_timeline, get_running_gags, etc.) already handle empty results with `.get("key", [])`.

---

## D-002: Typewriter speed 12 chars/sec (2025-02-17)

**Context:** Original spec was 20 cps. Bug made it 30 cps. User said "too fast to read."

**Decision:** 12 chars/sec — matches subtitle reading speed standards. 2-second hold time after typewriter completes.

---

## D-001: Float division for frame timing (2025-02-17)

**Context:** `frames_per_char = frame_rate // chars_per_second` used integer division. At 30fps/20cps, this gave `1` instead of `1.5`, making text appear at 30cps.

**Decision:** Use float division `frame_rate / chars_per_second` and `int()` only at the final frame count calculation. More accurate for any fps/cps combination.
