"""Centralized error alerting — sends notifications to #errors Discord channel."""

from datetime import datetime

ERRORS_CHANNEL_KEY = "errors"

# Maximum Discord message length
_MAX_MESSAGE_LENGTH = 2000


def format_error_message(stage, episode_id, error_message):
    """Format an error alert message for Discord.

    Args:
        stage: Pipeline stage name (e.g., "Script Generation").
        episode_id: Episode ID (e.g., "EP002") or None.
        error_message: The error description string.

    Returns:
        Formatted string ready to send to Discord.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    ep = episode_id if episode_id else "N/A"

    msg = (
        f"**{stage}** Failed\n"
        f"Episode: `{ep}`\n"
        f"Error: {error_message}\n"
        f"Time: {timestamp}"
    )

    if len(msg) > _MAX_MESSAGE_LENGTH:
        # Truncate the error message to fit within Discord's limit
        overflow = len(msg) - _MAX_MESSAGE_LENGTH + 3  # 3 for "..."
        msg = (
            f"**{stage}** Failed\n"
            f"Episode: `{ep}`\n"
            f"Error: {error_message[:len(error_message) - overflow]}...\n"
            f"Time: {timestamp}"
        )

    return msg


def format_startup_message():
    """Format a bot startup notification message.

    Returns:
        Formatted string for the startup alert.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"Bot is now online and running.\nStarted at: {timestamp}"


async def notify_error(bot, stage, episode_id, error_message):
    """Send an error alert to the #errors Discord channel.

    This function never raises — alerting should never crash the bot.

    Args:
        bot: Discord bot instance.
        stage: Pipeline stage name.
        episode_id: Episode ID or None.
        error_message: The error description.
    """
    try:
        from src.bot.bot import CHANNEL_IDS

        channel_id = CHANNEL_IDS.get(ERRORS_CHANNEL_KEY)
        if not channel_id:
            return

        channel = bot.get_channel(channel_id)
        if not channel:
            return

        msg = format_error_message(stage, episode_id, str(error_message))
        await channel.send(msg)
    except Exception as e:
        # Alerting must never crash the bot, but print so journalctl captures it
        print(f"[Alerting] Failed to send error alert: {e}")


async def notify_startup(bot):
    """Send a startup notification to the #errors Discord channel.

    This function never raises — alerting should never crash the bot.

    Args:
        bot: Discord bot instance.
    """
    try:
        from src.bot.bot import CHANNEL_IDS

        channel_id = CHANNEL_IDS.get(ERRORS_CHANNEL_KEY)
        if not channel_id:
            return

        channel = bot.get_channel(channel_id)
        if not channel:
            return

        msg = format_startup_message()
        await channel.send(msg)
    except Exception as e:
        # Alerting must never crash the bot, but print so journalctl captures it
        print(f"[Alerting] Failed to send startup notification: {e}")
