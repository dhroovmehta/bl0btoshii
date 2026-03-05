# Changelog

All notable changes to the Mootoshi pipeline.

---

## 2026-02-22 — LANCZOS Resampling & External Watermark Removal

**Problem:** Two visual artifacts in rendered output: (1) Visible vertical seams/stripes in all background images — caused by `Image.NEAREST` resampling at non-integer scale factors (e.g., 2752→1920 = 0.698x). Nearest-neighbor creates uneven column widths that appear as vertical bands in smooth illustrations. (2) A rectangular texture mismatch in the bottom-right corner of backgrounds — the `clean_background()` watermark removal function copied pixels from above the watermark area, which at material boundaries (grass/dirt, wood plank edges) created a visible patch.

**What changed:**

1. **LANCZOS resampling for backgrounds** — Switched all background resize calls from `Image.NEAREST` to `Image.LANCZOS` across 4 files. Character sprites remain NEAREST (correct for pixel art).

2. **External watermark removal** — Watermarks are now removed externally before source images enter the pipeline. `process_single_background()` no longer calls `clean_background()`. Processing is now: crop dark edges → LANCZOS resize. This eliminates the texture mismatch artifact entirely.

3. **Debug overlay removal** — Removed crosshair markers, coordinate labels, and title bar from `generate_positioning_test.py` output — clean composites only.

4. **Test updates** — Added 3 new LANCZOS verification tests (mock-based, tracking resampling method). Replaced obsolete `test_watermark_corner_is_patched` with `test_source_content_preserved_no_watermark_patching`.

**New architectural decisions:** D-028 (LANCZOS for backgrounds), D-029 (external watermark removal)

**Files modified:**
- `src/video_assembler/scene_builder.py` — 3 NEAREST→LANCZOS changes in `load_background_layers()`
- `scripts/process_background.py` — NEAREST→LANCZOS, removed watermark step
- `scripts/resize_for_pipeline.py` — NEAREST→LANCZOS for backgrounds
- `src/storyboard/renderer.py` — NEAREST→LANCZOS for thumbnails
- `scripts/generate_positioning_test.py` — removed debug overlay code
- `tests/test_process_background.py` — 3 new LANCZOS tests, 1 updated watermark test

**Test count:** 784 passing (unchanged count — replaced 1 obsolete test)

---

## 2026-02-22 — Per-Character Default Facing & Foreground Grounding

**Problem:** After the initial positioning fix, three issues remained: (1) Characters faced the *same* direction instead of facing each other — the mirror logic assumed all sprites face right by default, but pixel mass analysis revealed 4/6 characters (Chubs, Meows, Oinks, Quacks) face LEFT in their source sprites. When Oinks (default left) was mirrored for `facing="left"`, it flipped to face RIGHT — same as Pens. (2) Characters were positioned too high — ground_y values placed feet in the mid-ground (e.g., town_square horizontal at 0.78 = y=842, which is mid-grass). (3) Tests were not comprehensive enough — no coverage for per-character facing, no full position matrix across all 6 characters x 4 locations x 2 orientations.

**What changed:**

1. **Per-character `default_facing`** — Added `default_facing` field to all 6 characters in `characters.json`: Pens and Reows face RIGHT, Chubs/Meows/Oinks/Quacks face LEFT. Mirror logic changed from `if facing == "left"` to `if facing != default_facing`. A left-facing sprite placed at a left-facing position is NOT mirrored; it IS mirrored when placed at a right-facing position.

2. **Foreground ground_y values** — All ground_y values raised to place characters firmly in the foreground:
   - Diner: H 0.90→0.92, V 0.84→0.90
   - Farmers Market: H 0.84→0.90, V 0.77→0.88
   - Town Square: H 0.78→0.88, V 0.78→0.88
   - Reows Place: H 0.82→0.90, V 0.82→0.90

3. **Comprehensive test suite** — 42 new tests added:
   - `TestDefaultFacing` (8 tests): every character has `default_facing`, correct values per character
   - `TestForegroundPositioning` (8 parametrized tests): horizontal >= 85%, vertical >= 82%
   - `TestFullPositionMatrix` (~24 tests): all 6 chars x all 4 locations x both orientations — no crashes, primary pair faces each other
   - Pixel mass orientation test: verifies Oinks facing left preserves original sprite orientation
   - Mirror difference test: all 6 characters produce > 1000 pixel diff when mirrored

**New architectural decision:** D-027 (per-character default facing)

**Files modified:**
- `data/characters.json` — added `default_facing` to all 6 characters
- `data/locations.json` — all ground_y values raised for foreground grounding
- `src/video_assembler/sprite_manager.py` — `get_default_facing()` function, mirror logic uses default_facing comparison
- `src/storyboard/renderer.py` — mirror logic uses default_facing comparison
- `scripts/generate_positioning_test.py` — mirror logic uses default_facing comparison
- `tests/test_ground_anchored_positioning.py` — 40 new tests (facing, foreground, full matrix)
- `tests/test_video_assembler.py` — 4 new facing verification tests
- `tests/test_character_positioning.py` — dynamic ground_y assertions

**Test count:** 776 passing (was 734 — +42 new comprehensive tests)

---

## 2026-02-22 — Conversational Positioning & Sprite Facing

**Problem:** Characters were positioned at extreme edges of the frame (x_pct 0.14 and 0.83), making them look disconnected rather than engaged in conversation. Additionally, the `facing` field existed in `locations.json` but was completely ignored by the rendering code — all characters faced right regardless. In vertical mode (1080px wide), the diner's stool positions were so close they overlapped (219px gap for 240px-wide sprites).

**What changed:**

1. **Conversational positioning** — All primary conversation positions moved to x_pct 0.35 and 0.65 (30% gap). This produces:
   - Horizontal (1920px): 576px between centers = 2.4 character widths
   - Vertical (1080px): 324px between centers = 1.35 character widths
   Both look natural for two characters in casual conversation.

2. **Position reordering** — First two positions per location are now the primary conversation pair (stool_1/stool_2, bench_left/bench_right, etc.). `resolve_scene_positions()` assigns characters in order, so the first two always get the facing pair.

3. **Sprite facing** — `resolve_ground_position()` now returns `(x, y, facing)` 3-tuples. `composite_character()` applies `ImageOps.mirror()` when facing=="left". Left position faces right, right position faces left — characters look at each other.

4. **Storyboard facing** — `src/storyboard/renderer.py` updated to handle 3-tuples and flip thumbnails for facing direction.

5. **Sprite constants updated** — Test constants updated to match Bootoshi sprite sizes: MAX_SPRITE_WIDTH 192→260, MAX_SPRITE_HEIGHT 288→420. Obsolete tests removed (fixed-position text box clearance checks).

**New architectural decision:** D-026 (conversational positioning and sprite facing)

**Files modified:**
- `data/locations.json` — all position x_pct values and facing directions
- `src/video_assembler/sprite_manager.py` — 3-tuple returns, ImageOps.mirror flip
- `src/video_assembler/scene_builder.py` — 3-tuple unpacking for bubble positioning
- `src/storyboard/renderer.py` — 3-tuple unpacking + facing flip for thumbnails
- `tests/test_ground_anchored_positioning.py` — 7 new facing tests + updated assertions
- `tests/test_character_positioning.py` — updated constants, removed obsolete tests
- `tests/test_video_assembler.py` — 2 new flip tests
- `tests/test_v2_rendering.py` — adjusted bottom-strip threshold for sprite state diffs
- `scripts/generate_positioning_test.py` — new visual verification script

**Test count:** 734 passing (was 634 — +100 from previous session's work, net +7 new facing/flip tests, -3 removed obsolete tests)

---

## 2026-02-21 — Speech Bubble Dialogue System

**Problem:** Dialogue rendered as a fixed-width text box at the bottom of the screen with character portrait and name label. This looked dated and didn't match the Bootoshi.ai visual style where dialogue appears as floating speech bubbles above the speaking character.

**What changed:**

1. **Speech bubble renderer** — `src/text_renderer/renderer.py` completely rewritten. Dark auto-sized bubbles (near-black at 94% opacity) with white Press Start 2P text, rounded corners, and a triangular tail pointing down toward the speaker. Bubble width auto-sizes to fit text content, capped at max width per format (500px horizontal, 450px vertical).

2. **Character-relative positioning** — `src/video_assembler/scene_builder.py` now positions bubbles above the speaking character's head (centered on X, sprite_top - bubble_height - 8px gap) instead of at a fixed Y coordinate. Pre-computes sprite heights before the frame generator for efficiency.

3. **Removed from bubbles:** character name label, character portrait, fixed-width box layout.

4. **Audio blips disabled** — `generate_blip_events()` returns `[]`. Speech bubbles don't use audio blips.

5. **RenderConfig updated** — `text_box_width` repurposed as max speech bubble width (HORIZONTAL: 500px, VERTICAL: 450px). `text_box_height` and `text_box_y` kept for backward compatibility but unused.

**New architectural decision:** D-025 (speech bubble dialogue system)

**Files modified:**
- `src/text_renderer/renderer.py` — complete rewrite (speech bubbles)
- `src/video_assembler/scene_builder.py` — character-relative bubble positioning
- `src/video_assembler/render_config.py` — text_box_width now controls max bubble width
- `src/audio_mixer/mixer.py` — blip events disabled
- `tests/test_text_renderer.py` — rewritten for bubble constants and behavior
- `tests/test_v2_rendering.py` — added bubble positioning tests
- `tests/test_audio_mixer.py` — updated blip tests for disabled state
- `tests/test_dual_format.py` — updated for new RenderConfig values

**Test count:** 661 passing (was 657 — +4 new bubble tests)

---

## 2026-02-21 — Background Migration & Location Simplification

**Problem:** v1 had 6 locations (diner_interior, beach, forest, town_square, chubs_office, reows_place) with single vertical-only backgrounds (1080x1920). The Bootoshi visual redesign simplified this to 4 locations and required both horizontal (1920x1080) and vertical (1080x1920) backgrounds.

**What changed:**

1. **Locations simplified from 6 to 4:**
   - `diner` (renamed from `diner_interior`) — kept, same character positions
   - `farmers_market` — new location with stall_left, center_aisle, stall_right positions
   - `town_square` — kept unchanged
   - `reows_place` — kept unchanged
   - Removed: `beach`, `forest`, `chubs_office`

2. **Dual-orientation backgrounds** — each location now has horizontal + vertical:
   - `{location}.png` (1920x1080) — used for YouTube horizontal render
   - `{location}_vertical.png` (1080x1920) — used for Shorts/TikTok/Reels vertical render
   - 8 new background files total, 6 old ones deleted

3. **Vertical-aware background loading** — `scene_builder.load_background_layers()` now checks for `{id}_vertical.png` when target dimensions are vertical (height > width), falling back to `{id}.png`.

4. **Background processing script** — `scripts/process_background.py` handles watermark removal (bottom-right logo) and resizing from source dimensions (2752x1536 / 1536x2752) to pipeline dimensions.

5. **All references updated** — `locations.json`, `situations.json`, `content_weights.json`, `slot_machine.py`, `scene_builder.py`, `storyboard/renderer.py`, `resize_for_pipeline.py`, `copy_to_assets.py`, and all test files.

**New architectural decision:** D-024 (location simplification)

**Files created:**
- `scripts/process_background.py` — background processing (watermark removal + resize)
- `tests/test_process_background.py` — 15 tests

**Files modified:**
- `data/locations.json` — 6 locations → 4 locations
- `data/situations.json` — updated all best_locations arrays
- `data/analytics/content_weights.json` — updated location_weights
- `src/video_assembler/scene_builder.py` — vertical-aware loading + default fallback
- `src/storyboard/renderer.py` — default fallback diner_interior → diner
- `src/story_generator/slot_machine.py` — hardcoded location reference
- `scripts/resize_for_pipeline.py` — updated BG dimensions + vertical awareness
- `scripts/copy_to_assets.py` — updated BG_NAME_MAP
- `scripts/test_pipeline_assets.py` — updated expected assets
- `tests/conftest.py` — updated fixtures
- ~13 test files — diner_interior → diner, removed location references

**Tests:** 23 new tests added. Full suite: 657 passed, 0 failed.

---

## 2026-02-18 — v2 Stage 6: YouTube Dual-Publish

**Problem:** v1 only published one video to YouTube (always as a Short with `#Shorts` tag). After Stage 4 added dual format rendering (horizontal + vertical), we needed both videos published: horizontal as a regular YouTube video and vertical as a YouTube Short.

**What changed:**

1. **`publish_to_youtube()` gains `is_short` parameter** — controls whether `#Shorts` tag is kept or stripped from title and description:
   - `is_short=True`: Ensures `#Shorts` is in description (YouTube Short classification)
   - `is_short=False` (default): Strips `#Shorts` from both title and description (regular YouTube video)

2. **Pipeline Step 7 publishes twice** — calls `publish_to_youtube` for both formats:
   - Horizontal video → `publish_to_youtube(video_path_h, metadata, is_short=False)` — regular YouTube
   - Vertical video → `publish_to_youtube(video_path_v, metadata, is_short=True)` — YouTube Short

3. **Separate Discord notifications** — each upload sends its own success/failure message to `#pipeline-status` with format label (horizontal/vertical).

4. **Safety gate applies to both** — if safety check fails, neither upload happens.

**New architectural decision:** D-023 (YouTube dual-publish)

**Files modified:**
- `src/publisher/platforms.py` — `is_short` parameter, `#Shorts` tag stripping logic
- `src/bot/handlers/idea_selection.py` — Step 7 publishes both formats with separate error handling

**Tests:** 11 new tests in `tests/test_youtube_dual_publish.py`. Full suite: 634 passed, 0 failed.

---

## 2026-02-18 — v2 Stage 5: Audio Overhaul

**Problem:** v1 audio was too loud — music overpowered dialogue, SFX were jarring, text blips were distracting. Music stayed at the same volume during dialogue, making it hard to focus on the text. No mood-based music selection.

**What changed:**

1. **Volume reduction** — all audio levels significantly quieter:
   - Music: -12 dB → -20 dB (atmospheric background, not dominant)
   - SFX: -3 dB → -8 dB (noticeable but not jarring)
   - Text blips: -6 dB → -14 dB (subtle, not distracting)

2. **Dialogue ducking** — music drops an additional -6 dB during dialogue sections:
   - New `generate_ducking_schedule()` extracts dialogue time ranges from script
   - `_apply_ducking()` splits music at dialogue boundaries and reduces gain
   - `mix_episode_audio()` now applies ducking automatically (can disable with `enable_ducking=False`)

3. **Mood-based music selection** — already partially implemented in Stage 2 pipeline (`idea_selection.py`). Script's `metadata.mood` selects `playful.wav`, `calm.wav`, or `tense.wav` with v1 fallbacks.

**New architectural decision:** D-022 (dialogue ducking)

**Files modified:**
- `src/audio_mixer/mixer.py` — new volumes, DUCKING_DB constant, `generate_ducking_schedule()`, `_apply_ducking()`, `enable_ducking` parameter

**Tests:** 12 new tests in `tests/test_audio_overhaul.py`. Full suite: 629 passed, 0 failed.

---

## 2026-02-18 — v2 Stage 4: Dual Format Output

**Problem:** v2 Stage 3 rendered only 16:9 horizontal video. YouTube Shorts, TikTok, and Reels need 9:16 vertical. Previously you'd only get one format and miss the other platforms.

**What changed:**

1. **Render config module** — `src/video_assembler/render_config.py` defines `HORIZONTAL` (1920x1080) and `VERTICAL` (1080x1920) presets with format-specific text box layout.

2. **All rendering functions accept `render_config`** — `render_dialogue_frames()`, `build_scene_frames()`, `compose_episode()`, and `generate_end_card_frames()` accept an optional config. Default is horizontal (backward compatible).

3. **Pipeline renders both formats** — `_run_full_pipeline()` calls `compose_episode` twice (once horizontal, once vertical). Both videos uploaded to Google Drive with distinct filenames (`ep0001_title.mp4` + `ep0001_title_vertical.mp4`).

4. **Quality gate updated** — `check_video_quality()` accepts both 1920x1080 and 1080x1920 resolutions as valid.

5. **Asset check updated** — `check_asset_availability()` accepts parallax folder-based backgrounds in addition to single files.

**New architectural decision:** D-021 (dual format rendering)

**Files created:**
- `src/video_assembler/render_config.py` — RenderConfig dataclass with HORIZONTAL/VERTICAL presets

**Files modified:**
- `src/text_renderer/renderer.py` — accepts render_config for text box dimensions
- `src/video_assembler/scene_builder.py` — accepts render_config for frame dimensions, background scaling, position scaling
- `src/video_assembler/composer.py` — accepts render_config, format label in output filename
- `src/pipeline/orchestrator.py` — quality check accepts both resolutions, asset check accepts folder-based backgrounds
- `src/bot/handlers/idea_selection.py` — pipeline renders both formats, uploads both to Drive

**Tests:** 24 new tests in `tests/test_dual_format.py`. Full suite: 617 passed, 0 failed.

---

## 2026-02-18 — v2 Stage 3: Rendering Engine Upgrade

**Problem:** v1 rendered at 1080x1920 (vertical 9:16 only). Single flat backgrounds. No camera movements. Each frame saved as PNG to disk — slow, disk-heavy, and creates thousands of temporary files. Characters sized for vertical format looked tiny.

**What changed:**

1. **16:9 horizontal format** — primary output now 1920x1080. Characters and text boxes sized for widescreen.

2. **Parallax background system** — multi-layer backgrounds with depth effect:
   - Folder-based: `assets/backgrounds/{location}/background.png`, `midground.png`, `foreground.png`, optional `effects.png`
   - v1 fallback: single `{location}.png` files still work (resized to 1920x1080)
   - Each layer scrolls at different speed during camera pans (background=0.2x, midground=0.5x, foreground=0.8x)

3. **Camera system** — pan and zoom per scene:
   - New module: `src/video_assembler/camera.py`
   - Scenes can specify `camera: {start: {x, y, zoom}, end: {x, y, zoom}}`
   - Linear interpolation between start/end over scene duration
   - Default: static camera at origin (backward compatible)

4. **Frame streaming** — frames piped directly to FFmpeg via stdin:
   - No intermediate PNG files on disk (eliminates thousands of file writes)
   - `build_scene_frames()` returns a generator of PIL Images
   - `render_dialogue_frames()` returns PIL Images in memory
   - `compose_episode()` streams raw RGB bytes to `ffmpeg -f rawvideo`
   - Faster rendering, less disk I/O, lower storage usage

5. **Position scaling** — v1 character positions (calibrated for 1080x1920) automatically scaled to 1920x1080 via `scale_position_v1()`.

6. **Text box widened** — 1200x180 (was 900x200) for widescreen readability.

**New architectural decisions:** D-018 (16:9 primary format), D-019 (frame streaming), D-020 (parallax engine)

**Files created:**
- `src/video_assembler/camera.py` — camera system with pan, zoom, parallax

**Files modified:**
- `src/video_assembler/scene_builder.py` — 1920x1080, parallax loading, generator output, camera integration
- `src/video_assembler/composer.py` — frame streaming via FFmpeg stdin, no intermediate PNGs
- `src/text_renderer/renderer.py` — in-memory PIL Image output, wider text box

**Tests:** 31 new tests in `tests/test_v2_rendering.py`. Updated `test_e2e_pipeline.py`, `test_text_renderer.py`, `test_video_assembler.py` for v2 compatibility. Full suite: 587 passed, 0 failed.

---

## 2026-02-18 — v2 Stage 2: Pipeline Simplification

**Problem:** v1 pipeline had 3 human touchpoints (pick idea, approve script, pick video variant) and 8 pipeline stages. Too many steps = too many failure points. Notion integration added complexity for no value. Video variants were never meaningfully different.

**What changed:**
- **Removed Notion integration** (D-010) — no more script publishing to Notion
- **Removed script review step** (D-011) — scripts auto-generated, no human approval needed
- **Removed video variant system** (D-012) — 1 video per episode, not 3 variants to pick from
- **Removed `#script-review` and `#video-preview` channel routing** — `#script-review` renamed to `#pipeline-status` in code (same env var `DISCORD_CHANNEL_SCRIPT_REVIEW`)

**New automated pipeline:**
User picks idea → `_run_full_pipeline()` runs 9 steps automatically:
1. Generate script (LLM)
2. Check asset availability (backgrounds, characters, music)
3. Render video (`compose_episode`)
4. Quality check (duration, file size)
5. Generate metadata + safety check
6. Upload to Google Drive (assigns real EP number here)
7. Publish to YouTube (skipped if safety check fails)
8. Log continuity (timeline, gags, character growth)
9. Mark done → Discord notification

**State machine simplified:**
- v1: `idle → ideas_posted → script_generating → script_review → video_generating → video_review → publishing → done` (8 stages)
- v2: `idle → ideas_posted → pipeline_running → done` (4 stages)

**Recovery map simplified:**
- v1: `script_generating→idle, video_generating→script_review, publishing→video_review`
- v2: `pipeline_running→idle` (only one in-flight state)

**Files modified:**
- `src/bot/state.py` — simplified default state (removed `script_notion_url`, `script_version`, `video_variants`, `selected_video_index`; added `current_script`)
- `src/bot/recovery.py` — v2 recovery map with only `pipeline_running→idle`
- `src/bot/handlers/idea_selection.py` — complete rewrite with `_run_full_pipeline()`
- `src/bot/bot.py` — removed `video_preview` from CHANNEL_IDS, removed script_review/video_preview handler routing

**Bug fix (ISS-013):** YouTube title now correctly flows from script root through `generate_metadata()` → `publish_to_youtube()`. No more empty titles.

**Tests:** 32 new tests in `tests/test_v2_pipeline.py`. Updated `test_state.py`, `test_pipeline_reliability.py`, `conftest.py` for v2 compatibility. Full suite: 556 passed, 0 failed.

---

## 2026-02-18 — v2 Stage 1: Silent Failure Elimination

**Problem:** Three components silently produced garbage output for missing assets. Videos rendered with invisible characters (transparent placeholder), blue screens (no background), and no music (silence). The pipeline reported "success" every time.

**Fixes:**
- `sprite_manager.load_sprite()` — now prints `[WARNING]` to stdout and collects warnings via `get_warnings()` when character is missing
- `scene_builder.load_background()` — now prints `[WARNING]` and collects warnings when background is missing
- `audio_mixer.mix_episode_audio()` — now prints `[WARNING]` and collects warnings when music file is missing
- `orchestrator.check_asset_availability()` — now checks music files (v2 mood-based + v1 fallback)
- `orchestrator.collect_rendering_warnings()` — new function that aggregates warnings from all three modules after rendering
- `orchestrator.clear_all_rendering_warnings()` — new function to reset before each render

**Pattern:** Each module maintains a `_warnings` list. Functions still return usable fallbacks (so the pipeline doesn't crash), but loudly warn. After rendering, the pipeline caller checks `collect_rendering_warnings()` and sends to Discord #errors.

**Tests:** 22 new tests in `tests/test_silent_failures.py`. Full suite: 472 passed, 0 failed.

---

## 2026-02-18 — v2 Redesign Kickoff

**Problem:** v1 pipeline was unreliable. Silent failures at every stage. Only 1 video ever published to YouTube (without a title). Pipeline stalled without alerting. Too many human touchpoints (script review, video variant selection). Visuals were basic NES pixel art.

**v2 Goals:**
- Kill all silent failures — every error must reach Discord #errors
- Simplify pipeline: 3 ideas → pick 1 → auto script → auto video → Drive → YouTube
- Dual format: 16:9 horizontal (YouTube) + 9:16 vertical (Shorts/TikTok/Reels)
- Cinematic pixel art: parallax backgrounds, camera movements, sprite animation
- Audio overhaul: quieter music (-20dB), mood-based selection, dialogue ducking
- Auto-publish to YouTube (regular + Shorts)

**Removed from v1:**
- Notion integration (D-010)
- Script review step (D-011)
- Video variant system (D-012)
- #script-review, #video-preview Discord channels

**New architectural decisions:** D-010 through D-017 (see DECISION_LOG.md)

**Build stages:**
1. Fix error alerting
2. Simplify pipeline flow
3. Upgrade rendering engine (16:9, parallax, camera)
4. Dual format output
5. Audio overhaul
6. YouTube dual-publish

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
