"""Display-method rubric codes another module has to agree with.

judge_display measures these items and verification re-checks the verdicts against the same
measurements, so the map lives here rather than in either domain (placement rule 6).
"""

# Items whose verdict must agree with a threshold list computed by code (group_measures).
VIOLATION_KEYS = {"E02": "below_min_pt", "E04": "below_contrast_min", "E05": "below_contrast_min"}
