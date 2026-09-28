"""Display-method rubric codes shared between judge_display and verification (placement rule 6)."""

# Items whose verdict must agree with a threshold list computed by code (group_measures).
VIOLATION_KEYS = {"E02": "below_min_pt", "E04": "below_contrast_min", "E05": "below_contrast_min"}
