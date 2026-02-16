# Sprite Creation Guide — Nano Banana Pro (Step by Step)

This guide walks you through generating all 48 pixel art images for Blobtoshi using Google Gemini's Nano Banana Pro image generator. Follow every step exactly as written.

---

## What You Need Before Starting

- Your computer (Mac or PC — either works)
- Google Chrome browser (recommended, since Gemini is a Google product)
- Your Google account with the AI Pro subscription (you already have this — the PRO badge)
- The CSV file with all 48 prompts (already created at `data/sprite_prompts.csv`)
- A folder on your computer to save the downloaded images

---

## PHASE 1: Set Up Your Workspace

### Step 1: Create a folder to save images

1. Open **Finder** on your Mac
2. Navigate to your **Desktop** (click "Desktop" in the left sidebar)
3. Right-click on an empty area → click **"New Folder"**
4. Name it: **blobtoshi_sprites**
5. Double-click to open the **blobtoshi_sprites** folder
6. Inside it, create these subfolders (right-click → New Folder for each):
   - **pens**
   - **chubs**
   - **meows**
   - **oinks**
   - **quacks**
   - **reows**
   - **portraits**
   - **backgrounds**

When you're done, your folder structure should look like this:
```
Desktop/
  blobtoshi_sprites/
    pens/
    chubs/
    meows/
    oinks/
    quacks/
    reows/
    portraits/
    backgrounds/
```

### Step 2: Open the CSV file so you can copy prompts from it

1. Open **Google Chrome** (or whatever browser you use)
2. Open a new tab
3. Go to **Google Sheets**: https://sheets.google.com
4. Click the **blank spreadsheet** (the big "+" icon) to create a new sheet
5. In the new sheet, click **File** (top-left menu) → **Import**
6. Click the **Upload** tab
7. Click **"Browse"** and navigate to:
   `/Users/dhroov/Claude_Code_Projects/mootoshi/data/sprite_prompts.csv`
   (Or you can drag the file into the upload area)
8. When it asks about import settings:
   - Separator type: **Comma**
   - Leave everything else as default
   - Click **"Import data"**
9. You should now see a spreadsheet with 3 columns:
   - **Column A**: Character name (e.g., "Pens - idle")
   - **Column B**: Description (plain English of what the image should look like)
   - **Column C**: The prompt (this is what you will copy and paste into Gemini)
10. **Keep this tab open.** You will copy from Column C throughout this process.

---

## PHASE 2: Open Gemini and Select Nano Banana Pro

### Step 3: Open Gemini

1. Open a **new tab** in your browser (Ctrl+T on PC, Cmd+T on Mac)
2. Go to: **https://gemini.google.com**
3. If you're not logged in, log in with your Google account (the one with the PRO subscription)
4. You should see the Gemini chat interface — a text box at the bottom where you can type

### Step 4: Switch to Nano Banana Pro (the "Thinking" model)

This is important — by default, Gemini is set to "Fast" (the standard, lower quality model). You need to switch to "Thinking" for Nano Banana Pro.

1. Look at the **bottom-right of the prompt input box** — you will see the word **"Fast"** with a small dropdown arrow next to it (to the left of the microphone icon)
2. Click **"Fast"** — a dropdown menu will appear with model options
3. Select **"Thinking"** — this is Nano Banana Pro (the higher quality model)
   - **"Fast"** = Nano Banana (standard quality — do NOT use this)
   - **"Thinking"** = Nano Banana Pro (higher quality — USE THIS ONE)
4. The dropdown should now show **"Thinking"** instead of "Fast" — this confirms you're using Nano Banana Pro

---

## PHASE 3: Generate Your First Character (Pens)

We're going to generate all images for one character at a time. This keeps each character looking consistent across all their poses.

**The order we'll follow:**
1. Pens (6 sprites)
2. Chubs (6 sprites)
3. Meows (6 sprites)
4. Oinks (6 sprites)
5. Quacks (6 sprites)
6. Reows (6 sprites)
7. Portraits (6 images)
8. Backgrounds (6 images)

### Step 5: Generate Pens' IDLE sprite (the most important one)

The idle sprite is the "base" version of the character. All other poses must look like the same character. That's why we generate idle FIRST.

1. Go to your **Google Sheets tab** (the CSV you imported)
2. Find **Row 2** — this is "Pens - idle"
3. Click on the **Column C cell** in that row (the prompt column)
4. The cell should highlight. Press **Ctrl+C** (PC) or **Cmd+C** (Mac) to copy the prompt text
5. Switch to your **Gemini tab**
6. Click on the **text input box** at the bottom of the Gemini page
7. Press **Ctrl+V** (PC) or **Cmd+V** (Mac) to paste the prompt
8. **Before hitting Enter**, read the prompt to make sure it pasted correctly (no weird symbols or cut-off text)
9. Press **Enter** (or click the Send button)
10. **Wait.** Gemini will think for a moment (Nano Banana Pro takes a bit longer than the fast model — this is normal). You may see it generating interim images before the final one appears.

### Step 6: Evaluate the result

When the image appears, check these things:

**MUST HAVE (reject if missing):**
- [ ] Is it pixel art? (blocky, pixelated style — NOT smooth/realistic)
- [ ] Is it a penguin? (not a duck, chicken, or other bird)
- [ ] Is the character facing the viewer? (front-facing, not turned to the side)
- [ ] Does it have a yellow crest on top of its head?
- [ ] Is it holding a diet soda can?
- [ ] Is the body short and round?
- [ ] Is the background empty/transparent/plain? (no scenery behind the character)
- [ ] Is it a single character? (not multiple penguins)

**NICE TO HAVE (don't reject just for these):**
- The expression looks deadpan/neutral
- The colors are vibrant and appealing
- The proportions look good (not too stretched or squished)

### Step 7: If the image is NOT good — regenerate

If the image doesn't meet the MUST HAVE checklist above:

1. Type a new message in Gemini that refines your request. For example:
   - "Make it more pixelated, like retro video game pixel art"
   - "The character should be facing the viewer directly, not turned to the side"
   - "Add a yellow crest on top of the penguin's head"
   - "Remove the background scenery, make it a plain transparent background"
   - "Make it a single character only, not multiple"
2. Press Enter and wait for the new image
3. Repeat the checklist evaluation
4. **You may need 2-5 attempts** to get a good result. This is completely normal. Don't get frustrated — AI image generation often needs a few tries.

### Step 8: If the image IS good — download it

1. **Hover your mouse** over the generated image
2. Look for a **"Download full size"** button (it may appear as a download icon — a downward arrow)
3. Click it
4. Your browser will download the image file (probably to your Downloads folder)
5. Open **Finder** → go to **Downloads**
6. Find the file you just downloaded (it will be the most recent file — probably named something like `gemini_generated_image.png` or similar)
7. **Rename the file** to: **idle.png**
   - Right-click the file → click "Rename" → type `idle.png` → press Enter
8. **Move the file** to the correct folder:
   - Drag it from Downloads into: **Desktop → blobtoshi_sprites → pens**

**Your pens folder should now contain:**
```
Desktop/blobtoshi_sprites/pens/idle.png
```

### Step 9: Generate the remaining 5 Pens sprites using the idle as reference

This is the consistency trick. You will upload the idle image you just saved as a "reference" so Gemini keeps the same character design for the other poses.

**For each of the next 5 Pens sprites (talking, sipping, reaction_surprise, reaction_deadpan, walking), do the following:**

#### 9a: Start a new message with the reference image

1. In Gemini, look for an **image upload button** near the text input box (usually a "+" icon, a paperclip icon, or an image icon)
2. Click it
3. Navigate to: **Desktop → blobtoshi_sprites → pens → idle.png**
4. Select the file and click **Open** — the image will attach to your message

#### 9b: Add the prompt text

1. Go to your **Google Sheets tab**
2. Find the **next Pens row** (e.g., Row 3 = "Pens - talking")
3. Copy the prompt from **Column C** (click the cell, Cmd+C)
4. Go back to **Gemini**
5. Click in the text box (the reference image should still be attached)
6. Paste the prompt (Cmd+V)
7. **Add this text to the BEGINNING of the prompt** (type it before the pasted text):

```
Using the attached image as a reference for the character's design, colors, and proportions, generate the same character in a new pose:
```

So your full message will look like:
```
[attached image: idle.png]

Using the attached image as a reference for the character's design, colors, and proportions, generate the same character in a new pose: Pixel art penguin character, front-facing view, short round cute body, yellow crest on top of head, holding diet soda can in one flipper, mouth slightly open talking, subtle lean forward, colorful detailed pixel art style, transparent background, single character, full body visible
```

8. Press **Enter** and wait for the result

#### 9c: Evaluate, regenerate if needed, download, rename, move

1. **Evaluate** — Does it look like the SAME penguin as the idle sprite? Same colors, same body shape, same style? Is it doing the correct new pose?
2. If not, refine: "Make this look more like the reference image I attached" or "Keep the exact same character design but change the pose to [description]"
3. When satisfied, **download** the image (hover → Download full size)
4. **Rename** the file to match the sprite state:
   - Row 3 → `talking.png`
   - Row 4 → `sipping.png`
   - Row 5 → `reaction_surprise.png`
   - Row 6 → `reaction_deadpan.png`
   - Row 7 → `walking.png`
5. **Move** each file to: **Desktop → blobtoshi_sprites → pens**

**When all 6 Pens sprites are done, your pens folder should contain:**
```
Desktop/blobtoshi_sprites/pens/
  idle.png
  talking.png
  sipping.png
  reaction_surprise.png
  reaction_deadpan.png
  walking.png
```

---

## PHASE 4: Generate All Remaining Characters

Repeat the exact same process (Steps 5-9) for each character in this order:

### Chubs (Rows 8-13 in the spreadsheet)

- Generate **idle** first (Row 8) — no reference image needed
- Then use the Chubs idle as reference for the other 5 poses
- Save files as: idle.png, talking.png, calculating.png, excited.png, reaction_nervous.png, walking.png
- Save all to: **Desktop → blobtoshi_sprites → chubs**

### Meows (Rows 14-19)

- Generate **idle** first (Row 14) — no reference image needed
- Use the Meows idle as reference for the other 5 poses
- Save files as: idle.png, talking.png, refined_pose.png, reaction_appalled.png, reaction_pleased.png, walking.png
- Save all to: **Desktop → blobtoshi_sprites → meows**

### Oinks (Rows 20-25)

- Generate **idle** first (Row 20) — no reference image needed
- Use the Oinks idle as reference for the other 5 poses
- Save files as: idle.png, talking.png, serving.png, wiping_counter.png, reaction_exasperated.png, walking.png
- Save all to: **Desktop → blobtoshi_sprites → oinks**

### Quacks (Rows 26-31)

- Generate **idle** first (Row 26) — no reference image needed
- Use the Quacks idle as reference for the other 5 poses
- Save files as: idle.png, talking.png, investigating.png, suspicious.png, eureka.png, walking.png
- Save all to: **Desktop → blobtoshi_sprites → quacks**

### Reows (Rows 32-37)

- Generate **idle** first (Row 32) — no reference image needed
- Use the Reows idle as reference for the other 5 poses
- Save files as: idle.png, talking.png, burst_entrance.png, excited.png, scheming.png, walking.png
- Save all to: **Desktop → blobtoshi_sprites → reows**

---

## PHASE 5: Generate Portraits

Portraits are close-up face images used in the dialogue text boxes (when a character is speaking, their face appears next to the text).

### Rows 38-43 in the spreadsheet

For each portrait:

1. **Upload the character's idle sprite as reference** (from the folder you already saved)
2. Copy the portrait prompt from Column C
3. Add the reference prefix:
```
Using the attached image as a reference for the character's design and colors, generate a close-up portrait version of this character:
```
4. Generate, evaluate, download
5. **Rename files as:**
   - Row 38 → `pens_portrait.png`
   - Row 39 → `chubs_portrait.png`
   - Row 40 → `meows_portrait.png`
   - Row 41 → `oinks_portrait.png`
   - Row 42 → `quacks_portrait.png`
   - Row 43 → `reows_portrait.png`
6. **Save all to:** Desktop → blobtoshi_sprites → **portraits**

---

## PHASE 6: Generate Backgrounds

Backgrounds are full scenes with NO characters in them. Characters get placed on top of these during video assembly.

### Rows 44-49 in the spreadsheet

For each background:

1. **No reference image needed** — each background is unique
2. Copy the prompt from Column C
3. Generate, evaluate, download
4. **Rename files as:**
   - Row 44 → `diner.png`
   - Row 45 → `beach.png`
   - Row 46 → `forest.png`
   - Row 47 → `town_square.png`
   - Row 48 → `chubs_office.png`
   - Row 49 → `reows_place.png`
5. **Save all to:** Desktop → blobtoshi_sprites → **backgrounds**

**Background evaluation checklist:**
- [ ] Is it pixel art style? (blocky, retro game look)
- [ ] Does it match the location description? (e.g., diner should have counter, stools, checkered floor)
- [ ] Are there NO characters in the image? (backgrounds must be empty of characters)
- [ ] Is it portrait/vertical orientation? (taller than wide — for 9:16 video)
- [ ] Does it have enough "ground area" at the bottom for characters to stand on?

---

## PHASE 7: Final Checklist

When all 48 images are generated, your folder should look like this:

```
Desktop/blobtoshi_sprites/
  pens/
    idle.png
    talking.png
    sipping.png
    reaction_surprise.png
    reaction_deadpan.png
    walking.png
  chubs/
    idle.png
    talking.png
    calculating.png
    excited.png
    reaction_nervous.png
    walking.png
  meows/
    idle.png
    talking.png
    refined_pose.png
    reaction_appalled.png
    reaction_pleased.png
    walking.png
  oinks/
    idle.png
    talking.png
    serving.png
    wiping_counter.png
    reaction_exasperated.png
    walking.png
  quacks/
    idle.png
    talking.png
    investigating.png
    suspicious.png
    eureka.png
    walking.png
  reows/
    idle.png
    talking.png
    burst_entrance.png
    excited.png
    scheming.png
    walking.png
  portraits/
    pens_portrait.png
    chubs_portrait.png
    meows_portrait.png
    oinks_portrait.png
    quacks_portrait.png
    reows_portrait.png
  backgrounds/
    diner.png
    beach.png
    forest.png
    town_square.png
    chubs_office.png
    reows_place.png
```

**Total: 48 files (36 sprites + 6 portraits + 6 backgrounds)**

Count your files. If you have 48, you're done with the generation phase.

---

## Important Notes

### Rate Limits
Your Pro subscription allows approximately **100 Nano Banana Pro images per day**. Since you need 48 final images, and you may need 2-5 attempts per image, you could use 100-240 generations total.

**Plan for this:**
- If you get a "daily limit reached" message, STOP. Your limit resets approximately 24 hours later.
- You can split the work across 2-3 days:
  - **Day 1:** Pens + Chubs + Meows (18 sprites)
  - **Day 2:** Oinks + Quacks + Reows (18 sprites)
  - **Day 3:** Portraits + Backgrounds (12 images)

### Watermarks
Some Gemini Pro images may include a small watermark. After downloading your first image, zoom in and check all corners and edges for any watermark text or logo. If you see one, let me know — I can write a script to remove it programmatically.

### Consistency Is More Important Than Perfection
The #1 priority is that all 6 poses of the same character look like they belong together — same colors, same body shape, same proportions. A slightly imperfect but consistent set of sprites is MUCH better than 6 "perfect" sprites that all look like different characters.

### If Gemini Won't Generate an Image
Gemini has content safety filters. If a prompt gets rejected:
- Don't worry — none of our prompts contain anything inappropriate
- Try rephrasing slightly (e.g., remove "holding a magnifying glass" if it triggers a filter)
- If a specific pose keeps getting rejected, let me know and I'll write an alternative prompt

### Starting a New Chat for Each Character
After finishing all 6 poses for one character, consider starting a **new Gemini conversation** (click "New Chat" or the "+" button) before moving to the next character. This prevents the AI from accidentally blending character designs between different characters.

---

## After You're Done

Once all 48 images are saved, come back to me. I will:
1. Write a script to copy all images from your Desktop folder into the correct project asset folders
2. Process/resize them if needed for the video pipeline
3. Test them in the video assembler to make sure they work
