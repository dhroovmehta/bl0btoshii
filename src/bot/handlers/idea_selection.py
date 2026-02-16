"""Handler for #idea-selection channel.

Bot posts 2-3 episode ideas daily. User picks one by replying 1, 2, or 3.
On selection, triggers script generation and posts result to #script-review.
"""

import re
import asyncio
import os
from datetime import datetime

from src.bot.state import load_state, save_state


def parse_selection(text):
    """Parse user's idea selection from their message.

    Accepts: "1", "2", "3", "option 1", "option 2", "the first one", etc.
    Returns: 0-indexed selection (0, 1, 2) or None if not understood.
    """
    text = text.strip().lower()

    # Direct number
    if text in ("1", "2", "3"):
        return int(text) - 1

    # "option X" pattern
    match = re.search(r"option\s*(\d)", text)
    if match:
        num = int(match.group(1))
        if 1 <= num <= 3:
            return num - 1

    # Ordinal words
    ordinals = {"first": 0, "second": 1, "third": 2}
    for word, idx in ordinals.items():
        if word in text:
            return idx

    return None


async def post_daily_ideas(channel):
    """Generate and post 2-3 episode ideas to #idea-selection."""
    from src.story_generator.slot_machine import generate_daily_ideas

    ideas = generate_daily_ideas(3)
    today = datetime.now().strftime("%B %d, %Y")

    lines = [f"**Daily Episode Ideas — {today}**\n"]
    for i, idea in enumerate(ideas):
        char_a = idea["character_a"]
        char_b = idea["character_b"]
        additional = idea.get("additional_characters", [])
        location = idea["location"].replace("_", " ").title()

        if additional:
            chars = "Full Cast"
        else:
            chars = f"{char_a.capitalize()} + {char_b.capitalize()}"

        concept = idea["concept"]
        trending = idea.get("trending_tie_in")
        trending_text = f" Trending tie-in: {trending}." if trending else ""

        callbacks = idea.get("continuity_callbacks", [])
        callback_text = ""
        if callbacks:
            refs = [cb.get("reference", "") for cb in callbacks]
            callback_text = f" Callback: {', '.join(refs)}."

        lines.append(
            f"**Option {i + 1}:** {chars} | {location} | "
            f"{concept}{trending_text}{callback_text}\n"
        )

    lines.append('Reply with **1**, **2**, or **3**.')

    await channel.send("\n".join(lines))

    # Save state
    state = load_state()
    state["stage"] = "ideas_posted"
    state["ideas"] = ideas
    state["selected_idea_index"] = None
    save_state(state)


async def handle_idea_selection(message, bot):
    """Handle user replies in #idea-selection."""
    state = load_state()

    if state["stage"] != "ideas_posted":
        await message.channel.send(
            "No ideas are currently posted. Type `!generate` in any channel to trigger idea generation."
        )
        return

    selection = parse_selection(message.content)

    if selection is None:
        await message.channel.send(
            "I didn't understand your selection. Reply with **1**, **2**, or **3**."
        )
        return

    ideas = state.get("ideas", [])
    if selection >= len(ideas):
        await message.channel.send(
            f"Only {len(ideas)} options available. Reply with a number between 1 and {len(ideas)}."
        )
        return

    # Save selection
    selected_idea = ideas[selection]
    state["selected_idea_index"] = selection
    state["stage"] = "script_generating"
    save_state(state)

    await message.channel.send(f"Option {selection + 1} selected. Generating script now...")

    # Generate script in background
    asyncio.create_task(_generate_and_post_script(selected_idea, bot))


async def _generate_and_post_script(idea, bot):
    """Generate a script with Claude and post to #script-review."""
    from src.story_generator.engine import generate_episode
    from src.notion.script_publisher import publish_script

    script_channel_id = int(os.getenv("DISCORD_CHANNEL_SCRIPT_REVIEW", "0"))
    script_channel = bot.get_channel(script_channel_id)

    idea_channel_id = int(os.getenv("DISCORD_CHANNEL_IDEA_SELECTION", "0"))
    idea_channel = bot.get_channel(idea_channel_id)

    try:
        # Run blocking Claude API call in a thread
        loop = asyncio.get_event_loop()
        script, errors = await loop.run_in_executor(None, generate_episode, idea)

        if not script:
            await idea_channel.send(f"Script generation failed: {errors}")
            state = load_state()
            state["stage"] = "idle"
            save_state(state)
            return

        # Publish to Notion
        notion_url = await loop.run_in_executor(None, publish_script, script)

        # Save script and state
        state = load_state()
        state["current_episode"] = script.get("episode_id", "?")
        state["current_script"] = script
        state["script_notion_url"] = notion_url
        state["script_version"] = 1
        state["stage"] = "script_review"
        save_state(state)

        # Post to #script-review
        episode_id = script.get("episode_id", "?")
        title = script.get("title", "Untitled")
        scenes = len(script.get("scenes", []))
        total_dur = sum(s.get("duration_seconds", 0) for s in script.get("scenes", []))

        review_msg = (
            f"**Script Ready — {episode_id}: {title}**\n\n"
            f"[Notion Link]({notion_url})\n\n"
            f"Scenes: {scenes} | Duration: {total_dur}s\n\n"
            f"Reply **approve** to proceed to video production.\n"
            f"Reply with edit notes to request changes."
        )

        if errors:
            review_msg += f"\n\nWarnings: {', '.join(errors)}"

        await script_channel.send(review_msg)

    except Exception as e:
        print(f"[Idea Selection] Error generating script: {e}")
        if idea_channel:
            await idea_channel.send(f"Error generating script: {e}")
        state = load_state()
        state["stage"] = "idle"
        save_state(state)
