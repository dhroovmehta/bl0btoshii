"""Pipeline state manager — tracks which episode is in which stage."""

import json
import os
from datetime import datetime

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "pipeline_state.json")


def _default_state():
    return {
        "current_episode": None,
        "stage": "idle",  # v2 stages: idle, ideas_posted, pipeline_running, done
        "ideas": [],
        "selected_idea_index": None,
        "current_script": None,
        "updated_at": datetime.utcnow().isoformat()
    }


def load_state():
    """Load pipeline state from disk."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return _default_state()


def save_state(state):
    """Save pipeline state to disk."""
    state["updated_at"] = datetime.utcnow().isoformat()
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def reset_state():
    """Reset pipeline state to idle."""
    state = _default_state()
    save_state(state)
    return state


def get_stage():
    """Get current pipeline stage."""
    return load_state()["stage"]


def set_stage(stage):
    """Update pipeline stage."""
    state = load_state()
    state["stage"] = stage
    save_state(state)
    return state
