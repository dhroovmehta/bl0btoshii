"""Story Generator Engine — generates complete episode scripts using Claude."""

import json
import os
import anthropic
from dotenv import load_dotenv

from src.story_generator.prompts import build_story_prompt, build_edit_prompt
from src.story_generator.validator import validate_script

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096


def _get_client():
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set in .env")
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _get_next_episode_id():
    """Get a DRAFT episode ID for script generation.

    Returns DRAFT-EP-XXX format. The real EP number is only assigned
    on successful publish via assign_episode_number().
    """
    index_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "episodes", "index.json")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            index = json.load(f)
        num = index.get("next_episode_number", 1)
    else:
        num = 1
    return f"DRAFT-EP-{num:03d}"


def assign_episode_number():
    """Assign the real episode number and increment the counter.

    Called only after successful Drive upload + publish. Returns the
    real EP ID (e.g., "EP001") and increments next_episode_number.
    """
    index_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "episodes", "index.json")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            index = json.load(f)
    else:
        index = {"next_episode_number": 1, "episodes": []}

    num = index.get("next_episode_number", 1)
    real_id = f"EP{num:03d}"

    index["next_episode_number"] = num + 1
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)

    return real_id


def generate_episode(idea, max_retries=3):
    """Generate a complete episode script from an idea seed.

    Args:
        idea: Dict from slot_machine.generate_daily_ideas()
        max_retries: Number of attempts if validation fails.

    Returns:
        (script_dict, errors) — the validated script and any non-fatal warnings.
    """
    client = _get_client()
    episode_id = _get_next_episode_id()
    prompt = build_story_prompt(idea, episode_id)

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text content
            text = response.content[0].text.strip()

            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

            # Parse JSON
            script = json.loads(text)

            # Validate
            is_valid, errors = validate_script(script)

            if is_valid:
                return script, []
            else:
                print(f"[Story Engine] Attempt {attempt + 1}: validation errors: {errors}")
                if attempt == max_retries - 1:
                    # Return with warnings on last attempt
                    return script, errors

        except json.JSONDecodeError as e:
            print(f"[Story Engine] Attempt {attempt + 1}: JSON parse error: {e}")
            if attempt == max_retries - 1:
                raise ValueError(f"Failed to generate valid JSON after {max_retries} attempts")

        except anthropic.APIError as e:
            print(f"[Story Engine] API error: {e}")
            if attempt == max_retries - 1:
                raise

    return None, ["Max retries exceeded"]


def apply_edit_notes(original_script, edit_notes, max_retries=2):
    """Revise a script based on freeform edit notes from the user.

    Args:
        original_script: The current script dict.
        edit_notes: Freeform text from Discord.
        max_retries: Number of attempts.

    Returns:
        (revised_script, errors)
    """
    client = _get_client()
    prompt = build_edit_prompt(original_script, edit_notes)

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )

            text = response.content[0].text.strip()

            # Strip markdown code fences
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

            revised = json.loads(text)

            is_valid, errors = validate_script(revised)
            if is_valid:
                return revised, []
            else:
                print(f"[Story Engine] Edit attempt {attempt + 1}: validation errors: {errors}")
                if attempt == max_retries - 1:
                    return revised, errors

        except json.JSONDecodeError as e:
            print(f"[Story Engine] Edit attempt {attempt + 1}: JSON parse error: {e}")
            if attempt == max_retries - 1:
                raise ValueError(f"Failed to parse revised script after {max_retries} attempts")

        except anthropic.APIError as e:
            print(f"[Story Engine] API error: {e}")
            if attempt == max_retries - 1:
                raise

    return None, ["Max retries exceeded"]
