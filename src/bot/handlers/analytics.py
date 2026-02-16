"""Handler for #weekly-analytics channel.

Bot posts weekly performance reports (Notion links). Mostly automated.
"""


async def handle_analytics(message, bot):
    """Handle user replies in #weekly-analytics.

    This channel is mostly automated. The bot posts weekly performance
    report links. User messages here are informational only.
    """
    await message.channel.send(
        "Weekly analytics reports are posted here automatically every Monday at 9:00 AM ET. "
        "Use `!status` to check the current pipeline state."
    )
