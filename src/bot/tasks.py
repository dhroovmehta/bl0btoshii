"""Safe async task wrapper — prevents asyncio.create_task from silently swallowing exceptions."""

import asyncio
import traceback


async def _run_safe(coro, error_channel=None, bot=None, stage="Background Task"):
    """Run a coroutine and catch any exception it raises.

    Exceptions are printed to stdout (visible in journalctl) and optionally
    sent to a Discord channel and the #errors channel via notify_error.
    """
    try:
        return await coro
    except Exception as e:
        # Always print to stdout so journalctl captures it
        print(f"[safe_task] Exception in {stage}: {e}")
        traceback.print_exc()

        # Send to the originating Discord channel if provided
        if error_channel:
            try:
                await error_channel.send(f"Error in {stage}: {e}")
            except Exception:
                print(f"[safe_task] Failed to send error to channel: {e}")

        # Send to #errors via notify_error if bot is provided
        if bot:
            try:
                from src.bot.alerts import notify_error
                await notify_error(bot, stage, None, str(e))
            except Exception:
                print(f"[safe_task] Failed to send notify_error: {e}")


def safe_task(coro, error_channel=None, bot=None, stage="Background Task"):
    """Create an asyncio task with exception catching.

    Drop-in replacement for asyncio.create_task that ensures exceptions
    are visible in journalctl and optionally sent to Discord.

    Args:
        coro: The coroutine to run.
        error_channel: Optional Discord channel to send error messages to.
        bot: Optional Discord bot instance for notify_error calls.
        stage: Human-readable stage name for error messages.

    Returns:
        asyncio.Task
    """
    return asyncio.ensure_future(_run_safe(coro, error_channel, bot, stage))
