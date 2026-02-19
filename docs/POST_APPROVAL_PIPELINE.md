# How Your Video Gets Made (Post-Script Approval)

## What AI Does vs. What It Doesn't

**Claude AI (Anthropic API) is used for ONE thing:** writing the script. That's it. Everything after script approval is deterministic — no AI involved in the animation, video, sound, or publishing. It's all code + pre-made pixel art assets + FFmpeg.

---

## The Pipeline: Step by Step

### Step 1: You Approve the Script in Discord
In `#script-review`, you read the script and reply `!approve`. This kicks off video production.

### Step 2: Three Video Variants Are Rendered
The system generates 3 complete videos from the same script, each with different vibes:

| Variant | Music | Pacing | Punchline Hold |
|---------|-------|--------|----------------|
| Standard | Situation-matched (e.g. bouncy for everyday, tense for mystery) | Normal (1.0x) | 2 seconds |
| Upbeat | Energetic track | Faster (0.85x) | 1 second |
| Tense | Tense underscore | Slower (1.15x) | 3 seconds |

Each variant takes ~17 minutes to render on the VPS (3 scenes x ~5 min each + end card + encoding).

### Step 3: Frame-by-Frame Rendering (Pillow / PIL)
For each scene, the system builds every single frame as a PNG image:
- **Background:** Loads a pre-drawn pixel art background (e.g. `diner_interior.png`) and scales it to 1080x1920 (vertical/Shorts format) using nearest-neighbor scaling (keeps the pixels crispy, no blurring)
- **Characters:** Loads pre-drawn character sprites (each character has `idle.png` and `talking.png` states), positions them at predefined spots in the scene (e.g. `stool_1`, `booth_left`)
- **Dialogue boxes:** Renders an NES-style text box at the bottom of the frame with a typewriter animation — characters appear one at a time at 12 characters per second, using the "Press Start 2P" retro pixel font. Each character has their own name color. The full text holds on screen for 2 seconds after the typewriter finishes so viewers can read it.
- **End card:** A 3-second branded card with the episode title and "BLOBTOSHI" branding

A typical 3-scene episode produces ~2,000+ frames at 30fps.

### Step 4: Audio Mixing (pydub)
Three audio layers are mixed together into a single WAV file:
- **Background music** — looped to match episode length, reduced to -12dB so it doesn't drown out everything else. Music is pre-made WAV files in `assets/music/`
- **Sound effects** — placed at specific timestamps defined in the script (e.g. door slam at 3.2 seconds). Played at -3dB
- **Text blips** — small chirp sounds synced to the typewriter animation (one blip every 3 characters). Each character has their own unique blip sound. Played at -6dB

All audio assets are pre-made WAV files. No AI-generated audio.

### Step 5: Video Encoding (FFmpeg)
Two FFmpeg passes:
1. **Frames to Video:** All 2,000+ PNG frames are encoded into an H.264 MP4 at 30fps, 1080x1920 resolution, CRF 18 (high quality)
2. **Audio mux:** The mixed WAV audio is encoded to AAC at 128kbps and combined with the video

Final output: a single MP4 file, typically 5-8 MB, 45-90 seconds long.

### Step 6: You Pick a Variant in Discord
All 3 videos are posted to `#video-preview`. You watch them and reply `1`, `2`, or `3` to pick your favorite. You can also request a custom mix (e.g. "music from v2, pacing from v1") and the system renders a 4th version.

### Step 7: Upload to Google Drive
The selected video is uploaded to your Google Drive folder via the Google Drive API. Filename format: `ep0001_beach-day-delivery.mp4`.

### Step 8: Episode Numbering
The episode gets its real ID (e.g. `EP001`). During production it used a draft ID (`DRAFT-EP-001`) — the real number is only assigned at publish time so numbers stay sequential with no gaps.

### Step 9: Metadata Generation (No AI)
Platform-specific titles, descriptions, and hashtags are generated using a rules engine (not AI):
- **TikTok:** Short title (max 55 chars), 5 hashtags, casual tone
- **YouTube:** Title with "| Blobtoshi #Shorts" suffix, 15 tags, keyword-optimized description
- **Instagram:** Caption with CTA, 15 hashtags

A safety check scans all metadata for profanity, offensive content, and clickbait phrases.

### Step 10: Publishing Schedule Posted to Discord
A schedule is posted to `#publishing-log` showing when each platform will publish (staggered by 30 minutes). You can reply to override any metadata before it goes live.

### Step 11: Publishing to Platforms
- **YouTube Shorts:** Fully implemented — uploads via YouTube Data API v3 (resumable upload), sets title/description/tags, posts as #Shorts
- **TikTok:** API integration scaffolded but not yet implemented (pending API approval)
- **Instagram Reels:** API integration scaffolded but not yet implemented

### Step 12: Continuity Logging
Timeline events, running gags, and character developments from the episode are saved to local JSON files. Future scripts reference this data so Claude can write callbacks to previous episodes.

---

## Tools Summary

| Tool | What It Does | AI? |
|------|-------------|-----|
| **Claude Sonnet** (Anthropic API) | Writes the script | Yes — only step that uses AI |
| **Pillow (PIL)** | Renders every frame as a PNG (backgrounds, sprites, text boxes, compositing) | No |
| **Press Start 2P font** | Retro pixel font for dialogue boxes and end cards | No |
| **pydub** | Mixes music + SFX + text blips into a single audio track | No |
| **FFmpeg** | Encodes PNG frames to H.264 video, muxes audio as AAC | No |
| **Google Drive API** | Uploads final video to your Drive folder | No |
| **YouTube Data API v3** | Publishes to YouTube Shorts | No |
| **Notion API** | Archives the script as a Notion page | No |
| **Rules engine** (YAML config) | Generates titles, descriptions, hashtags per platform | No |

## All Visual and Audio Assets Are Pre-Made
- **Backgrounds:** Hand-drawn pixel art PNGs in `assets/backgrounds/`
- **Character sprites:** Hand-drawn pixel art PNGs in `assets/characters/{name}/` (idle + talking states)
- **Music:** Pre-composed WAV tracks in `assets/music/` (main_theme, tense_theme, upbeat_theme)
- **SFX:** Pre-recorded WAV files in `assets/sfx/`
- **Portraits:** Character face portraits in `assets/ui/portraits/`
- **Font:** Press Start 2P (Google Fonts, free) in `assets/ui/fonts/`

No assets are generated by AI. They were all created upfront.
