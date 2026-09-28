"""Settings passed at invoke time, never stored in State."""

from dataclasses import dataclass, field
from pathlib import Path

from dotenv import find_dotenv


def default_data_dir() -> str:
    env = find_dotenv(usecwd=True)
    return str((Path(env).parent if env else Path.cwd()) / "data")


def default_rubric_dir() -> str:
    """Folder of the rubric yaml files, checked into the repo."""
    env = find_dotenv(usecwd=True)
    return str((Path(env).parent if env else Path.cwd()) / "assets")


def default_db_path() -> str:
    return str(Path(default_data_dir()) / "reference.sqlite")


@dataclass
class Context:
    model: str = "gpt-5-mini"
    data_dir: str = field(default_factory=default_data_dir)
    db_path: str = field(default_factory=default_db_path)
    display_max_model_calls: int = 5
    display_max_visual_crops: int = 12
    rules_subdir: str = "site_rules"
    viewport_width: int = 1280
    viewport_height: int = 800
    max_turns: int = 20
    max_visits: int = 3
