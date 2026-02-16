# MOOTOSHI — Technical Product Requirements Document (PRD)

## Island IP Automated Content Production Pipeline

**Version:** 2.0
**Created:** February 14, 2026
**Purpose:** Complete technical specification for Claude Code to build the Island IP content production pipeline. This document is the single source of truth for the entire system.
**Local Path:** `/Users/dhroov/Claude_Code_Projects/mootoshi`
**GitHub:** `github.com/dhroovmehta/mootoshi`
**Series Name:** TBD (referred to as "Island IP" throughout this document)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Discord Bot — Command Center](#3-discord-bot--command-center)
4. [Notion Integration](#4-notion-integration)
5. [Tool Selection Guide (Options per Task)](#5-tool-selection-guide)
6. [Project Directory Structure](#6-project-directory-structure)
7. [Data Schemas](#7-data-schemas)
8. [Module 1: Story Generator Engine](#8-module-1-story-generator-engine)
9. [Module 2: Continuity Engine](#9-module-2-continuity-engine)
10. [Module 3: Trending Topics & Seasonal Themes](#10-module-3-trending-topics--seasonal-themes)
11. [Module 4: Storyboard Renderer](#11-module-4-storyboard-renderer)
12. [Module 5: Text Box Renderer](#12-module-5-text-box-renderer)
13. [Module 6: Video Assembler](#13-module-6-video-assembler)
14. [Module 7: Audio Mixer](#14-module-7-audio-mixer)
15. [Module 8: Video Variant Generator](#15-module-8-video-variant-generator)
16. [Module 9: Metadata Generator](#16-module-9-metadata-generator)
17. [Module 10: Publishing & Scheduling](#17-module-10-publishing--scheduling)
18. [Module 11: Analytics & Feedback Loop](#18-module-11-analytics--feedback-loop)
19. [End-to-End Pipeline Orchestration](#19-end-to-end-pipeline-orchestration)
20. [Build Priority & Dependency Tree](#20-build-priority--dependency-tree)
21. [Error Handling & Quality Gates](#21-error-handling--quality-gates)
22. [Configuration & Environment Setup](#22-configuration--environment-setup)
23. [Step-by-Step Guides for Manual Tasks](#23-step-by-step-guides-for-manual-tasks)
24. [Decision Log](#24-decision-log)
25. [Legal & Compliance Notes](#25-legal--compliance-notes)

---

## 1. Project Overview

### 1.1 What We're Building

An automated content production pipeline that generates, assembles, and publishes short-form video episodes (30-45 seconds) featuring NES/8-bit pixel art animal characters on an island. The pipeline takes episode seed parameters as input and outputs platform-ready vertical video (9:16) published to TikTok, YouTube Shorts, and Instagram Reels.

The entire system is controlled through a Discord server with dedicated channels. The creator (you) interacts only through Discord. All documents (scripts, reports) live in Notion. Everything else is automated.

### 1.2 Core Constraints

- **No voice acting.** All dialogue is NES-style text boxes.
- **NES pixel art aesthetic.** All visuals are 8-bit style with limited color palettes.
- **Audio is chiptune music + retro SFX only.**
- **Child-safe content.** No profanity, violence, or mature themes.
- **Minimize costs.** Prefer free/open-source tools. Max budget: ~$50/month.
- **Claude Max subscription available** — Claude API calls for story generation are covered.
- **Claude Code is the primary build tool** for all scripts and automation.
- **Discord is the only human interface.** You never need to touch code, terminals, or dashboards.
- **Notion is the document layer.** Scripts and reports are published as Notion pages.

### 1.3 Target Output

- Minimum 1 episode per day across all 3 platforms (30+ episodes/month)
- Each episode: 30-45 seconds, 1080x1920 (9:16), MP4
- Automated from idea generation through publishing
- Human touchpoints: idea selection, script approval, video preview selection

### 1.4 The Characters

Six animal characters. All follow the [Sound]-sters naming convention with shortened nicknames.

| Character | Animal | Archetype | Comedy Function |
|-----------|--------|-----------|-----------------|
| **Pensters (Pens)** | Penguin | The Steady One | Deadpan straight man. Diet soda always in flipper. Max 5 words per line. |
| **Chubsters (Chubs)** | Grey Seal | The Mogul | Monetizes everything. Business jargon in casual contexts. |
| **Meowsters (Meows)** | Cat | The Diplomat | Overly formal. From the "United Meows of Ameowica." |
| **Oinksters (Oinks)** | Pig | The Heart | Diner owner. Everyman. Gets pulled into everyone's schemes. |
| **Quacksters (Quacks)** | Call Duck | The Investigator | Conspiracy theorist. Drives plot lines through paranoia. |
| **Reowsters (Reows)** | Bear (NOT cat) | The Wild Card | Chaos agent. Bursts in with wild energy and half-baked ideas. |

**Design references:** Pens inspired by Pen Pen (Evangelion). Reows inspired by Yogi Bear (Hanna-Barbera) visual + Top Cat meets Kramer personality. Reows being a bear named with a cat sound is intentional — never change this.

**Oinks owns the Main Street diner** — the central gathering place and most-used location.

### 1.5 Content Rules

- No hard limit on repeating character pairings
- No hard limit on number of characters per episode — depends on the story
- At least one full-cast episode per week
- Minimum 1 episode posted daily on each platform
- Characters have continuity — they remember past events, have running gags, show growth
- Trending topics and seasonal themes are factored into story generation
- Tone: playful, funny, unserious, clean, child-safe

---

## 2. System Architecture Overview

### 2.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     DAILY AUTOMATED PIPELINE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. IDEA GENERATION (Automated)                                  │
│     ├── Slot Machine picks episode parameters                    │
│     ├── Continuity Engine checks for callback opportunities      │
│     ├── Trending Topics module checks current trends             │
│     ├── Seasonal Theme module checks calendar events             │
│     └── Generates 2-3 episode concepts                           │
│              │                                                   │
│              ▼                                                   │
│  2. IDEA SELECTION (Human — Discord #idea-selection)             │
│     ├── Bot posts 2-3 options                                    │
│     ├── You reply with your pick                                 │
│     └── Bot kicks off script generation                          │
│              │                                                   │
│              ▼                                                   │
│  3. SCRIPT WRITING (Automated)                                   │
│     ├── Claude generates full episode script                     │
│     ├── Script validated automatically                           │
│     ├── Published to Notion as new page                          │
│     └── Link posted to Discord #script-review                    │
│              │                                                   │
│              ▼                                                   │
│  4. SCRIPT REVIEW (Human — Discord #script-review)               │
│     ├── You review script in Notion                              │
│     ├── Approve in Discord, OR                                   │
│     ├── Submit freeform edits in Discord                         │
│     │   ├── Claude interprets edits, rewrites script             │
│     │   ├── New Notion page created with changes                 │
│     │   └── Updated link posted in Discord — repeat review       │
│     └── On approval, bot kicks off video production              │
│              │                                                   │
│              ▼                                                   │
│  5. VIDEO PRODUCTION (Automated)                                 │
│     ├── Asset check (sprites, backgrounds, SFX, music)           │
│     ├── Text box rendering (frame-by-frame typewriter)           │
│     ├── Video assembly (FFmpeg compositing)                      │
│     ├── Audio mixing (music + SFX + text blips)                  │
│     └── Generate 2-3 video variants                              │
│         (different music, pacing, character positioning)          │
│              │                                                   │
│              ▼                                                   │
│  6. VIDEO PREVIEW (Human — Discord #video-preview)               │
│     ├── Bot posts links to 2-3 video versions                    │
│     ├── You pick one, OR                                         │
│     ├── Request changes (e.g. "music from v2, pacing from v1")   │
│     │   ├── System generates new version                         │
│     │   └── Posts updated link — repeat review                   │
│     └── On approval, bot kicks off metadata + scheduling         │
│              │                                                   │
│              ▼                                                   │
│  7. METADATA GENERATION (Automated)                              │
│     ├── Auto-generate titles, descriptions, hashtags per platform│
│     ├── Apply industry best-practice rules                       │
│     ├── Content safety scan                                      │
│     └── Post metadata log to Discord #publishing-log             │
│              │                                                   │
│              ▼                                                   │
│  8. SCHEDULING & PUBLISHING (Automated — no human input)         │
│     ├── Schedule for next optimal time slot                      │
│     ├── Stagger across platforms (30 min apart)                  │
│     ├── Upload to TikTok, YouTube Shorts, Instagram Reels        │
│     └── Log results in #publishing-log                           │
│              │                                                   │
│              ▼                                                   │
│  9. ANALYTICS (Automated — runs 24-48 hours after publish)       │
│     ├── Pull performance data from all platforms                 │
│     ├── Auto-adjust content weights for future episodes          │
│     └── Weekly: publish performance report to Notion             │
│         └── Link posted to Discord #weekly-analytics             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.11+ |
| LLM API | Anthropic Claude API (via Max subscription) | Latest (claude-sonnet-4-20250514) |
| Discord Bot | discord.py | Latest |
| Notion API | notion-client (Python) | Latest |
| Image Processing | Pillow (PIL) | Latest |
| Video Composition | FFmpeg | 6.0+ |
| Audio Processing | pydub + FFmpeg | Latest |
| HTTP Client | httpx (async) | Latest |
| Data Format | JSON (flat-file) → SQLite (at scale) | — |
| Scheduling | APScheduler (local) or n8n (orchestrated) | Latest |
| Testing | pytest | Latest |
| Config | PyYAML + python-dotenv | Latest |

---

## 3. Discord Bot — Command Center

### 3.1 Overview

The Discord bot is the single interface between you and the pipeline. It runs in a private Discord server with dedicated channels. You never need to touch code, terminals, or dashboards — everything happens through Discord messages.

### 3.2 Server Structure

```
MOOTOSHI SERVER
├── #idea-selection        — Daily: bot posts 2-3 episode ideas, you pick one
├── #script-review         — Bot posts Notion link to script, you approve/edit
├── #video-preview         — Bot posts 2-3 video versions, you pick/edit
├── #publishing-log        — Bot logs scheduled metadata, you intervene if needed
└── #weekly-analytics      — Bot posts Notion link to weekly performance report
```

### 3.3 Bot Implementation: Discord Bot Spec

**Framework:** discord.py (Python)

**Bot behavior per channel:**

#### #idea-selection

```
DAILY TRIGGER: Pipeline cron job (configurable time, e.g., 8:00 AM ET)

BOT POSTS:
"🎬 **Daily Episode Ideas — [Date]**

**Option 1:** Reows + Pens | Diner | Reows has invented a new food item 
and needs Pens to taste-test it. Callback: References the "theme park 
incident" from EP012.

**Option 2:** Quacks + Meows | Town Square | Quacks suspects Meows' 
diplomatic pouch contains classified diner menus. Trending tie-in: 
International Pancake Day.

**Option 3:** Full Cast | Diner | Reows proposes an island-wide talent 
show. Everyone's reaction reveals their deepest insecurities.

Reply with **1**, **2**, or **3**."

USER REPLIES: "2"

BOT RESPONDS:
"✅ Option 2 selected. Generating script now..."
[Triggers script generation pipeline]
```

**Input parsing:** Bot accepts "1", "2", "3", or natural language like "option 2" or "the second one" or "quacks and meows one".

#### #script-review

```
BOT POSTS (after script generation):
"📝 **Script Ready — EP024: The Diplomatic Pouch**

[Notion Link: https://notion.so/...]

Title: EP # 024 | The Diplomatic Pouch | Feb 15, 2026

Reply **approve** to proceed to video production.
Reply with edit notes to request changes."

USER REPLIES (approve): "approve"
BOT RESPONDS: "✅ Script approved. Starting video production..."

USER REPLIES (edits): "make quacks more paranoid in scene 2, 
and add a callback to the ketchup conspiracy from EP008"
BOT RESPONDS: "✏️ Revising script with your notes..."
[Claude rewrites script, publishes new Notion page]
"📝 **Updated Script — EP024: The Diplomatic Pouch (v2)**
[New Notion Link: https://notion.so/...]
Reply **approve** or submit more edits."
```

#### #video-preview

```
BOT POSTS (after video production):
"🎥 **Video Preview — EP024: The Diplomatic Pouch**

**Version 1:** Mystery theme music, standard pacing (34s)
[Video link or file]

**Version 2:** Town theme music, faster pacing (30s)
[Video link or file]

**Version 3:** Chill theme music, slower pacing with extended 
punchline hold (38s)
[Video link or file]

Reply with your pick (**1**, **2**, **3**) or request changes."

USER REPLIES: "use music from 1 but pacing from 2"
BOT RESPONDS: "🎬 Generating custom version..."
[System creates new version, posts link]
"🎥 **Updated Version — EP024: The Diplomatic Pouch (Custom)**
[Video link]
Reply **approve** or request more changes."

USER REPLIES: "approve"
BOT RESPONDS: "✅ Video approved. Generating metadata and scheduling..."
```

#### #publishing-log

```
BOT POSTS (automated — no response needed):
"📋 **Scheduled — EP024: The Diplomatic Pouch**

**TikTok** (10:00 AM ET)
Title: Quacks vs. the diplomatic pouch 🔍
Desc: When Meows brings a briefcase to the square, 
Quacks knows something's up. #pixelart #comedy #retro #animation
Hashtags: #pixelart #comedy #retro #animation #IslandIP

**YouTube Shorts** (10:30 AM ET)
Title: The Diplomatic Pouch | Island IP #Shorts
Desc: Quacks investigates Meows' suspicious briefcase. 
It's exactly what you think. Or is it?

**Instagram Reels** (11:00 AM ET)
Caption: Quacks will NOT rest until the truth is revealed. 
Spoiler: it's just lunch. Follow for more island chaos 🏝️
#pixelart #retrogaming #comedy #animation #IslandIP

⚠️ Reply to override any metadata before scheduled post time."

[After successful publishing:]
"✅ **Published — EP024: The Diplomatic Pouch**
TikTok: [link] ✅
YouTube: [link] ✅
Instagram: [link] ✅"
```

#### #weekly-analytics

```
BOT POSTS (automated — weekly, e.g., every Monday 9:00 AM):
"📊 **Weekly Performance Report — Week of Feb 10-16, 2026**

[Notion Link: https://notion.so/...]

Quick summary:
- Top episode: EP021 (Reows + Pens, Diner) — 12,400 total views
- Best completion rate: EP023 (Deadpan punchline) — 58%
- Rising character: Quacks (engagement up 34% week-over-week)
- System adjustment: Increasing Reows+Pens frequency by 15%

Full breakdown and recommendations in the report."
```

### 3.4 Bot Technical Requirements

```python
# Core dependencies
discord.py >= 2.3.0
python-dotenv >= 1.0.0

# Bot needs these Discord permissions:
# - Send Messages
# - Read Messages
# - Attach Files (for video previews)
# - Embed Links
# - Add Reactions

# Bot needs these intents:
# - message_content (to read user replies)
# - guilds
```

**Message handling logic:**
- Bot listens only in its designated channels
- Bot only responds to messages from authorized user(s) — your Discord user ID
- Bot ignores its own messages
- Each channel has its own message handler with context-aware parsing
- Bot maintains state (which episode is currently in which stage) via a simple JSON state file or SQLite

---

## 4. Notion Integration

### 4.1 Overview

Notion is the document layer. All scripts and reports are published as Notion pages in a dedicated workspace you've already set up.

### 4.2 Notion API Integration

```python
# Dependencies
notion-client >= 2.0.0

# Authentication
NOTION_API_KEY=secret_...          # Internal integration token
NOTION_SCRIPTS_DB_ID=...           # Database ID for episode scripts
NOTION_ANALYTICS_DB_ID=...         # Database ID for weekly reports
```

### 4.3 Script Pages

Every script is published as a new Notion page in the Scripts database.

**Page title format:** `EP # XXX | [Episode Title] | [Date]`

Example: `EP # 024 | The Diplomatic Pouch | Feb 15, 2026`

**Page properties:**
| Property | Type | Example |
|----------|------|---------|
| Episode Number | Number | 24 |
| Title | Title | The Diplomatic Pouch |
| Date | Date | 2026-02-15 |
| Status | Select | Draft / Approved / Published |
| Characters | Multi-select | Quacks, Meows |
| Location | Select | Town Square |
| Situation | Select | Mystery / Investigation |
| Punchline Type | Select | Reveal |
| Version | Number | 1 |
| Parent Version | Relation | (link to previous version if this is an edit) |

**Page body content:** The full episode script in readable format — scene-by-scene with dialogue, stage directions, SFX cues, and timing notes. Formatted for easy human reading, not raw JSON.

**Version control:** Edits create a NEW page (e.g., `EP # 024 | The Diplomatic Pouch | Feb 15, 2026 (v2)`). The new page links back to the original via the Parent Version relation. This gives you full version history in Notion.

### 4.4 Analytics Report Pages

Weekly performance reports are published as Notion pages in the Analytics database.

**Page title format:** `Weekly Report | [Start Date] - [End Date]`

**Page body content:** Performance metrics, character rankings, pairing analysis, punchline type effectiveness, platform breakdown, trending insights, and system adjustments made.

---

## 5. Tool Selection Guide

For each task in the pipeline, here are the options ranked by recommendation. The **Primary** choice is what the pipeline is built around. **Alternatives** are viable substitutes.

### 5.1 Story/Script Generation

| Option | Cost | Pros | Cons | Verdict |
|--------|------|------|------|---------|
| **Claude API (via Max sub)** | $0 additional | Best creative writing, structured JSON output, already subscribed | Rate limits on Max plan | **PRIMARY** |
| OpenAI GPT-4o API | ~$5-15/mo | Good structured output | Additional cost, less creative for character voice | Alternative |
| Local LLM (Llama 3) | $0 (hardware) | No API costs, no rate limits | Lower quality for comedy writing, needs GPU | Not recommended |

### 5.2 Character & Background Art Generation

| Option | Cost | Pros | Cons | Verdict |
|--------|------|------|------|---------|
| **Midjourney v6** | $10-30/mo | Best aesthetic quality for concept art | No API, Discord-only | **PRIMARY for initial design** |
| **PixelLab** | $15/mo | Purpose-built pixel art, sprite animation | Narrower tool | **Best for sprite refinement** |
| Leonardo AI | $12/mo | API available, good control | Less polished than Midjourney | Alternative |
| Flux (open source) | $0 (GPU) | Free, LoRA training for character consistency | Setup complexity | Future option |

### 5.3 Sprite Animation

| Option | Cost | Pros | Cons | Verdict |
|--------|------|------|------|---------|
| **Aseprite** | $20 one-time | Industry standard pixel art animation | Manual tool | **PRIMARY** |
| Piskel | $0 (free, browser) | Free, good for basics | Limited features | Starter alternative |
| PixelLab animation | $15/mo (bundled) | AI-assisted | Less control | Complement |

### 5.4 Video Composition

| Option | Cost | Pros | Cons | Verdict |
|--------|------|------|------|---------|
| **FFmpeg (scripted)** | $0 (free) | Fully automatable | No GUI | **PRIMARY for automation** |
| **CapCut** | $0 (free) | Easy GUI | Not automatable | **Manual phase only** |
| Remotion (React) | $0 (free) | Programmatic, great for text animation | Complex setup | Strong alternative |
| MoviePy (Python) | $0 (free) | Python-native | Slower rendering | Simpler alternative |

### 5.5 Text Box Rendering

| Option | Cost | Pros | Cons | Verdict |
|--------|------|------|------|---------|
| **PIL/Pillow (Python)** | $0 (free) | Full control, pixel-perfect | Build from scratch | **PRIMARY** |
| Pygame | $0 (free) | Game-native rendering | Heavier dependency | Alternative |

### 5.6 Audio / Music

| Option | Cost | Pros | Cons | Verdict |
|--------|------|------|------|---------|
| **Royalty-free chiptune libraries** | $0 | Immediate, no production needed | Limited variety | **PRIMARY for launch** |
| **jsfxr / sfxr** | $0 (browser) | Retro SFX generation | SFX only | **PRIMARY for SFX** |
| FamiTracker | $0 (free) | Authentic NES composition | Learning curve | Future original music |
| Suno AI | $10/mo | AI-generated chiptune | Quality varies | Alternative |

### 5.7 Scheduling & Publishing

| Option | Cost | Pros | Cons | Verdict |
|--------|------|------|------|---------|
| **n8n (self-hosted)** | $0 (free) | Fully automatable, visual workflow | Setup complexity | **PRIMARY for automation** |
| n8n (cloud) | $20/mo | Same, no hosting | Monthly cost | Easier alternative |
| **Buffer** | $0 (free tier) | Simple scheduling UI | Not fully automatable | **Manual phase** |
| Custom Python (direct API) | $0 | Full control | Must manage each API | Fallback |

### 5.8 Analytics

| Option | Cost | Pros | Cons | Verdict |
|--------|------|------|------|---------|
| **Platform native APIs** | $0 | Direct, most accurate | Integrate each separately | **PRIMARY data source** |
| **JSON flat-file** | $0 | Simple, no database | Doesn't scale past ~1000 eps | **PRIMARY storage for MVP** |
| SQLite | $0 | Structured queries | Slightly more complex | Upgrade path |

---

## 6. Project Directory Structure

```
mootoshi/
├── README.md
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
│
├── config/
│   ├── pipeline.yaml                # Master pipeline configuration
│   ├── platforms.yaml               # Platform API credentials and settings
│   ├── scheduling.yaml              # Posting schedule rules
│   ├── metadata_rules.yaml          # Title/description/hashtag generation rules
│   ├── quality_gates.yaml           # Automated quality check thresholds
│   └── discord.yaml                 # Discord server/channel IDs, authorized users
│
├── data/
│   ├── characters.json              # Character definitions
│   ├── situations.json              # Situation templates
│   ├── punchlines.json              # Punchline type definitions
│   ├── locations.json               # Location/background definitions
│   ├── continuity/
│   │   ├── timeline.json            # Episode event log for callbacks
│   │   ├── running_gags.json        # Active running gag tracker
│   │   └── character_growth.json    # Character development log
│   ├── episodes/
│   │   ├── index.json               # Episode master index
│   │   └── EP001/
│   │       ├── script.json          # Generated script
│   │       ├── storyboard.json      # Visual storyboard plan
│   │       ├── metadata.json        # Production metadata
│   │       ├── variants/            # Video variant files
│   │       └── analytics.json       # Performance data
│   └── analytics/
│       ├── daily_summary.json
│       ├── weekly_reports/
│       ├── character_performance.json
│       └── content_weights.json     # Auto-adjusted generation weights
│
├── assets/
│   ├── characters/
│   │   ├── pens/
│   │   │   ├── idle.png
│   │   │   ├── talking.png
│   │   │   ├── sipping.png
│   │   │   ├── reaction_surprise.png
│   │   │   ├── reaction_deadpan.png
│   │   │   ├── walking.png
│   │   │   └── metadata.json        # Sprite dimensions, frame counts, anchor points
│   │   ├── chubs/
│   │   ├── meows/
│   │   ├── oinks/
│   │   ├── quacks/
│   │   └── reows/
│   ├── backgrounds/
│   │   ├── diner_interior.png
│   │   ├── beach.png
│   │   ├── forest.png
│   │   ├── town_square.png
│   │   ├── chubs_office.png
│   │   └── reows_place.png
│   ├── ui/
│   │   ├── textbox_template.png
│   │   ├── endcard_template.png
│   │   ├── fonts/
│   │   │   └── PressStart2P-Regular.ttf
│   │   └── portraits/
│   │       ├── pens_portrait.png
│   │       └── ...
│   ├── music/
│   │   ├── town_theme.ogg
│   │   ├── adventure_theme.ogg
│   │   ├── mystery_theme.ogg
│   │   ├── chill_theme.ogg
│   │   ├── silly_theme.ogg
│   │   └── LICENSES.md              # Music license documentation
│   └── sfx/
│       ├── text_blip_low.wav
│       ├── text_blip_mid.wav
│       ├── text_blip_high.wav
│       ├── text_blip_warm.wav
│       ├── text_blip_quick.wav
│       ├── text_blip_bold.wav
│       ├── door_burst.wav
│       ├── surprise.wav
│       ├── sip.wav
│       ├── cash_register.wav
│       ├── magnifying_glass.wav
│       └── menu_select.wav
│
├── src/
│   ├── __init__.py
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── bot.py                   # Main Discord bot
│   │   ├── handlers/
│   │   │   ├── idea_selection.py    # #idea-selection channel handler
│   │   │   ├── script_review.py     # #script-review channel handler
│   │   │   ├── video_preview.py     # #video-preview channel handler
│   │   │   ├── publishing_log.py    # #publishing-log channel handler
│   │   │   └── analytics.py         # #weekly-analytics channel handler
│   │   └── state.py                 # Pipeline state manager
│   ├── notion/
│   │   ├── __init__.py
│   │   ├── client.py                # Notion API client wrapper
│   │   ├── script_publisher.py      # Publish scripts to Notion
│   │   └── report_publisher.py      # Publish analytics reports to Notion
│   ├── story_generator/
│   │   ├── __init__.py
│   │   ├── engine.py                # Main story generation engine
│   │   ├── slot_machine.py          # Random episode seed generator
│   │   ├── prompts.py               # Claude prompt templates
│   │   └── validator.py             # Script validation
│   ├── continuity/
│   │   ├── __init__.py
│   │   ├── engine.py                # Continuity tracking engine
│   │   ├── callback_finder.py       # Find callback opportunities
│   │   └── gag_tracker.py           # Running gag management
│   ├── trends/
│   │   ├── __init__.py
│   │   ├── trending.py              # Trending topic discovery
│   │   └── seasonal.py              # Seasonal/calendar theme engine
│   ├── storyboard/
│   │   ├── __init__.py
│   │   └── renderer.py              # Storyboard preview generator
│   ├── text_renderer/
│   │   ├── __init__.py
│   │   ├── renderer.py              # NES text box frame generator
│   │   └── fonts.py                 # Font loading
│   ├── video_assembler/
│   │   ├── __init__.py
│   │   ├── composer.py              # Main FFmpeg composition pipeline
│   │   ├── scene_builder.py         # Per-scene frame generation
│   │   ├── sprite_manager.py        # Character sprite positioning
│   │   ├── variant_generator.py     # Generate 2-3 video variants
│   │   └── transitions.py           # Scene transitions
│   ├── audio_mixer/
│   │   ├── __init__.py
│   │   └── mixer.py                 # Music + SFX + blip mixing
│   ├── metadata/
│   │   ├── __init__.py
│   │   ├── generator.py             # Platform-specific metadata generator
│   │   ├── safety_check.py          # Content safety scanner
│   │   └── rules.py                 # Metadata rules engine
│   ├── publisher/
│   │   ├── __init__.py
│   │   ├── tiktok.py
│   │   ├── youtube.py
│   │   ├── instagram.py
│   │   ├── scheduler.py             # Posting schedule manager
│   │   └── formatter.py             # Platform metadata formatting
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── collector.py             # Pull data from platform APIs
│   │   ├── analyzer.py              # Performance analysis
│   │   └── feedback.py              # Auto-adjust content weights
│   └── pipeline/
│       ├── __init__.py
│       ├── orchestrator.py          # End-to-end pipeline runner
│       └── quality_gate.py          # Quality checks between stages
│
├── templates/
│   ├── claude_story_prompt.txt      # Master prompt for story generation
│   ├── claude_edit_prompt.txt       # Prompt for interpreting edit notes
│   ├── claude_metadata_prompt.txt   # Prompt for metadata generation
│   └── episode_metadata_template.json
│
├── tests/
│   ├── test_story_generator.py
│   ├── test_continuity.py
│   ├── test_text_renderer.py
│   ├── test_video_assembler.py
│   ├── test_metadata.py
│   └── test_publisher.py
│
├── output/                          # Final rendered videos
│
├── guides/                          # Step-by-step guides for manual tasks
│   ├── 01_discord_server_setup.md
│   ├── 02_notion_workspace_setup.md
│   ├── 03_platform_account_setup.md
│   ├── 04_midjourney_character_design.md
│   ├── 05_pixellab_sprite_creation.md
│   ├── 06_aseprite_sprite_sheets.md
│   ├── 07_background_creation.md
│   ├── 08_sound_effects_creation.md
│   ├── 09_chiptune_music_sourcing.md
│   └── 10_api_key_setup.md
│
└── n8n/
    ├── daily_pipeline.json
    └── analytics_pull.json
```

---

## 7. Data Schemas

### 7.1 characters.json

```json
{
  "characters": {
    "pens": {
      "full_name": "Pensters",
      "nickname": "Pens",
      "animal": "Penguin",
      "archetype": "The Steady One",
      "personality_traits": ["chill", "dependable", "unshakeable", "reliable", "level-headed", "quietly smart", "laconic"],
      "comedy_function": "The straight man. Deadpan reactions to chaos. The audience laughs because Pens doesn't.",
      "signature_prop": "diet soda (always in flipper)",
      "catchphrases": ["...cool.", "I'm good.", "*sips diet soda*", "...yep.", "Sounds like a you problem."],
      "dialogue_style": "Minimal. 1-5 words max per line. Never explains himself. Uses ellipses frequently.",
      "visual_notes": "Short, round black and white body, small flipper-wings, maroon crest on head. Diet soda always visible.",
      "design_reference": "Pen Pen from Neon Genesis Evangelion",
      "relationships": {
        "reows": "Tolerates his chaos with quiet amusement. The odd couple.",
        "oinks": "Quiet comfortable friendship. Can sit in silence together.",
        "quacks": "Listens to theories without judgment. Neither agrees nor disagrees.",
        "chubs": "Respects the hustle. Occasionally gives surprisingly sharp business advice.",
        "meows": "Finds the formality mildly entertaining."
      },
      "sprite_states": ["idle", "talking", "sipping", "reaction_surprise", "reaction_deadpan", "walking"],
      "text_blip_sound": "text_blip_low.wav",
      "name_color": "#4FC3F7"
    },
    "chubs": {
      "full_name": "Chubsters",
      "nickname": "Chubs",
      "animal": "Grey Seal",
      "archetype": "The Mogul",
      "personality_traits": ["business-minded", "opportunistic", "friendly", "analytical", "always networking", "genuinely generous"],
      "comedy_function": "Monetizes everything. Sees business opportunities in the most inappropriate situations.",
      "signature_prop": "small tie or briefcase",
      "catchphrases": ["What's the ROI on that?", "I see a market opportunity here.", "Let me run the numbers.", "Have you considered franchising?", "This is bullish."],
      "dialogue_style": "Business jargon in casual contexts. Speaks in pitches. Medium-length lines.",
      "visual_notes": "Large, round, blob-like seal body. Widest silhouette. Small tie. Briefcase when walking.",
      "design_reference": "Generic seal with business accessories",
      "relationships": {
        "reows": "Torn between friendship and financial sense when Reows pitches ideas.",
        "meows": "Mutual respect. Both take themselves seriously.",
        "oinks": "Frequent customer. Has suggested 'optimizing the menu' multiple times.",
        "pens": "Pens occasionally drops surprisingly good business advice.",
        "quacks": "Gets nervous when Quacks investigates his 'business dealings.'"
      },
      "sprite_states": ["idle", "talking", "calculating", "excited", "reaction_nervous", "walking"],
      "text_blip_sound": "text_blip_mid.wav",
      "name_color": "#78909C"
    },
    "meows": {
      "full_name": "Meowsters",
      "nickname": "Meows",
      "animal": "Cat",
      "archetype": "The Diplomat",
      "personality_traits": ["refined", "formal", "worldly", "connected", "polished", "good-hearted underneath"],
      "comedy_function": "Overly formal in casual situations. Treats simple interactions like diplomatic negotiations.",
      "signature_prop": "monocle or top hat (TBD based on pixel art testing)",
      "catchphrases": ["On behalf of the United Meows of Ameowica...", "I shall consult with my embassy.", "This is a matter of international importance.", "Per the accords...", "How... provincial."],
      "dialogue_style": "Formal, diplomatic language. Long sentences with unnecessary gravitas.",
      "visual_notes": "Upright cat, sleek posture. Monocle or top hat for diplomacy flair.",
      "design_reference": "Refined aristocratic housecat",
      "relationships": {
        "chubs": "Professional mutual respect.",
        "reows": "Finds him fascinating and horrifying in equal measure.",
        "oinks": "Treats ordering at the diner like a state dinner.",
        "quacks": "Quacks suspects him of being a spy. Meows is oblivious.",
        "pens": "Mildly entertained by Pens' brevity."
      },
      "sprite_states": ["idle", "talking", "refined_pose", "reaction_appalled", "reaction_pleased", "walking"],
      "text_blip_sound": "text_blip_high.wav",
      "name_color": "#CE93D8"
    },
    "oinks": {
      "full_name": "Oinksters",
      "nickname": "Oinks",
      "animal": "Pig",
      "archetype": "The Heart (Comic Relief)",
      "personality_traits": ["good-natured", "well-rounded", "relatable", "slightly goofy", "hardworking", "long-suffering"],
      "comedy_function": "The everyman. Pig running a diner. Gets pulled into everyone's schemes.",
      "signature_prop": "apron (diner owner)",
      "catchphrases": ["Can I just get someone to order something?", "That's not on the menu.", "I'm not cleaning that up.", "Welcome to the diner, what can I—", "*sighs*"],
      "dialogue_style": "Normal, relatable speech. Exasperated reactions. The only character who talks like a regular person.",
      "visual_notes": "Medium-round pig body with apron. Often holding a plate or towel.",
      "design_reference": "Friendly cartoon pig with diner worker accessories",
      "role_in_world": "Owns and operates the Main Street diner — the central gathering place.",
      "relationships": {
        "everyone": "Everyone comes to Oinks. He's the social hub.",
        "reows": "Reows' 'help' always makes things worse.",
        "quacks": "Gets interrogated about mundane diner things regularly.",
        "pens": "Quiet, comfortable friendship.",
        "chubs": "Best customer. Worst backseat manager.",
        "meows": "Takes way too long to order."
      },
      "sprite_states": ["idle", "talking", "serving", "wiping_counter", "reaction_exasperated", "walking"],
      "text_blip_sound": "text_blip_warm.wav",
      "name_color": "#F48FB1"
    },
    "quacks": {
      "full_name": "Quacksters",
      "nickname": "Quacks",
      "animal": "Call Duck",
      "archetype": "The Investigator",
      "personality_traits": ["industrious", "curious", "paranoid", "pattern-seeking", "determined", "conspiracy-minded"],
      "comedy_function": "Conspiracy theorist plot engine. Investigates mundane things. Connects dots that aren't there.",
      "signature_prop": "magnifying glass or small notebook",
      "catchphrases": ["That's EXACTLY what they want you to think.", "Something doesn't add up here.", "I've been tracking this for weeks.", "Wake up, people.", "Follow the breadcrumbs."],
      "dialogue_style": "Intense, conspiratorial whisper energy. Uses 'they' and 'them' without referencing anyone specific.",
      "visual_notes": "Small, compact call duck. Smallest silhouette. Magnifying glass or notebook.",
      "design_reference": "Mini detective duck",
      "relationships": {
        "oinks": "Primary interrogation target.",
        "reows": "Wild ideas accidentally validate theories. Dangerous pairing.",
        "meows": "Suspects Meows is a foreign agent.",
        "pens": "Tries to recruit Pens for investigations. Pens declines.",
        "chubs": "Follows the money."
      },
      "sprite_states": ["idle", "talking", "investigating", "suspicious", "eureka", "walking"],
      "text_blip_sound": "text_blip_quick.wav",
      "name_color": "#FFD54F"
    },
    "reows": {
      "full_name": "Reowsters",
      "nickname": "Reows",
      "animal": "Bear",
      "archetype": "The Wild Card",
      "personality_traits": ["free-spirited", "eccentric", "confident", "chaotic", "endlessly enthusiastic", "physical comedy magnet"],
      "comedy_function": "Chaos agent. Bursts into scenes with wild energy and half-baked ideas delivered with total confidence.",
      "signature_prop": "white collar and blue pork pie hat with white center (Yogi Bear style)",
      "catchphrases": ["GUYS. I just had the GREATEST idea.", "Trust me on this one.", "What could possibly go wrong?", "You're gonna love this.", "I know a guy."],
      "dialogue_style": "High energy, exclamation points, ALL CAPS for emphasis. Long enthusiastic rants.",
      "visual_notes": "Large bear. White collar around neck, blue pork pie hat with white center. Brown fur with lighter brown patches on belly, face, and inner ears. Biggest silhouette. Always in motion.",
      "design_reference": "Yogi Bear (Hanna-Barbera) visual. Top Cat meets Kramer personality.",
      "name_note": "'Reow' is a cat sound. Reows is a bear. This is INTENTIONAL. Do not change.",
      "relationships": {
        "pens": "The classic odd couple. Chaos meets calm. Highest comedy potential.",
        "chubs": "Pitches terrible business ideas with total confidence.",
        "quacks": "Wild ideas accidentally validate conspiracy theories.",
        "oinks": "Tries to 'help' at the diner. Makes everything worse.",
        "meows": "Fascinates and horrifies the diplomat in equal measure."
      },
      "sprite_states": ["idle", "talking", "burst_entrance", "excited", "scheming", "walking"],
      "text_blip_sound": "text_blip_bold.wav",
      "name_color": "#A1887F"
    }
  }
}
```

### 7.2 situations.json

```json
{
  "situations": {
    "everyday_life": {
      "id": "everyday_life",
      "name": "Everyday Life",
      "description": "Relatable daily situations — ordering food, waiting, small talk",
      "best_locations": ["diner_interior", "town_square", "beach"],
      "templates": [
        "{char_a} tries to order food but {char_b} complicates it",
        "{char_a} and {char_b} are waiting for something that never comes",
        "{char_a} asks {char_b} a simple question that spirals",
        "{char_a} has a minor inconvenience that {char_b} makes worse",
        "{char_a} tries to relax but {char_b} keeps interrupting"
      ]
    },
    "mystery_investigation": {
      "id": "mystery_investigation",
      "name": "Mystery / Investigation",
      "description": "Quacks-driven — something mundane gets blown out of proportion",
      "best_locations": ["diner_interior", "forest", "town_square"],
      "best_characters": ["quacks"],
      "templates": [
        "{char_a} notices something 'suspicious' about {location}",
        "{char_a} interrogates {char_b} about a mundane change",
        "{char_a} builds a conspiracy theory about {everyday_thing}",
        "{char_a} tries to recruit {char_b} for an investigation",
        "{char_a} connects two completely unrelated events"
      ]
    },
    "scheme_adventure": {
      "id": "scheme_adventure",
      "name": "Scheme / Adventure",
      "description": "Reows-driven — a wild idea, someone gets dragged along",
      "best_locations": ["beach", "forest", "diner_interior"],
      "best_characters": ["reows"],
      "templates": [
        "{char_a} has a 'great idea' and needs {char_b}'s help",
        "{char_a} found something 'amazing' and drags {char_b} to see it",
        "{char_a} tries to 'improve' something that was fine",
        "{char_a} claims to have a new skill and demonstrates it poorly",
        "{char_a} pitches a plan with total confidence. It's terrible."
      ]
    },
    "business_opportunity": {
      "id": "business_opportunity",
      "name": "Business Opportunity",
      "description": "Chubs-driven — everything is a deal, a pitch, or an optimization",
      "best_locations": ["diner_interior", "chubs_office", "town_square"],
      "best_characters": ["chubs"],
      "templates": [
        "{char_a} tries to monetize {everyday_thing}",
        "{char_a} pitches a 'partnership' to {char_b} for something absurd",
        "{char_a} runs the numbers on {char_b}'s hobby",
        "{char_a} tries to franchise the diner (again)",
        "{char_a} gives unsolicited business advice to {char_b}"
      ]
    },
    "diplomatic_incident": {
      "id": "diplomatic_incident",
      "name": "Diplomatic Incident",
      "description": "Meows-driven — formality meets casual island life",
      "best_locations": ["diner_interior", "town_square"],
      "best_characters": ["meows"],
      "templates": [
        "{char_a} treats a simple interaction as a diplomatic negotiation",
        "{char_a} invokes a nonexistent treaty or accord",
        "{char_a} tries to establish formal protocols for {everyday_thing}",
        "{char_a} sends a formal communique about a casual invitation",
        "{char_a} holds a press conference about {mundane_event}"
      ]
    },
    "chill_hangout": {
      "id": "chill_hangout",
      "name": "Chill Hangout",
      "description": "Pens-driven — calm vibes while chaos happens around him",
      "best_locations": ["diner_interior", "beach"],
      "best_characters": ["pens"],
      "templates": [
        "{char_a} just wants to sit quietly but {char_b} has other plans",
        "{char_a} and {char_b} have a comfortable silence interrupted by {char_c}",
        "{char_a} gives one-word advice that accidentally solves everything",
        "{char_a} watches chaos unfold without reacting",
        "{char_a} is asked to choose a side. Refuses. Sips diet soda."
      ]
    }
  }
}
```

### 7.3 punchlines.json

```json
{
  "punchline_types": {
    "deadpan": {
      "id": "deadpan",
      "name": "The Deadpan",
      "description": "A character's complete nonreaction IS the joke",
      "best_characters": ["pens"],
      "execution": "Final dialogue line is 1-3 words of total underreaction. Hold on the deadpan face for 2 seconds."
    },
    "backfire": {
      "id": "backfire",
      "name": "The Backfire",
      "description": "The plan goes comically wrong",
      "best_characters": ["reows", "chubs"],
      "execution": "Build up confidence, then instant reversal. Quick cut to aftermath."
    },
    "misunderstanding": {
      "id": "misunderstanding",
      "name": "The Misunderstanding",
      "description": "Characters talk past each other completely",
      "best_characters": ["meows", "oinks"],
      "execution": "Two characters having two different conversations simultaneously."
    },
    "escalation": {
      "id": "escalation",
      "name": "The Escalation",
      "description": "A small thing spirals absurdly out of control",
      "best_characters": ["quacks", "reows"],
      "execution": "Start mundane, each beat doubles the absurdity."
    },
    "reveal": {
      "id": "reveal",
      "name": "The Reveal",
      "description": "The conspiracy theory turns out to be wrong (or hilariously right)",
      "best_characters": ["quacks"],
      "execution": "Build suspense, dramatic pause, then the mundane (or insane) truth."
    },
    "entrance": {
      "id": "entrance",
      "name": "The Entrance",
      "description": "A character bursts in and changes everything",
      "best_characters": ["reows"],
      "execution": "Calm scene disrupted by explosive entrance."
    }
  }
}
```

### 7.4 locations.json

```json
{
  "locations": {
    "diner_interior": {
      "id": "diner_interior",
      "name": "Oinks' Diner",
      "background_file": "diner_interior.png",
      "description": "Classic American diner. Counter with stools, booths, neon sign. Menu board in background.",
      "default_music": "town_theme.ogg",
      "character_positions": {
        "behind_counter": {"x": 200, "y": 600, "facing": "right"},
        "stool_1": {"x": 400, "y": 650, "facing": "left"},
        "stool_2": {"x": 550, "y": 650, "facing": "left"},
        "stool_3": {"x": 700, "y": 650, "facing": "left"},
        "booth_left": {"x": 150, "y": 500, "facing": "right"},
        "booth_right": {"x": 350, "y": 500, "facing": "left"},
        "door_entrance": {"x": 900, "y": 600, "facing": "left"}
      },
      "mood": "warm, cozy, everyday"
    },
    "beach": {
      "id": "beach",
      "name": "Island Beach",
      "background_file": "beach.png",
      "description": "Sandy beach with ocean, palm trees, blue sky.",
      "default_music": "chill_theme.ogg",
      "character_positions": {
        "left_sand": {"x": 200, "y": 700, "facing": "right"},
        "right_sand": {"x": 700, "y": 700, "facing": "left"},
        "water_edge": {"x": 450, "y": 750, "facing": "down"},
        "under_palm": {"x": 100, "y": 600, "facing": "right"}
      },
      "mood": "relaxed, bright, adventurous"
    },
    "forest": {
      "id": "forest",
      "name": "Island Forest",
      "background_file": "forest.png",
      "description": "Dense pixel trees, dappled light, mossy ground.",
      "default_music": "mystery_theme.ogg",
      "character_positions": {
        "clearing_left": {"x": 250, "y": 650, "facing": "right"},
        "clearing_right": {"x": 650, "y": 650, "facing": "left"},
        "path_center": {"x": 450, "y": 700, "facing": "down"}
      },
      "mood": "mysterious, adventurous"
    },
    "town_square": {
      "id": "town_square",
      "name": "Town Square",
      "background_file": "town_square.png",
      "description": "Open square with fountain, benches, storefronts.",
      "default_music": "town_theme.ogg",
      "character_positions": {
        "bench_left": {"x": 200, "y": 650, "facing": "right"},
        "bench_right": {"x": 600, "y": 650, "facing": "left"},
        "fountain_center": {"x": 400, "y": 600, "facing": "down"},
        "standing_left": {"x": 150, "y": 700, "facing": "right"},
        "standing_right": {"x": 750, "y": 700, "facing": "left"}
      },
      "mood": "public, social, daytime"
    },
    "chubs_office": {
      "id": "chubs_office",
      "name": "Chubs' Office",
      "background_file": "chubs_office.png",
      "description": "Small office with desk, charts on wall, nameplate.",
      "default_music": "town_theme.ogg",
      "character_positions": {
        "behind_desk": {"x": 450, "y": 550, "facing": "down"},
        "visitor_chair": {"x": 450, "y": 750, "facing": "up"}
      },
      "mood": "professional, slightly absurd"
    },
    "reows_place": {
      "id": "reows_place",
      "name": "Reows' Place",
      "background_file": "reows_place.png",
      "description": "Chaotic, eclectic room. Random items everywhere.",
      "default_music": "silly_theme.ogg",
      "character_positions": {
        "center": {"x": 450, "y": 650, "facing": "down"},
        "doorway": {"x": 800, "y": 650, "facing": "left"}
      },
      "mood": "chaotic, eccentric, energetic"
    }
  }
}
```

### 7.5 Episode Script Schema (Story Generator Output)

```json
{
  "episode_id": "EP024",
  "title": "The Diplomatic Pouch",
  "slug": "the-diplomatic-pouch",
  "created_at": "2026-02-15T10:30:00Z",
  "version": 1,
  "generation_params": {
    "character_a": "quacks",
    "character_b": "meows",
    "location": "town_square",
    "situation": "mystery_investigation",
    "punchline_type": "reveal",
    "trending_tie_in": "International Pancake Day",
    "seasonal_theme": null,
    "continuity_callbacks": [
      {"episode_id": "EP008", "reference": "ketchup conspiracy", "type": "running_gag"}
    ]
  },
  "duration_target_seconds": 35,
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 8,
      "background": "town_square",
      "characters_present": ["quacks", "meows"],
      "character_positions": {
        "quacks": "bench_left",
        "meows": "standing_right"
      },
      "character_animations": {
        "quacks": "suspicious",
        "meows": "walking"
      },
      "action_description": "Meows walks through town square carrying a briefcase. Quacks watches from a bench.",
      "dialogue": [
        {
          "character": "quacks",
          "text": "There he is. Right on schedule.",
          "animation_trigger": "suspicious",
          "duration_ms": 2500
        }
      ],
      "sfx_triggers": [
        {"sfx": "magnifying_glass", "time_ms": 500}
      ],
      "music": "mystery_theme.ogg"
    }
  ],
  "end_card": {
    "duration_seconds": 3,
    "text": "Follow for more island chaos!",
    "background": "endcard_template.png"
  },
  "continuity_log": {
    "events": ["Quacks investigated Meows' briefcase", "Briefcase contained pancakes"],
    "new_running_gags": ["Quacks now suspects all briefcases"],
    "character_developments": ["Meows revealed he bakes pancakes as a hobby"]
  },
  "metadata": {
    "total_duration_seconds": 35,
    "characters_featured": ["quacks", "meows"],
    "primary_location": "town_square",
    "content_pillar": "mystery_investigation",
    "punchline_type": "reveal"
  }
}
```

---

## 8. Module 1: Story Generator Engine

### 8.1 Purpose

Takes Episode Engine parameters and generates a complete, structured episode script in JSON format.

### 8.2 Function Signature

```python
async def generate_episode(
    character_a: str,
    character_b: str,
    location: str,
    situation: str,
    punchline_type: str,
    additional_characters: list[str] = None,
    duration_target: int = 35,
    trending_tie_in: str = None,
    seasonal_theme: str = None,
    continuity_callbacks: list[dict] = None,
    seed: int = None
) -> dict:
```

### 8.3 Idea Generation (Slot Machine)

The slot machine generates 2-3 episode ideas for the daily Discord post.

```python
async def generate_daily_ideas(count: int = 3) -> list[dict]:
    """
    Generates 2-3 episode ideas incorporating:
    1. Performance-weighted character/situation/punchline selection
    2. Continuity callbacks from past episodes
    3. Trending topics (if relevant)
    4. Seasonal themes (if applicable)
    5. Variety rules (full-cast episode if none this week)
    
    Returns list of idea dicts, each containing:
    - characters involved
    - location
    - situation type
    - 2-3 sentence concept summary
    - any trending/seasonal tie-in
    - any continuity callback opportunity
    """
```

**Variety rules:**
- At least one full-cast episode per week (check weekly count)
- Feature at least 5 of 6 characters per week
- Don't use the exact same situation template two days in a row
- If analytics data exists, weight toward high-performing combos

### 8.4 Claude Prompt Template

The master prompt for story generation must include:
- Complete character data for all characters in the episode
- Location details and available character positions
- Situation template and punchline specification
- Continuity context (past events, running gags, character growth)
- Trending tie-in or seasonal theme if applicable
- Dialogue rules (Pens max 5 words, Reows ALL CAPS energy, etc.)
- Output format (strict JSON matching Schema 7.5)
- Duration and timing constraints

### 8.5 Edit Interpretation

When you submit freeform edit notes in Discord, Claude interprets them:

```python
async def apply_edit_notes(
    original_script: dict,
    edit_notes: str,       # Your freeform feedback from Discord
    character_data: dict
) -> dict:
    """
    Takes the original script and your natural language edit notes.
    Claude interprets the notes and generates a revised script.
    Returns the complete updated script as a new version.
    """
```

---

## 9. Module 2: Continuity Engine

### 9.1 Purpose

Tracks events, running gags, and character development across episodes to enable callbacks, references, and narrative continuity.

### 9.2 Data Structures

**timeline.json** — chronological log of every significant event:
```json
{
  "events": [
    {
      "episode_id": "EP003",
      "episode_title": "The Ketchup Incident",
      "date": "2026-02-17",
      "event": "Quacks discovered the diner was out of ketchup and built a conspiracy theory",
      "characters_involved": ["quacks", "oinks"],
      "location": "diner_interior",
      "tags": ["conspiracy", "ketchup", "diner", "food"],
      "callback_potential": "high"
    }
  ]
}
```

**running_gags.json** — active recurring jokes:
```json
{
  "gags": [
    {
      "id": "ketchup_conspiracy",
      "origin_episode": "EP003",
      "description": "Quacks believes 'they' are withholding ketchup from the island",
      "last_referenced": "EP012",
      "times_referenced": 3,
      "status": "active",
      "escalation_ideas": ["Quacks starts hoarding ketchup", "Quacks forms a ketchup task force"]
    }
  ]
}
```

**character_growth.json** — tracks how characters develop:
```json
{
  "characters": {
    "meows": {
      "developments": [
        {
          "episode_id": "EP024",
          "development": "Revealed he bakes pancakes as a secret hobby",
          "personality_impact": "Shows a softer, less formal side"
        }
      ]
    }
  }
}
```

### 9.3 Callback Finder

```python
def find_callback_opportunities(
    characters: list[str],
    situation: str,
    location: str
) -> list[dict]:
    """
    Searches timeline, running gags, and character growth for
    relevant callbacks given the upcoming episode's parameters.
    
    Returns list of callback opportunities ranked by relevance,
    each with the source episode, what happened, and a suggested
    way to reference it.
    """
```

### 9.4 Post-Episode Logging

After every episode is published, the continuity engine automatically:
1. Extracts significant events from the script's `continuity_log`
2. Updates timeline.json with new events
3. Updates running_gags.json (new gags, updated reference counts)
4. Updates character_growth.json with any character developments

---

## 10. Module 3: Trending Topics & Seasonal Themes

### 10.1 Purpose

Checks for current trending topics and upcoming calendar events that can be woven into episode ideas for relevance and discoverability.

### 10.2 Trending Topics

```python
async def get_trending_topics() -> list[dict]:
    """
    Checks TikTok Creative Center, YouTube Trending, and 
    general news for topics that could be humorously adapted
    to the island setting.
    
    Filters: only child-safe, non-political, non-controversial topics.
    Prefers: food trends, holidays, pop culture moments, internet humor,
    seasonal activities, silly observance days.
    
    Returns list of:
    {
        "topic": "International Pancake Day",
        "source": "calendar",
        "relevance_score": 0.8,
        "story_angle": "Oinks adds pancakes to the diner menu, 
                        chaos ensues over toppings"
    }
    """
```

### 10.3 Seasonal Theme Calendar

Pre-loaded calendar of seasonal themes and observance days:

```yaml
# config/seasonal_themes.yaml (partial)
themes:
  - date_range: "02-14"
    theme: "Valentine's Day"
    story_angles: ["Characters exchange cards", "Oinks makes heart-shaped menu items"]
  - date_range: "03-17"
    theme: "St. Patrick's Day"
    story_angles: ["Everything at the diner turns green", "Treasure hunt on the island"]
  - date_range: "10-01:10-31"
    theme: "Halloween Season"
    story_angles: ["Island costume contest", "Quacks investigates 'haunted' forest"]
  - date_range: "12-01:12-31"
    theme: "Holiday Season"
    story_angles: ["Island gift exchange", "Reows builds a 'holiday attraction'"]
  # ... full year of themes
```

### 10.4 Integration with Story Generator

When generating daily ideas, the slot machine:
1. Checks trending topics (if any are relevant and child-safe)
2. Checks seasonal calendar (if today matches any theme)
3. If a trend or theme exists, one of the 2-3 daily ideas incorporates it
4. The other ideas are standard Episode Engine outputs
5. Trending/seasonal content is never forced — it's always one option among others

---

## 11. Module 4: Storyboard Renderer

### 11.1 Purpose

Converts a script JSON into a visual storyboard — a grid of annotated thumbnails showing each scene. Used for the script review step (optional visual aid alongside the Notion script page).

### 11.2 Implementation

```python
def render_storyboard(script: dict, output_dir: str) -> str:
    """
    Generates a storyboard image grid. Each cell shows:
    - Background plate
    - Character sprites in position (placeholder if needed)
    - Dialogue text overlaid
    - Scene number and duration label
    
    Returns: path to storyboard PNG
    """
```

---

## 12. Module 5: Text Box Renderer

### 12.1 Purpose

Generates frame-by-frame images of NES-style dialogue text boxes with typewriter animation.

### 12.2 Text Box Visual Spec

- **Position:** Bottom of 1080x1920 frame, centered horizontally
- **Dimensions:** 900px wide x 200px tall
- **Background:** Dark (#1A1A3A at ~85% opacity)
- **Border:** 2px solid white, pixel-perfect (no anti-aliasing)
- **Font:** "Press Start 2P" (Google Fonts, free, OFL), 16-20px
- **Character name:** Top-left, in character's `name_color`, bold
- **Text area:** Below name, left-aligned, white
- **Portrait:** 48x48px character face, left side (optional)
- **Typewriter speed:** ~20 characters per second with blip sound per character

### 12.3 Function Signature

```python
def render_dialogue_frames(
    character_id: str,
    text: str,
    font_path: str,
    frame_rate: int = 30,
    chars_per_second: int = 20,
    box_width: int = 900,
    box_height: int = 200,
    include_portrait: bool = True
) -> list[str]:  # Returns list of frame image paths
```

---

## 13. Module 6: Video Assembler

### 13.1 Composition Pipeline

```
For each scene in script:
    1. BACKGROUND: Load + scale to 1080x1920 (nearest-neighbor)
    2. CHARACTERS: Load sprite, extract frame, scale, position, composite
    3. DIALOGUE: Render text box frames, composite at bottom
    4. SFX: Record trigger timestamps for audio mixer

After all scenes:
    5. END CARD: Load template, overlay text, hold 3 seconds
    6. AUDIO: Mix music + SFX + text blips (Module 7)
    7. RENDER: Combine frames to video via FFmpeg, mux audio
    8. OUTPUT: MP4 at 1080x1920, 30fps, H.264 + AAC
```

### 13.2 FFmpeg Commands

```bash
# Frames to video
ffmpeg -framerate 30 -i frames/frame_%05d.png -c:v libx264 -pix_fmt yuv420p temp.mp4

# Add audio
ffmpeg -i temp.mp4 -i mixed_audio.wav -c:v copy -c:a aac -shortest output.mp4
```

### 13.3 Critical Rules

- **Nearest-neighbor scaling ONLY** — no anti-aliasing, no smoothing
- All sprites must maintain pixel-perfect rendering at any scale
- Text boxes render over all other layers
- Simple cuts between scenes (no fancy transitions — NES authentic)

---

## 14. Module 7: Audio Mixer

### 14.1 Implementation

```python
def mix_episode_audio(
    script: dict,
    music_path: str,
    sfx_dir: str = "assets/sfx/",
    music_volume_db: float = -12.0,
    sfx_volume_db: float = -3.0,
    blip_volume_db: float = -6.0
) -> str:  # Returns path to mixed WAV
```

Process:
1. Load background music, loop if shorter than episode
2. Reduce music to -12dB (background level)
3. Place character-specific text blips synced to typewriter animation
4. Place SFX at trigger timestamps
5. Mix all layers, normalize, export WAV

---

## 15. Module 8: Video Variant Generator

### 15.1 Purpose

Generates 2-3 variations of each episode for you to choose from in the #video-preview channel.

### 15.2 Variant Dimensions

Each variant differs along these axes:
- **Music track:** Different background music from the assets library
- **Pacing:** Adjusts scene durations and dialogue timing (faster/slower/standard)
- **Character positioning:** Alternate position assignments from the location's available positions
- **Punchline hold:** Varies the hold time on the final frame (1s / 2s / 3s)

### 15.3 Implementation

```python
async def generate_variants(
    script: dict,
    count: int = 3
) -> list[str]:  # Returns list of video file paths
    """
    Takes an approved script and generates 2-3 video variants.
    
    Variant 1: Default — standard pacing, location-default music
    Variant 2: Alternate music + slightly faster pacing
    Variant 3: Different music + slower pacing with extended punchline hold
    
    Each variant is a complete, publishable video.
    """
```

### 15.4 Custom Version from Edit Notes

```python
async def generate_custom_variant(
    script: dict,
    edit_notes: str,           # "music from v2, pacing from v1"
    existing_variants: list    # References to already-generated versions
) -> str:  # Returns path to custom video
```

---

## 16. Module 9: Metadata Generator

### 16.1 Purpose

Auto-generates platform-specific titles, descriptions, and hashtags following industry best practices.

### 16.2 Metadata Rules Engine

Based on analysis of top short-form content creators and current platform best practices:

```yaml
# config/metadata_rules.yaml

tone:
  voice: "playful, funny, unserious, clean"
  never: ["clickbait", "misleading", "offensive", "profanity", "suggestive"]
  always: ["character names when featured", "curiosity gap or funny premise"]

titles:
  max_length: 55  # Characters — avoids mobile truncation
  structure: "Hook or funny premise, not a description of what happens"
  include_character_names: true
  examples_good:
    - "Quacks vs. the suspicious briefcase"
    - "Reows has a business idea. Pens is supportive."
    - "Meows orders coffee. It takes 20 minutes."
    - "Nobody asked Reows to help. He helped anyway."
  examples_bad:
    - "Episode 24 of our animated series"  # Boring, no hook
    - "YOU WON'T BELIEVE what happens next"  # Clickbait
    - "Funny animal cartoon"  # Generic, no personality

descriptions:
  first_line_is_hook: true  # Visible before "show more"
  tone: "conversational, like texting a friend about a funny thing that happened"
  include_soft_cta: true
  cta_examples:
    - "Follow for more island chaos"
    - "New episode every day"
    - "Which character are you?"
  max_length_tiktok: 150
  max_length_youtube: 300
  max_length_instagram: 2200

hashtags:
  count_per_post: "3-5"  # Industry best practice — less is more
  strategy: "3-layer approach"
  layers:
    broad: ["#comedy", "#animation", "#funny", "#shorts"]
    niche: ["#pixelart", "#retrogaming", "#8bit", "#indieanimation", "#retro"]
    content_specific: ["#IslandIP"]  # Plus character names, episode-specific tags
  rules:
    - "Never use identical hashtag sets on consecutive posts"
    - "Rotate broad hashtags weekly"
    - "Always include at least 1 niche hashtag"
    - "YouTube: always include #Shorts"
    - "Check TikTok Creative Center for trending hashtags daily"
    - "Only use trending hashtags if genuinely relevant to the episode"

platform_specific:
  tiktok:
    tone: "Most casual. Internet humor. Emoji OK but sparingly."
    hashtag_placement: "end of description"
    max_hashtags: 5
  youtube:
    tone: "Slightly more descriptive. Keyword-optimized first line."
    always_include: "#Shorts"
    hashtag_placement: "title or description"
    max_hashtags: 5
  instagram:
    tone: "Caption-style. Can be slightly longer. End with CTA."
    hashtag_placement: "end of caption"
    max_hashtags: 5

content_safety:
  auto_scan: true
  block_list: []  # Profanity and offensive terms list
  flag_threshold: 0.7  # Flag for human review if safety confidence below this
```

### 16.3 Implementation

```python
async def generate_metadata(script: dict) -> dict:
    """
    Generates platform-specific metadata following rules engine.
    
    Returns:
    {
        "tiktok": {"title": "...", "description": "...", "hashtags": [...]},
        "youtube": {"title": "...", "description": "...", "tags": [...]},
        "instagram": {"caption": "...", "hashtags": [...]}
    }
    """

def safety_check(metadata: dict) -> tuple[bool, list[str]]:
    """
    Scans all metadata for content safety issues.
    Returns (is_safe, list_of_issues)
    """
```

---

## 17. Module 10: Publishing & Scheduling

### 17.1 Scheduling Configuration

```yaml
# config/scheduling.yaml
scheduling:
  timezone: "America/New_York"
  episodes_per_day: 1  # Minimum
  
  optimal_times:
    tiktok:
      - "10:00"
      - "19:00"
    youtube:
      - "12:00"
      - "17:00"
    instagram:
      - "11:00"
      - "20:00"
  
  stagger_minutes: 30  # Post to each platform 30 min apart
```

### 17.2 Platform APIs

| Platform | Method | Status | Notes |
|----------|--------|--------|-------|
| **YouTube** | Data API v3 (OAuth 2.0) | **Production ready** | Fully automated. Resumable upload. OAuth app published to production (no token expiry). |
| **TikTok** | Content Posting API (OAuth 2.0) | **Pending approval** | App submitted for review. Manual posting required until approved. |
| **Instagram** | Manual posting | **Manual** | Decision: skip API integration due to Meta's complex approval process. See `docs/instagram_posting_guide.md`. |

### 17.3 Google Drive Backup

Every final video is uploaded to Google Drive after variant selection:
- **Folder:** `https://drive.google.com/drive/u/4/folders/1OBzCzvzIPxWNCHU6JI-uIMJuCEK4Y-Uv`
- **Filename format:** `ep0001_short-title.mp4`
- **Module:** `src/publisher/drive.py`
- **Env var:** `GOOGLE_DRIVE_FOLDER_ID` (shared OAuth credentials with YouTube)

### 17.4 Discord Publishing Alert

After Drive upload, an alert is posted to `#publishing-log` (channel ID: `1472347949504659590`):
```
**New Episode Ready:** ep0001_the-pink-donut.mp4
**Google Drive:** https://drive.google.com/file/d/.../view

**TikTok:** #pixelart #comedy #Blobtoshi #animation #trending
**YouTube:** #Shorts #pixelart #comedy #Blobtoshi #animation
**Instagram:** #pixelart #reels #comedy #Blobtoshi #animation
```
Hashtags are 3-5 per platform, trending, and algorithmically optimized.

### 17.5 Auto-Schedule Flow

Once you approve the final video and metadata passes safety check:
1. Upload final video to Google Drive
2. Post publishing alert to #publishing-log with per-platform hashtags
3. Get next optimal posting slot per platform
4. Stagger by 30 minutes
5. Upload and schedule on each platform (YouTube automated; TikTok/Instagram manual)
6. After publish: log confirmation with post URLs

### 17.6 Override Capability

If you reply in #publishing-log before the scheduled time, the system:
- Interprets your freeform edit ("change the TikTok title to...")
- Updates the metadata
- Confirms the change
- Publishes with updated metadata at scheduled time

---

## 18. Module 11: Analytics & Feedback Loop

### 18.1 Data Collection

```python
async def collect_episode_analytics(episode_id: str) -> dict:
    """
    Pulls performance data from all platforms 24-48 hours after publish.
    
    Metrics per platform: views, likes, comments, shares,
    avg watch time, completion rate.
    """
```

### 18.2 Auto-Adjustment

The system automatically adjusts content weights based on performance:

```python
def update_content_weights() -> dict:
    """
    Analyzes all episode performance and updates weights for:
    - Character selection probability
    - Character pairing probability
    - Situation type probability
    - Punchline type probability
    - Location probability
    
    Weights are stored in data/analytics/content_weights.json
    and used by the slot machine for future idea generation.
    
    No human approval needed — adjustments happen automatically.
    """
```

### 18.3 Weekly Report

Published every Monday to Notion, link posted to #weekly-analytics.

Report contents:
- Total views, engagement, follower growth across all platforms
- Top 3 episodes by views, engagement, completion rate
- Character rankings (by views, engagement, completion)
- Pairing rankings
- Situation type rankings
- Punchline type rankings
- Platform comparison (TikTok vs YouTube vs Instagram)
- Trending tie-in effectiveness (if any were used)
- System adjustments made (weight changes)
- Recommendations for next week

---

## 19. End-to-End Pipeline Orchestration

### 19.1 Daily Trigger

The pipeline runs daily on a cron schedule (configurable, e.g., 8:00 AM ET):

1. **Trend Check** — Scan for trending topics and seasonal themes
2. **Continuity Check** — Load timeline, running gags, character growth
3. **Idea Generation** — Slot machine generates 2-3 ideas
4. **Discord Post** — Bot posts ideas to #idea-selection
5. **WAIT** — Bot waits for your selection
6. **Script Generation** — Claude writes script based on your pick
7. **Notion Publish** — Script published to Notion
8. **Discord Post** — Bot posts Notion link to #script-review
9. **WAIT** — Bot waits for your approval (or edit loop)
10. **Asset Check** — Verify all required sprites, backgrounds, SFX exist
11. **Video Production** — Text rendering → video assembly → audio mix
12. **Variant Generation** — Create 2-3 video versions
13. **Discord Post** — Bot posts video links to #video-preview
14. **WAIT** — Bot waits for your pick (or edit loop)
15. **Metadata Generation** — Auto-generate titles, descriptions, hashtags
16. **Safety Check** — Scan metadata for content issues
17. **Discord Post** — Bot posts metadata log to #publishing-log
18. **Auto-Schedule** — Schedule for next optimal time slots
19. **Auto-Publish** — Upload to all platforms at scheduled times
20. **Confirmation** — Bot posts publish confirmation with links
21. **Continuity Update** — Log events, gags, character growth
22. **Analytics** (24-48 hours later) — Pull performance data, update weights

---

## 20. Build Priority & Dependency Tree

Build in this exact order:

```
PHASE 1: FOUNDATION (Days 1-2)
├── 1. Project structure + setup script + requirements.txt
├── 2. characters.json
├── 3. situations.json + punchlines.json + locations.json
├── 4. All config YAML files
└── 5. .env.example with all required variables

PHASE 2: DISCORD BOT (Days 3-5)
├── 6. Discord bot core (bot.py + state management)
├── 7. #idea-selection handler
├── 8. #script-review handler
├── 9. #video-preview handler
├── 10. #publishing-log handler
└── 11. #weekly-analytics handler

PHASE 3: NOTION INTEGRATION (Days 5-6)
├── 12. Notion client wrapper
├── 13. Script publisher (creates pages with proper formatting)
└── 14. Report publisher

PHASE 4: STORY ENGINE (Days 6-8)
├── 15. Claude prompt templates
├── 16. Story generator engine
├── 17. Slot machine (idea generator)
├── 18. Script validator
├── 19. Edit interpreter (freeform notes → revised script)
├── 20. Continuity engine (timeline, gags, growth tracking)
└── 21. Trending topics + seasonal themes module

PHASE 5: VISUAL RENDERING (Days 9-12)
├── 22. Text box renderer
├── 23. Sprite manager
├── 24. Scene builder
├── 25. Video assembler (FFmpeg pipeline)
├── 26. Video variant generator
└── 27. Storyboard renderer

PHASE 6: AUDIO (Days 12-13)
└── 28. Audio mixer (music + SFX + blips)

PHASE 7: METADATA & PUBLISHING (Days 14-17)
├── 29. Metadata generator + rules engine
├── 30. Content safety scanner
├── 31. Scheduler
├── 32. TikTok publisher
├── 33. YouTube publisher
└── 34. Instagram publisher

PHASE 8: ANALYTICS (Days 17-19)
├── 35. Platform data collector
├── 36. Performance analyzer
├── 37. Auto-weight adjuster (feedback loop)
└── 38. Weekly report generator

PHASE 9: ORCHESTRATION (Days 19-21)
├── 39. Pipeline orchestrator
├── 40. Quality gates
└── 41. n8n workflow setup (optional)

PHASE 10: TESTING (Days 21-23)
└── 42. Tests for all modules
```

---

## 21. Error Handling & Quality Gates

### 21.1 Quality Gates

```yaml
# config/quality_gates.yaml
quality_gates:
  script_generation:
    max_retries: 3
    validation_required: true
    human_review: true  # Always — via Discord #script-review
  
  asset_check:
    allow_placeholders: false  # After initial asset creation
    block_on_missing: true
    notify_discord: true  # Alert in #publishing-log if asset missing
  
  video_assembly:
    resolution_check: true  # Must be 1080x1920
    duration_tolerance_pct: 15  # Allow 15% deviation
    audio_sync_check: true
    min_file_size_kb: 500
    max_file_size_mb: 100
  
  metadata:
    safety_check_required: true
    profanity_scan: true
    flag_threshold: 0.7
  
  publishing:
    max_retries: 3
    retry_backoff_seconds: [30, 120, 600]
```

### 21.2 Error Handling Pattern

Every module uses consistent error handling. Failed stages notify via Discord #publishing-log with the error and suggested action.

---

## 22. Configuration & Environment Setup

### 22.1 Environment Variables (.env)

```bash
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Discord
DISCORD_BOT_TOKEN=...
DISCORD_GUILD_ID=...
DISCORD_CHANNEL_IDEA_SELECTION=...
DISCORD_CHANNEL_SCRIPT_REVIEW=...
DISCORD_CHANNEL_VIDEO_PREVIEW=...
DISCORD_CHANNEL_PUBLISHING_LOG=...
DISCORD_CHANNEL_WEEKLY_ANALYTICS=...
DISCORD_AUTHORIZED_USER_ID=...

# Notion
NOTION_API_KEY=secret_...
NOTION_SCRIPTS_DB_ID=...
NOTION_ANALYTICS_DB_ID=...

# TikTok
TIKTOK_CLIENT_KEY=...
TIKTOK_CLIENT_SECRET=...
TIKTOK_ACCESS_TOKEN=...

# YouTube + Google Drive (shared OAuth credentials)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...
GOOGLE_DRIVE_FOLDER_ID=...

# Instagram / Meta
META_APP_ID=...
META_APP_SECRET=...
INSTAGRAM_ACCESS_TOKEN=...
INSTAGRAM_BUSINESS_ACCOUNT_ID=...

# Pipeline
PIPELINE_ENV=development
LOG_LEVEL=INFO
PIPELINE_TIMEZONE=America/New_York
```

---

## 23. Step-by-Step Guides for Manual Tasks

The following guides are comprehensive, idiot-proof walkthroughs for every manual task you are responsible for. Each guide assumes zero prior experience with the tool.

These guides will be created as individual markdown files in the `guides/` directory.

---

### Guide 01: Discord Server Setup

**File:** `guides/01_discord_server_setup.md`

**What you'll do:** Create a private Discord server with 5 channels and add the Mootoshi bot.

**Steps:**

1. **Open Discord** — Go to discord.com in your browser or open the Discord app. Log in to your account.

2. **Create a new server** — On the left sidebar, click the **+** button (it's a circle with a plus sign at the bottom of your server list). Click **"Create My Own"**. Click **"For me and my friends"**. Name the server **"Mootoshi"**. Click **"Create"**.

3. **Delete the default channels** — You'll see a #general and possibly a #voice channel. Right-click on each one → **Delete Channel** → Confirm. We're replacing these with our own.

4. **Create the 5 channels** — For each channel below, click the **+** next to "TEXT CHANNELS" in the sidebar:
   - Type: `idea-selection` → Click Create
   - Type: `script-review` → Click Create
   - Type: `video-preview` → Click Create
   - Type: `publishing-log` → Click Create
   - Type: `weekly-analytics` → Click Create

5. **Get your Server ID** — Go to Discord Settings (gear icon bottom-left) → **Advanced** → Turn on **Developer Mode**. Go back to your server. Right-click the server name at the top-left → **Copy Server ID**. Save this — it goes in your `.env` file as `DISCORD_GUILD_ID`.

6. **Get each Channel ID** — Right-click each channel name → **Copy Channel ID**. Save each one — they go in your `.env` file.

7. **Get your User ID** — Click on your own username at the bottom-left → **Copy User ID**. This goes in `.env` as `DISCORD_AUTHORIZED_USER_ID`.

8. **Create the bot application** — Go to discord.com/developers/applications in your browser. Click **"New Application"**. Name it **"Mootoshi Bot"**. Click **Create**.

9. **Create the bot user** — In the application page, click **"Bot"** in the left sidebar. Click **"Add Bot"** → Confirm. Under the bot's name, click **"Reset Token"** → Copy the token. Save this — it goes in `.env` as `DISCORD_BOT_TOKEN`. **IMPORTANT: Never share this token with anyone.**

10. **Set bot permissions** — Still on the Bot page, scroll down to **"Privileged Gateway Intents"**. Turn ON: **Message Content Intent**. Click **Save Changes**.

11. **Invite the bot to your server** — Click **"OAuth2"** in the left sidebar → **"URL Generator"**. Under Scopes, check **"bot"**. Under Bot Permissions, check: **Send Messages**, **Read Messages/View Channels**, **Attach Files**, **Embed Links**, **Add Reactions**. Copy the generated URL at the bottom. Paste it in your browser. Select your **Mootoshi** server. Click **Authorize**.

12. **Verify** — Go back to your Mootoshi Discord server. You should see "Mootoshi Bot" in the member list on the right side. The bot will appear offline until the code is running.

**Done.** Your Discord server is ready.

---

### Guide 02: Notion Workspace Setup

**File:** `guides/02_notion_workspace_setup.md`

**What you'll do:** Set up two Notion databases (Scripts and Analytics) and create an API integration.

**Steps:**

1. **Open Notion** — Go to notion.so and log in.

2. **Create a new page** — In the left sidebar, click **"+ New page"**. Title it **"Mootoshi"**. This is your main workspace page.

3. **Create the Scripts database** — Inside the Mootoshi page, type `/database` and select **"Database - Full page"**. Title it **"Episode Scripts"**.

4. **Add database properties** — Click the **+** at the end of the property headers to add each:
   - **Episode Number**: Type = Number
   - **Status**: Type = Select → Add options: "Draft", "In Review", "Approved", "Published"
   - **Characters**: Type = Multi-select → Add: "Pens", "Chubs", "Meows", "Oinks", "Quacks", "Reows"
   - **Location**: Type = Select → Add: "Diner", "Beach", "Forest", "Town Square", "Chubs' Office", "Reows' Place"
   - **Situation**: Type = Select → Add: "Everyday Life", "Mystery", "Scheme", "Business", "Diplomatic", "Chill Hangout"
   - **Punchline Type**: Type = Select → Add: "Deadpan", "Backfire", "Misunderstanding", "Escalation", "Reveal", "Entrance"
   - **Version**: Type = Number
   - **Date**: Type = Date

5. **Create the Analytics database** — Go back to the Mootoshi page. Create another full-page database titled **"Weekly Reports"**.

6. **Create the Notion API integration** — Go to notion.so/my-integrations in your browser. Click **"+ New integration"**. Name: **"Mootoshi Bot"**. Associated workspace: Select your workspace. Click **Submit**.

7. **Copy the API key** — On the integration page, under **"Internal Integration Secret"**, click **"Show"** → Copy the key. Save this — it goes in `.env` as `NOTION_API_KEY`.

8. **Connect the integration to your databases** — Go back to Notion. Open the **Episode Scripts** database. Click the **...** menu at the top-right → **"Connections"** → **"Connect to"** → Find and select **"Mootoshi Bot"**. Repeat for the **Weekly Reports** database.

9. **Get the database IDs** — Open the **Episode Scripts** database. Look at the URL in your browser. It will look like: `notion.so/your-workspace/abc123def456...?v=...`. The part after the workspace name and before the `?v=` is the database ID. Copy it. Save it as `NOTION_SCRIPTS_DB_ID`. Repeat for the **Weekly Reports** database → save as `NOTION_ANALYTICS_DB_ID`.

**Done.** Your Notion workspace is ready.

---

### Guide 03: Platform Account Setup

**File:** `guides/03_platform_account_setup.md`

**What you'll do:** Create TikTok, YouTube, and Instagram accounts for the Island IP brand.

#### TikTok

1. Download TikTok on your phone or go to tiktok.com.
2. Sign up with a new account. Use your brand email.
3. Set username to your brand name (TBD — use a placeholder for now).
4. Switch to a **Creator Account**: Go to Settings → Account → Switch to Business Account (or Creator Account). This unlocks analytics.
5. Fill out your profile: bio, link, profile picture (can use a placeholder pixel art image).
6. **For API access (later):** Go to developers.tiktok.com. Log in with your TikTok account. Create a new app. You'll need to submit for review to get Content Posting API access. This can take 1-2 weeks, so start this early.

#### YouTube

1. Go to youtube.com. Sign in with your Google account (or create one for the brand).
2. Click your profile icon → **"Create a channel"**. Use your brand name.
3. Go to **YouTube Studio** (studio.youtube.com) → **Customization** → Fill out profile, banner, description.
4. **For API access:** Go to console.cloud.google.com. Create a new project named "Mootoshi". Enable the **YouTube Data API v3**. Create **OAuth 2.0 credentials**. You'll get a Client ID and Client Secret — save these for `.env`.

#### Instagram

1. Download Instagram on your phone. Sign up with your brand email.
2. Set username to your brand name.
3. Switch to a **Creator Account** or **Business Account**: Settings → Account → Switch to professional account.
4. **Link to a Facebook Page:** Instagram's API requires a Facebook Page. Go to facebook.com → Create a Page for your brand. Then in Instagram Settings → Account → Linked Accounts → Facebook → Connect your Page.
5. **For API access:** Go to developers.facebook.com. Create a new app (type: Business). Add the Instagram Graph API. Generate a long-lived access token. Save the token and your Instagram Business Account ID for `.env`.

---

### Guide 04: Character Design with Midjourney

**File:** `guides/04_midjourney_character_design.md`

**What you'll do:** Use Midjourney to generate character concept art for all 6 characters.

**What you need first:** A Midjourney subscription ($30/month Standard plan). Go to midjourney.com and sign up.

**Steps:**

1. **Join the Midjourney Discord** — After subscribing, you'll get access to the Midjourney Discord server. All image generation happens through Discord messages.

2. **Go to a generation channel** — In the Midjourney Discord, find any `#newbies` or `#general` channel (or DM the Midjourney Bot directly for privacy — click the bot's name and start a DM).

3. **Generate character concepts** — Type `/imagine` followed by your prompt. Here are the exact prompts to use for each character. Copy-paste these exactly:

**Pens (Penguin):**
```
/imagine NES 8-bit pixel art penguin character, small round black and white body, maroon crest on head, holding a diet soda can in flipper, deadpan expression, simple limited color palette, retro game sprite style, black background, 32x48 pixel scale --ar 1:1 --style raw --s 50
```

**Chubs (Seal):**
```
/imagine NES 8-bit pixel art grey seal character, very round plump body, wearing a tiny necktie, holding small briefcase, friendly expression, simple limited color palette, retro game sprite style, black background, 32x48 pixel scale --ar 1:1 --style raw --s 50
```

**Meows (Cat):**
```
/imagine NES 8-bit pixel art cat character, upright standing posture, sleek and refined, wearing a tiny monocle, dignified expression, simple limited color palette, retro game sprite style, black background, 32x48 pixel scale --ar 1:1 --style raw --s 50
```

**Oinks (Pig):**
```
/imagine NES 8-bit pixel art pig character, medium round body, wearing a diner apron, holding a plate, friendly approachable expression, simple limited color palette, retro game sprite style, black background, 32x48 pixel scale --ar 1:1 --style raw --s 50
```

**Quacks (Duck):**
```
/imagine NES 8-bit pixel art call duck character, very small compact round body, holding a tiny magnifying glass, suspicious squinting expression, simple limited color palette, retro game sprite style, black background, 32x48 pixel scale --ar 1:1 --style raw --s 50
```

**Reows (Bear):**
```
/imagine NES 8-bit pixel art bear character, large round body inspired by Yogi Bear, brown fur with lighter brown patches on belly and face, wearing a white collar and blue pork pie hat with white center, big enthusiastic expression, energetic pose, simple limited color palette, retro game sprite style, black background, 32x48 pixel scale --ar 1:1 --style raw --s 50
```

4. **Evaluate results** — Midjourney generates 4 images per prompt. Look at all 4. Click the buttons below the image: **U1, U2, U3, U4** to upscale (enlarge) the one you like best. **V1, V2, V3, V4** to generate variations of one you almost like.

5. **Iterate** — Run each prompt 5-10 times with slight modifications until you're happy. Try adjusting:
   - Add `--chaos 20` for more variety
   - Change `--s 50` to `--s 100` for more stylized results
   - Add descriptive words: "chubby", "tiny", "imposing", "adorable"
   - Remove elements that aren't working

6. **Save your favorites** — Right-click and save the upscaled images you like best. Create a folder on your computer: `character_concepts/` with subfolders for each character.

7. **Silhouette test** — Open each saved image. Squint at it or make it very small. Can you tell which character is which just from the shape? If yes, you have good designs. If two characters look too similar, iterate more on one of them.

8. **The rule of pixel art:** Don't worry if Midjourney's output looks too detailed or "HD." The next step (PixelLab and Aseprite) will convert these into true NES-resolution sprites. Midjourney is for getting the *design right* — the shape, the personality, the props, the silhouette.

**Tip:** Save 3-5 favorites per character, not just 1. You'll want options when creating the final sprites.

---

### Guide 05: Sprite Creation with PixelLab

**File:** `guides/05_pixellab_sprite_creation.md`

**What you'll do:** Convert your Midjourney character concepts into proper NES-resolution pixel sprites using PixelLab.

**What you need first:** A PixelLab subscription ($15/month). Go to pixellab.ai and sign up.

**Steps:**

1. **Open PixelLab** — Go to pixellab.ai and log in.

2. **Upload your reference** — Click "New Project" or "Generate". Look for an option to upload a reference image. Upload your favorite Midjourney concept for the character.

3. **Set the canvas size** — Set your output to 32x48 pixels (or 48x48 if 32x48 isn't available). This is the NES sprite resolution.

4. **Set the color palette** — Limit to 4-6 colors per character. PixelLab may have NES palette presets. If not, use these approximate constraints:
   - 1 dark outline color (black or near-black)
   - 1 primary body color
   - 1 secondary body color (lighter shade)
   - 1 accent color (for props, eyes, or distinctive features)
   - 1-2 additional colors if needed

5. **Generate the sprite** — Use PixelLab's AI to generate a pixel art version of your character at the target resolution. The prompt should be simple: "NES style pixel art sprite of [character description], front-facing idle pose, limited color palette"

6. **Generate each pose** — For each character, you need these sprite states (use the same reference/style for consistency):
   - **Idle** — standing still, default pose
   - **Talking** — mouth open or slight gesture change
   - **Signature action** — Pens sipping, Oinks serving, Quacks investigating, etc.
   - **Reaction surprise** — eyes wide, slight jump
   - **Reaction specific** — character-specific (Pens deadpan, Oinks exasperated, etc.)
   - **Walking** — 2-frame walk cycle

7. **Download each sprite** — Save as PNG with transparent background. Name them:
   - `pens_idle.png`
   - `pens_talking.png`
   - `pens_sipping.png`
   - etc.

8. **Check consistency** — Open all sprites for one character side by side. They should look like the same character — same body proportions, same colors, same general shape. Only the specific pose/expression should differ.

**If PixelLab isn't getting consistent results:** Move to Guide 06 (Aseprite) and manually adjust the sprites pixel-by-pixel. At 32x48 pixels, this is very doable — you're editing a tiny grid.

---

### Guide 06: Sprite Sheet Creation with Aseprite

**File:** `guides/06_aseprite_sprite_sheets.md`

**What you'll do:** Clean up, finalize, and organize your character sprites into proper sprite sheets using Aseprite.

**What you need first:** Aseprite ($20 one-time purchase). Go to aseprite.org and buy it.

**Steps:**

1. **Install and open Aseprite** — Download, install, and open the application.

2. **Create a new file** — File → New. Width: 32, Height: 48, Color Mode: RGBA. Background: Transparent. Click OK.

3. **Import your PixelLab sprite** — File → Open → Select one of your PixelLab sprites (e.g., `pens_idle.png`). It will open in a new tab.

4. **Clean up the sprite** — At this resolution, you can see every individual pixel. Use the **Pencil tool** (shortcut: B) to fix any pixels that look off. Use the **Eraser tool** (shortcut: E) to clean up the background. Zoom in with the scroll wheel or Ctrl/Cmd + Plus.

5. **Create animation frames** — This is where you turn a single sprite into an animated character:

   a. **Duplicate the frame** — At the bottom of the screen, you'll see Frame 1 in the timeline. Right-click on Frame 1 → **"New Frame"** (or press Alt+N). This creates Frame 2 as a copy of Frame 1.

   b. **Make small changes** — For Frame 2, make the small pixel changes needed for the animation:
      - **Idle animation:** Move 2-3 pixels up/down for a subtle breathing motion
      - **Talking:** Open the mouth (change 3-5 pixels around the mouth area)
      - **Walking:** Shift the legs/feet by 2-3 pixels

   c. **Repeat** — Create 2-4 frames per animation state. NES animations are simple — 2 frames is often enough.

6. **Export as sprite sheet** — File → Export Sprite Sheet. Sheet type: **"By Rows"**. Check **"JSON Data"** (this creates a metadata file the pipeline needs). Click **Export**. Save as `pens_idle_sheet.png`.

7. **Repeat for every character state** — Go through each character, each pose. It's tedious but the sprites are tiny — each one should take 5-15 minutes to clean up and animate.

8. **Create the portrait sprites** — New file: 48x48 pixels. Draw or clean up a close-up face of each character. These are used in the text box dialogue. Export as `pens_portrait.png`, etc.

9. **Organize your files** — Copy all final sprites into the project assets folder:
   ```
   assets/characters/pens/idle.png
   assets/characters/pens/talking.png
   assets/characters/pens/sipping.png
   ...
   ```

**Key Aseprite shortcuts:**
- **B** = Pencil (draw pixels)
- **E** = Eraser
- **G** = Paint bucket (fill area)
- **I** = Eyedropper (pick color from canvas)
- **Alt+N** = New frame
- **Scroll** = Zoom in/out
- **Space + drag** = Pan around canvas

**The golden rule:** At 32x48 pixels, every single pixel matters. Changing just 3-4 pixels can dramatically alter the expression or pose. This is what makes NES pixel art both challenging and forgiving — small changes have big impact, but mistakes are easy to fix.

---

### Guide 07: Background Creation

**File:** `guides/07_background_creation.md`

**What you'll do:** Create NES-style background plates for each location.

**Steps:**

1. **Use Midjourney for concepts** — Generate background art using these prompts:

**Diner Interior:**
```
/imagine NES 8-bit pixel art retro diner interior, counter with bar stools, booths along windows, neon sign, checkered floor, warm lighting, limited color palette, retro game background style, side-scrolling perspective --ar 9:16 --style raw --s 50
```

**Beach:**
```
/imagine NES 8-bit pixel art tropical beach scene, sand, ocean waves, palm trees, blue sky with clouds, bright colors, limited color palette, retro game background style, side-scrolling perspective --ar 9:16 --style raw --s 50
```

**Forest:**
```
/imagine NES 8-bit pixel art forest scene, tall pixelated trees, mossy ground, dappled light through canopy, mysterious atmosphere, limited color palette, retro game background style --ar 9:16 --style raw --s 50
```

(Repeat for: town square, Chubs' office, Reows' place)

2. **Refine in Aseprite** — Import the Midjourney output into Aseprite. Resize to your target background resolution (e.g., 270x480 pixels — this is 1080x1920 divided by 4, which scales up pixel-perfectly). Clean up details, ensure the color palette is limited and NES-authentic.

3. **Important:** Backgrounds should be designed at 270x480 (or similar NES-scale resolution) and then scaled up to 1080x1920 using **nearest-neighbor** scaling. This maintains the chunky pixel look.

4. **Save** — Export as PNG. Place in `assets/backgrounds/`.

---

### Guide 08: Sound Effects Creation

**File:** `guides/08_sound_effects_creation.md`

**What you'll do:** Generate retro 8-bit sound effects using jsfxr.

**Steps:**

1. **Open jsfxr** — Go to sfxr.me in your browser. This is a free, browser-based retro sound effect generator. No download needed.

2. **Generate SFX** — On the left, you'll see preset categories. Click each one to generate random sounds in that category:
   - **Pickup/Coin** — Great for menu select, positive reactions
   - **Laser/Shoot** — Great for surprise, reveal moments
   - **Explosion** — Great for door bursts, big entrances
   - **Powerup** — Great for eureka moments, celebrations
   - **Hit/Hurt** — Great for backfire moments, comedy impacts
   - **Jump** — Great for bouncy animations
   - **Blip/Select** — Great for text blip sounds

3. **For text blip sounds** — You need 6 different blip sounds (one per character). Click **"Blip/Select"** repeatedly. Each click generates a new random blip. When you hear one you like, adjust the sliders to get the right "personality":
   - **Pens:** Low-pitched, slow blip (calm energy)
   - **Chubs:** Mid-pitched, professional-sounding blip
   - **Meows:** High-pitched, refined blip
   - **Oinks:** Warm, medium-pitched blip
   - **Quacks:** Quick, staccato blip (nervous energy)
   - **Reows:** Bold, loud, enthusiastic blip

4. **Export** — Click the **"Export .wav"** button (or "Save as .wav") for each sound you like. Name them according to the asset naming convention: `text_blip_low.wav`, `door_burst.wav`, etc.

5. **Place in project** — Copy all WAV files to `assets/sfx/`.

**You need these SFX at minimum:**
- 6 text blip sounds (one per character)
- `door_burst.wav` (Reows' entrance)
- `surprise.wav` (general reaction)
- `sip.wav` (Pens' diet soda)
- `cash_register.wav` (business/money gag)
- `magnifying_glass.wav` (Quacks investigating)
- `menu_select.wav` (scene transitions)

---

### Guide 09: Chiptune Music Sourcing

**File:** `guides/09_chiptune_music_sourcing.md`

**What you'll do:** Find and download royalty-free 8-bit chiptune music tracks for background music.

**Steps:**

1. **Free sources** (check license for each track — must be royalty-free for commercial use):
   - **Incompetech (Kevin MacLeod)** — incompetech.com. Huge library of free music. Filter by "8-bit" or "chiptune" genre. License: Creative Commons (attribution required — add credit to video description).
   - **Free Music Archive** — freemusicarchive.org. Search "chiptune" or "8-bit". Check each track's license before downloading.
   - **OpenGameArt** — opengameart.org. Search "chiptune music". Many tracks are CC0 (public domain) or CC-BY.
   - **YouTube Audio Library** — studio.youtube.com → Audio Library. Filter by mood and genre. These are free to use in YouTube content. Check if license extends to other platforms.

2. **What to download** — You need 5 tracks minimum:
   - **Town/Diner theme** — Upbeat, warm, cozy. Think "friendly neighborhood" energy.
   - **Adventure theme** — Energetic, exploratory. For beach and outdoor episodes.
   - **Mystery theme** — Slightly suspenseful, detective-vibes. For Quacks episodes.
   - **Chill theme** — Relaxed, easygoing. For Pens-centric calm episodes.
   - **Silly theme** — Goofy, playful. For Reows-centric chaotic episodes.

3. **Track license documentation** — For EVERY track you download, create an entry in `assets/music/LICENSES.md`:
   ```
   ## town_theme.ogg
   - Title: [Original Track Title]
   - Artist: [Artist Name]
   - Source: [URL where you downloaded it]
   - License: [License type, e.g., CC BY 4.0]
   - Attribution: [Required credit text, if any]
   ```

4. **Convert to OGG** — The pipeline uses OGG format. If your download is MP3 or WAV, convert it. You can use any free online converter (e.g., cloudconvert.com → select your file → choose OGG → download).

5. **Place in project** — Copy all OGG files to `assets/music/`.

---

### Guide 10: API Key Setup

**File:** `guides/10_api_key_setup.md`

**What you'll do:** Obtain all API keys needed for the pipeline and add them to your .env file.

**Steps:**

1. **Anthropic API Key** — Go to console.anthropic.com. Log in with your Claude Max account. Go to API Keys → Create Key. Copy and save it.

2. **Discord Bot Token** — Already obtained in Guide 01, step 9.

3. **Notion API Key** — Already obtained in Guide 02, step 7.

4. **TikTok API** — Go to developers.tiktok.com. Create an app. Apply for Content Posting API scope (requires app review — submit early, takes 1-2 weeks).

5. **YouTube API** — Go to console.cloud.google.com. Create a project → Enable YouTube Data API v3 → Create OAuth 2.0 credentials → Get Client ID, Client Secret, and follow the OAuth flow to get a Refresh Token.

6. **Instagram/Meta API** — Go to developers.facebook.com. Create a Business app → Add Instagram Graph API → Generate a long-lived access token → Get your Instagram Business Account ID.

7. **Add all keys to .env** — Open the `.env` file in your project root. Fill in each variable. Make sure `.env` is in your `.gitignore` so it never gets committed to GitHub.

---

## 24. Decision Log

Decisions made during implementation that deviate from or extend the original PRD.

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-15 | **Instagram: manual posting instead of API integration** | Meta's Graph API requires Business verification, app review, and ongoing compliance — overly complex for a single-creator workflow. Manual posting via `docs/instagram_posting_guide.md` is faster and gives more control over captions/hashtags. |
| 2026-02-15 | **TikTok: manual posting until app approval** | TikTok Content Posting API app submitted for review (1-3 business days). `publish_to_tiktok()` is stubbed — will be implemented once approved. Manual posting required in the interim. |
| 2026-02-16 | **YouTube: production-ready, fully automated** | YouTube Data API v3 has no approval process. Resumable upload implemented in `src/publisher/platforms.py`. OAuth app published to production (tokens do not expire). |
| 2026-02-16 | **Google Drive backup for all final videos** | Every selected video is uploaded to a shared Drive folder (`ep0001_short-title.mp4` format). Enables manual posting to TikTok/Instagram from Drive. Module: `src/publisher/drive.py`. |
| 2026-02-16 | **Discord alert with per-platform hashtags** | After Drive upload, a formatted alert with 3-5 trending hashtags per platform is posted to `#publishing-log`. Enables quick copy-paste for manual posting. |
| 2026-02-16 | **Google OAuth scopes: youtube.upload + drive** | Single set of OAuth credentials (GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN) used for both YouTube upload and Google Drive upload. User re-authorized via OAuth Playground to add Drive scope. |
| 2026-02-16 | **VPS deployment on Hostinger (Ubuntu 24.04)** | Bot deployed as systemd service on existing Hostinger VPS. Auto-restarts on failure. Deployment script: `deploy/setup.sh`. |

---

## 25. Legal & Compliance Notes

### 24.1 Content Classification

- YouTube: Mark videos as **"not made for kids"** (audience is broad, not exclusively children)
- TikTok/Instagram: Standard adult creator accounts

### 24.2 AI Disclosure

- Include "Created with AI tools" in account bios (transparency best practice)

### 24.3 Music Licensing

- Use ONLY royalty-free or CC-licensed music
- Maintain license log at `assets/music/LICENSES.md`
- If composing original music later (FamiTracker), you own the copyright

### 24.4 Character IP

- All characters are original. Design references (Yogi Bear, Pen Pen) are inspiration only.
- Final pixel art designs MUST be sufficiently distinct from referenced characters
- Do not copy trademarked visual elements
- Consider trademark registration once designs are locked

---

## End of PRD

**For Claude Code — build in the exact sequence listed in Section 20.**

**For the creator — complete the guides in Section 23 in parallel while Claude Code builds the pipeline.**

The system is designed so that once the initial manual setup is complete (Guides 01-10), your only daily interaction is through Discord: pick an idea, approve a script, choose a video version. Everything else is automated.
