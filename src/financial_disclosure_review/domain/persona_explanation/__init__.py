"""Reader-tailored advice on what to check before signing, shown beside the page."""

from .dataset import PersonaStore, ensure_dataset
from .generate import generate_persona_explanation
from .profiles import PROFILE_ALLOWLIST, resolve_dataset_profile, resolve_profile
from .selection import choose_profile, select_persona

__all__ = [
    "PROFILE_ALLOWLIST",
    "PersonaStore",
    "choose_profile",
    "ensure_dataset",
    "generate_persona_explanation",
    "resolve_dataset_profile",
    "resolve_profile",
    "select_persona",
]
