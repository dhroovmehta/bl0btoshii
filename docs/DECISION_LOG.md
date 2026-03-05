# Decision Log

Architectural and design decisions made during development.

---

## D-029: External watermark removal workflow (2026-02-22)

**Context:** The `clean_background()` function in `remove_watermarks.py` removed Nano Banana Pro watermarks by copying a strip of pixels from directly above the watermark area. This worked when the watermark sat on uniform textures, but at material boundaries (grass meeting dirt, wood plank edges) it created a visible rectangular patch — the copied strip had a different texture than what it replaced. The artifact was present in every background except the diner (which has a flat foreground).

**Decision:** Watermarks are now removed externally before source images enter the pipeline. `process_single_background()` no longer calls `clean_background()` — it only crops dark edges and LANCZOS-resizes. The user removes watermarks using an online tool (or any method of their choosing) and provides clean PNGs as source input. This cleanly separates "art cleanup" (manual/external) from "pipeline processing" (automated).

**Alternative considered:** Improve `clean_background()` with content-aware inpainting (e.g., using OpenCV's `inpaint()` or a texture synthesis approach). Rejected — adds significant complexity and dependency weight for a step the user can handle more accurately in seconds with an online tool. The pipeline should process, not repair.

---

## D-028: LANCZOS resampling for background images (2026-02-22)

**Context:** All background resize calls used `Image.NEAREST` (nearest-neighbor). At non-integer scale factors — the standard case, since source images are 2752x1536 and pipeline targets are 1920x1080 (0.698x) — nearest-neighbor produces uneven column widths. Each source pixel maps to either 0 or 1 output pixel, creating a repeating pattern of wider and narrower columns visible as vertical seam artifacts in smooth illustrations.

**Decision:** Switched all background resize calls to `Image.LANCZOS` across 4 files: `scene_builder.py` (3 locations — parallax layers, vertical backgrounds, single-file backgrounds), `process_background.py`, `resize_for_pipeline.py`, and `storyboard/renderer.py`. Character sprites remain `Image.NEAREST` because they are pixel art — LANCZOS would blur the intentionally crisp pixel edges. Added 3 mock-based tests that intercept `Image.resize()` calls and verify the resampling method parameter is LANCZOS (not NEAREST) for backgrounds.

**Alternative considered:** Pre-render source backgrounds at exact pipeline dimensions (1920x1080 and 1080x1920) to avoid resizing entirely. Rejected — Nano Banana Pro outputs at fixed resolutions (2752x1536), so resize is unavoidable. LANCZOS handles this correctly with smooth interpolation.

---

## D-027: Per-character default facing direction (2026-02-22)

**Context:** The initial facing implementation (D-026) used `if facing == "left": mirror()` — which assumed all sprite source images face right. Pixel mass analysis of all 12 sprites revealed this was wrong: only Pens and Reows face right in their source art. Chubs, Meows, Oinks, and Quacks face left. The result was that when Oinks (naturally left-facing) was placed at a left-facing position, the mirror flipped her to face RIGHT — both characters ended up facing the same direction.

**Decision:** Added `default_facing` to each character in `characters.json` (determined via pixel mass analysis of alpha channels — comparing left-half vs right-half pixel density). Mirror logic changed from `if facing == "left"` to `if facing != default_facing`. This means: a sprite is only flipped when the scene demands a direction opposite to its natural pose. Applied consistently across `sprite_manager.py`, `storyboard/renderer.py`, and `generate_positioning_test.py`.

Ground_y values also raised across all locations (diner H 0.92, farmers_market H 0.90, town_square H 0.88, reows_place H 0.90) to push characters into the visual foreground. Previous values placed characters in the mid-ground, making them look like they were floating in the grass or floor.

**Alternative considered:** Re-render all sprites to face right. Rejected — would require 12 new Nano Banana Pro generations and processing. The `default_facing` approach is data-driven and adapts automatically to however the artist produces the sprites.

---

## D-026: Conversational positioning and sprite facing (2026-02-22)

**Context:** Characters were positioned at location-specific named positions (stool_1, bench_left, etc.) but the x_pct values were calibrated for visual spread rather than conversational distance. Primary pairs were at 0.14/0.83 or 0.34/0.55 — either too far apart (characters look disconnected) or too close (overlap in vertical mode where 1080px width gives less room). The `facing` field was defined in `locations.json` but never read by the rendering pipeline — all sprites rendered facing right regardless.

**Decision:** Standardized all primary conversation positions at x_pct 0.35 and 0.65 across all 4 locations. This 30% gap produces comfortable conversational distance at both orientations (576px horizontal, 324px vertical). First two positions per location are always the primary pair and face each other (left faces right, right faces left). `resolve_ground_position()` returns `(x, y, facing)` 3-tuples, and `composite_character()` applies `ImageOps.mirror()` for `facing == "left"`. Backward compatibility maintained: `get_character_position()` still returns 2-tuples, and `composite_character()` accepts both 2-tuple and 3-tuple position arguments.

**Alternative considered:** Keep positions spread out and only fix facing. Rejected — the wide separation (e.g., 0.14 and 0.83 = 66% of frame width apart) looked wrong for characters in conversation. Natural talking distance is roughly 1.5-2.5 character widths, which maps to 0.35/0.65 in both orientations.

---

## D-025: Speech bubble dialogue system (2026-02-21)

**Context:** v1 dialogue rendered as a fixed-width dark box at the bottom of the screen with a character portrait and name label. This looked generic and didn't match the Bootoshi.ai visual style, where dialogue appears as floating speech bubbles above the speaking character — dark background, white pixel text, triangular tail pointing down.

**Decision:** Replaced the bottom-screen text box with auto-sized speech bubbles positioned above each speaking character. Bubbles use the same Press Start 2P font at 16px, dark background (20, 20, 30 at 94% opacity), rounded corners (6px radius), and a triangular tail (12px tall, 16px wide). Bubble width auto-sizes based on text content, capped at format-specific max (500px horizontal, 450px vertical). Scene builder pre-computes sprite heights and positions each bubble centered on the character's X coordinate, above their sprite top with an 8px gap. Frame-bound clamping prevents bubbles from going off-screen.

Audio blips disabled — `generate_blip_events()` returns empty list. Speech bubbles are a visual-only system with typewriter text animation (12 chars/sec + 2s hold).

**Alternative considered:** Keep bottom text box but restyle it to match Bootoshi colors. Rejected — character-relative floating bubbles are the defining visual element of Bootoshi.ai's dialogue system and create much stronger visual connection between speaker and text.

---

## D-024: Location simplification — 6 to 4 locations (2026-02-21)

**Context:** The Bootoshi visual redesign required regenerating all backgrounds in a new art style. With 6 locations, that meant creating 12+ background images (horizontal + vertical for each). Three locations (beach, forest, chubs_office) were rarely used and didn't add meaningful variety to episode settings. Reducing locations simplifies asset management and focuses the show's visual identity.

**Decision:** Simplified from 6 locations to 4:
- `diner` (renamed from `diner_interior` for consistency) — kept as the primary location
- `farmers_market` (new) — replaces beach/forest as the outdoor location
- `town_square` — kept unchanged
- `reows_place` — kept unchanged
- Removed: `beach`, `forest`, `chubs_office`

Each location has both horizontal (1920x1080) and vertical (1080x1920) single-file backgrounds. The scene builder auto-selects the correct orientation based on render target dimensions. All situation `best_locations` arrays updated — removed locations mapped to the most thematically appropriate remaining location (e.g., beach → farmers_market, chubs_office → diner).

**Alternative considered:** Keep all 6 locations and generate backgrounds for each. Rejected — the 3 removed locations were rarely selected by the slot machine, added maintenance burden, and didn't meaningfully expand the show's world. Fewer, better-crafted locations serve the visual quality goals of the Bootoshi redesign.

---

## D-023: YouTube dual-publish (2026-02-18)

**Context:** After Stage 4 added dual format rendering (horizontal 1920x1080 + vertical 1080x1920), both videos were uploaded to Google Drive but only one was published to YouTube. The horizontal video should be a regular YouTube video; the vertical video should be a YouTube Short. YouTube classifies Shorts by the `#Shorts` hashtag in the description plus vertical aspect ratio.

**Decision:** Added `is_short` parameter to `publish_to_youtube()`. When `is_short=False` (default), `#Shorts` is stripped from both title and description using regex. When `is_short=True`, `#Shorts` is kept/appended. Pipeline Step 7 now calls `publish_to_youtube` twice: once for horizontal (regular YouTube, `is_short=False`) and once for vertical (YouTube Short, `is_short=True`). Each upload has independent error handling and Discord notifications.

**Alternative considered:** Separate metadata generation for regular vs. Shorts (different titles, descriptions). Rejected — the metadata generator already produces good content. Stripping `#Shorts` at the publisher level is simpler and keeps the metadata generator format-agnostic. If distinct metadata is needed later, it can be added without changing the publisher.

---

## D-022: Dialogue ducking (2026-02-18)

**Context:** Music at a constant volume competed with dialogue text. Viewers couldn't focus on reading when the music was prominent. Professional video and game audio uses "ducking" — automatically lowering background music when dialogue is active.

**Decision:** Added `generate_ducking_schedule()` to extract dialogue time ranges from the script. `_apply_ducking()` splits the music track at dialogue boundaries and applies an additional -6 dB during those segments. Ducking is enabled by default in `mix_episode_audio()` but can be disabled via `enable_ducking=False`. Combined with the base music volume reduction from -12 dB to -20 dB, music during dialogue sits at -26 dB — barely audible, letting the text and blips take focus.

**Alternative considered:** Sidechain compression (real-time volume reduction triggered by blip audio). Rejected — overkill for a pre-rendered pipeline. Pre-computed ducking schedule from the script is simpler, deterministic, and testable.

---

## D-021: Dual format rendering (2026-02-18)

**Context:** YouTube Shorts, TikTok, and Reels need 9:16 vertical video. Regular YouTube works best at 16:9 horizontal. Rendering a single format means missing half the distribution channels. Re-rendering from scratch doubles compute time but guarantees both outputs from the same script.

**Decision:** Introduced `RenderConfig` dataclass with `HORIZONTAL` (1920x1080) and `VERTICAL` (1080x1920) presets. All rendering functions (`render_dialogue_frames`, `build_scene_frames`, `compose_episode`, `generate_end_card_frames`) accept an optional `render_config` parameter. Pipeline calls `compose_episode` twice — once per format. Both videos uploaded to Google Drive. v1 backgrounds (1080x1920) map naturally to vertical format with no scaling; horizontal format resizes them. Parallax folders work for both.

**Alternative considered:** Crop-based approach (render at high res, crop differently for each format). Rejected — cropping a 16:9 frame to 9:16 loses 75% of the image, requiring completely different composition. Two full renders with format-specific layout is the right approach.

---

## D-020: Parallax background engine (2026-02-18)

**Context:** v1 backgrounds were single flat images. Videos looked static and lacked visual depth. Modern pixel art games use parallax scrolling (multi-layer backgrounds moving at different speeds) to create depth illusion.

**Decision:** Background system checks for `assets/backgrounds/{location}/` folder with ordered layers: `background.png` (depth 0.2), `midground.png` (depth 0.5), `foreground.png` (depth 0.8), `effects.png` (depth 0.9). Falls back to single `{location}.png` file. Camera movements shift layers at different parallax rates.

**Alternative considered:** Shader-based depth-of-field effect. Rejected — too complex for 2D pixel art pipeline. Layer-based parallax is the industry standard for 2D games and animation.

---

## D-019: Frame streaming to FFmpeg (2026-02-18)

**Context:** v1 saved every frame as a PNG file to disk, then FFmpeg read them back. For a 60-second episode at 30fps, that's 1800 PNG writes + 1800 PNG reads. Slow, creates thousands of temp files, and uses significant disk space.

**Decision:** Pipe raw RGB pixel data directly to FFmpeg's stdin via `subprocess.Popen`. Scene builder yields PIL Images via generator. Composer writes `frame.tobytes()` to pipe. Eliminates all intermediate frame files.

**Alternative considered:** Keep file-based but use RAM disk. Rejected — streaming is simpler, faster, and doesn't require OS-level configuration.

---

## D-018: 16:9 horizontal as primary format (2026-02-18)

**Context:** v1 output was 1080x1920 (9:16 vertical only, for YouTube Shorts/TikTok/Reels). YouTube regular videos perform better as 16:9 horizontal. Most content creators produce horizontal as primary and crop for vertical.

**Decision:** Primary render format is 1920x1080 (16:9 horizontal). Stage 4 will add automatic vertical (9:16) output from the same scene data. v1 character positions auto-scaled from 1080x1920 coordinates via `scale_position_v1()`.

**Alternative considered:** Keep vertical as primary. Rejected because YouTube regular content (horizontal) has better algorithmic reach and watch time than Shorts.

---

## D-017: Auto-publish both YouTube regular + YouTube Shorts (2026-02-18)

**Context:** v1 only published to YouTube Shorts (vertical). With the new dual-format system, we produce both a horizontal (16:9) and vertical (9:16) video. YouTube regular content gets more algorithmic reach and longer watch sessions than Shorts.

**Decision:** Call `publish_to_youtube()` twice per episode — once for the horizontal video (regular YouTube upload) and once for the vertical video (YouTube Shorts). Both use the same metadata with minor format-specific adjustments (#Shorts appended for vertical). YouTube privacy set to "unlisted" during testing, "public" for production.

**Alternative considered:** Only publishing horizontal to YouTube and vertical to Shorts/TikTok/Reels. Rejected because YouTube Shorts has a separate discovery algorithm that drives significant traffic.

---

## D-016: Mood-based music selection (2026-02-18)

**Context:** v1 variant system used per-variant music (main_theme, tense_theme, upbeat_theme) to differentiate 3 video variants. With variants removed, we need a single music track per episode that matches the story tone.

**Decision:** Script includes a `mood` field (playful, calm, tense) set during generation. The audio mixer auto-selects the matching track. Three music tracks needed: `playful.wav`, `calm.wav`, `tense.wav`. Zero picks from free tracks I recommend. Music ducking: reduce by additional -5dB during dialogue.

**Trade-off:** Less variety per episode, but a well-matched single track beats three random options. If the mood detection is wrong, the story still works — it's background music, not a score.

---

## D-015: Stream frames to FFmpeg via stdin — no temp files (2026-02-18)

**Context:** v1 saves every rendered frame as an individual PNG to disk, then runs FFmpeg over the directory. For a 30-second video at 30fps = 900 frames × 1920x1080 RGBA PNGs. On the 1GB VPS, this caused disk pressure and memory issues, especially when rendering 3 variants (2700 frames).

**Decision:** Pipe rendered frames directly to FFmpeg's stdin via `subprocess.Popen`. Each frame is encoded to raw bytes, written to FFmpeg, then garbage collected. No temp frame files ever touch disk. Only the final MP4 is saved.

**Alternative considered:** Keep temp files but clean up between variants. Rejected because even a single variant's 900 frames at 1920x1080 is ~7GB of raw RGBA data on disk.

---

## D-014: Parallax background engine with backward compatibility (2026-02-18)

**Context:** v1 uses single flat background images per location. v2 upgrades to multi-layer parallax backgrounds (3-4 layers per location) for depth. Zero creates new assets incrementally using Nano Banana Pro — not all locations will have layers at once.

**Decision:** New background loading checks for directory first (`backgrounds/{location}/background.png`, `midground.png`, `foreground.png`, optional `effects.png`). If directory doesn't exist, falls back to v1 flat file (`backgrounds/{location}.png`). Camera system controls parallax by moving layers at different speeds relative to camera position.

**Trade-off:** Backward compatibility adds a code path that eventually becomes dead code. Acceptable because Zero creates assets at his own pace and we can't block on art.

---

## D-013: Dual video format — 16:9 horizontal + 9:16 vertical (2026-02-18)

**Context:** v1 rendered only 9:16 vertical (1080x1920). YouTube penalizes vertical content in regular feed. TikTok and Reels require vertical. Zero wants both.

**Decision:** Render both formats from the same scene data. Horizontal (1920x1080) for regular YouTube. Vertical (1080x1920) for YouTube Shorts, TikTok, and Instagram Reels. Layout configs (text box position, character Y positions, text box size) vary per format. Both rendered sequentially using the same scene frames — camera, parallax, dialogue are identical, only layout differs.

**Impact:** ~2x render time vs single format. On a 2-4GB VPS, each format takes ~15-20 min = ~30-40 min total (vs ~45 min for v1's 3 variants). Net improvement since we render 2 videos instead of 3.

---

## D-012: Remove video variants — replace with dual-format output (2026-02-18)

**Context:** v1 generated 3 video variants (Standard, Upbeat, Tense) with different music and pacing, posted to #video-preview for Zero to pick. This tripled render time, required a human selection step, and added a failure point.

**Decision:** Remove variant system entirely. One script → one set of scene data → two output formats (horizontal + vertical). No human video selection step. The pipeline goes straight from video generation to Drive upload and YouTube publish.

**What's removed:** `variant_generator.py` (VARIANT_PRESETS, generate_variants, generate_single_variant, generate_custom_variant), #video-preview channel handler, video selection state machine states.

---

## D-011: Remove script review step (2026-02-18)

**Context:** v1 published each script to Notion, posted the link to Discord #script-review, and waited for Zero to approve or submit edits. This required checking Notion, reading the full script, and typing "approve" — every day. Zero wants to just pick an idea and get a video.

**Decision:** Remove script review entirely. After Zero picks an idea, the pipeline generates the script and immediately proceeds to video generation. No human review, no Notion link, no edit loop.

**Trade-off:** Zero loses the ability to tweak scripts before rendering. If a script is bad, the video is also bad. Acceptable because: (a) the story generator has been reliable in producing good scripts, (b) Zero rarely made edits in v1, (c) the time cost of daily review outweighs the occasional bad script.

---

## D-010: Remove Notion integration entirely (2026-02-18)

**Context:** v1 published scripts to Notion and was planned to publish analytics reports there. Notion added a dependency (API key, workspace setup, page formatting), an extra failure point, and another thing to check. Zero never opened the Notion pages — he read the script summary in Discord.

**Decision:** Remove all Notion code. Scripts are generated and used internally only — the pipeline posts a brief summary to Discord (episode ID, title, scene count, duration) as a notification, not for review. Analytics reports (future feature) will post directly to Discord.

**What's removed:** `src/notion/` directory (client.py, script_publisher.py, report_publisher.py), NOTION_API_KEY and NOTION_SCRIPTS_DB_ID env vars, Notion-related Discord messages.

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
