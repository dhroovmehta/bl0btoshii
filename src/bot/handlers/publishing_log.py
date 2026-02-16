"""Handler for #publishing-log channel.

Bot posts automated publishing status. User can override metadata before publish.
"""

from src.bot.state import load_state, save_state


async def handle_publishing_log(message, bot):
    """Handle user replies in #publishing-log.

    This channel is mostly automated (bot posts logs).
    User can reply to override metadata before scheduled publish time.
    Examples: "change the TikTok title to ...", "update youtube description ..."
    """
    state = load_state()

    if state["stage"] not in ("publishing", "done"):
        await message.channel.send(
            "No episode is currently in the publishing stage."
        )
        return

    metadata = state.get("metadata")
    if not metadata:
        await message.channel.send("No metadata found to update.")
        return

    # Parse the override
    text = message.content.strip().lower()
    updated = False

    # Detect platform-specific overrides
    for platform in ["tiktok", "youtube", "instagram"]:
        if platform in text:
            platform_meta = metadata.get(platform, {})

            if "title" in text and platform != "instagram":
                # Extract new title after "to" keyword
                new_title = _extract_value(message.content, "title")
                if new_title:
                    platform_meta["title"] = new_title
                    updated = True

            if "description" in text:
                new_desc = _extract_value(message.content, "description")
                if new_desc:
                    if platform == "instagram":
                        platform_meta["caption"] = new_desc
                    else:
                        platform_meta["description"] = new_desc
                    updated = True

            if "caption" in text and platform == "instagram":
                new_caption = _extract_value(message.content, "caption")
                if new_caption:
                    platform_meta["caption"] = new_caption
                    updated = True

            metadata[platform] = platform_meta

    if updated:
        state["metadata"] = metadata
        save_state(state)
        await message.channel.send(
            "Metadata updated. Here's the current state:\n\n"
            + _format_metadata_summary(metadata)
        )
    else:
        await message.channel.send(
            "Could not parse the override. Try:\n"
            "- `change the tiktok title to [new title]`\n"
            "- `update youtube description to [new description]`\n"
            "- `update instagram caption to [new caption]`"
        )


def _extract_value(text, field):
    """Extract the value after 'to' in a metadata override command.

    E.g., "change the tiktok title to My New Title" → "My New Title"
    """
    markers = [f"{field} to ", f"{field}: "]
    text_lower = text.lower()
    for marker in markers:
        idx = text_lower.find(marker)
        if idx != -1:
            return text[idx + len(marker):].strip().strip('"').strip("'")
    return None


def _format_metadata_summary(metadata):
    """Format a brief summary of current metadata."""
    lines = []
    for platform in ["tiktok", "youtube", "instagram"]:
        data = metadata.get(platform, {})
        title = data.get("title", data.get("caption", "N/A"))[:60]
        lines.append(f"**{platform.capitalize()}:** {title}")
    return "\n".join(lines)
