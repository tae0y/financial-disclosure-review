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
    # Checked-in yaml assets read at review time: case corpus, case risk kinds, reader profiles.
    rubric_dir: str = field(default_factory=default_rubric_dir)
    display_max_model_calls: int = 5
    display_max_visual_crops: int = 12
    rules_subdir: str = "site_rules"
    viewport_width: int = 1280
    viewport_height: int = 800
    max_turns: int = 20
    max_visits: int = 3
    # Exploration budget of the page agent: scroll/expand/open_link calls in one discovery, and
    # consecutive interactions that revealed nothing new before exploration is closed.
    max_interactions: int = 8
    max_no_progress: int = 2
    # Reference cases rank by BM25 slot overlap; the paid query-embedding rerank is opt-in.
    case_rerank: bool = False
    # Reader profile id from assets/persona_profiles.yaml; empty picks the file's default.
    persona_profile: str = ""
    # Reader wanted in free text (Korean); a small tool loop turns it into dataset filters.
    persona_request: str = ""
    # Reader wanted as dataset filters (domain/persona_explanation/dataset.Filters fields).
    persona_attributes: dict | None = None
    # One exact dataset row; wins over persona_attributes and persona_request.
    persona_uuid: str = ""
    # A deployment can narrow the public sites a review may reach. This setting travels with the
    # graph so the browser checks the same allow-list again for every redirect target.
    allowed_hosts: tuple[str, ...] = ()
