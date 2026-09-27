"""Building the reference DB from the rubric yaml files."""

import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path

import yaml

# Loads every rubric yaml in RUBRICS into Context().db_path. Safe to re-run: both files are
# checked first, then all rubric tables are dropped and rebuilt in one transaction, so the DB
# always matches the yaml files (a failed build leaves the previous DB untouched).
RUBRICS = {  # yaml file stem -> the field that lists the screens an item applies to
    "card_guardrail_rubric": "page_types",
    "plain_service_rubric": "targets",
}
RUBRIC_SCHEMA = [
    "DROP TABLE IF EXISTS rubric_sources",
    "DROP TABLE IF EXISTS rubric_screens",
    "DROP TABLE IF EXISTS rubric_page_types",  # table of the first, card-only schema
    "DROP TABLE IF EXISTS rubric_applies_to",
    "DROP TABLE IF EXISTS rubric_items",
    "DROP TABLE IF EXISTS rubrics",
    """CREATE TABLE rubrics (
        name TEXT PRIMARY KEY,         -- yaml file stem
        source_file TEXT NOT NULL,
        screen_field TEXT NOT NULL     -- page_types or targets, restored by load_rubric
    )""",
    """CREATE TABLE rubric_items (
        code TEXT PRIMARY KEY,
        rubric TEXT NOT NULL REFERENCES rubrics(name),
        position INTEGER NOT NULL,     -- order in the yaml
        group_name TEXT NOT NULL,
        applies_condition TEXT,
        binding TEXT NOT NULL,
        criterion TEXT NOT NULL,
        UNIQUE (rubric, position)
    )""",
    """CREATE TABLE rubric_applies_to (
        code TEXT NOT NULL REFERENCES rubric_items(code),
        position INTEGER NOT NULL,
        product_type TEXT NOT NULL,
        PRIMARY KEY (code, position)
    )""",
    """CREATE TABLE rubric_screens (
        code TEXT NOT NULL REFERENCES rubric_items(code),
        position INTEGER NOT NULL,
        screen TEXT NOT NULL,
        PRIMARY KEY (code, position)
    )""",
    """CREATE TABLE rubric_sources (
        code TEXT NOT NULL REFERENCES rubric_items(code),
        position INTEGER NOT NULL,
        doc TEXT NOT NULL,
        loc TEXT NOT NULL,
        quote TEXT NOT NULL,
        snapshot TEXT NOT NULL,
        official_url TEXT NOT NULL,
        PRIMARY KEY (code, position)
    )""",
    "CREATE INDEX rubric_items_rubric ON rubric_items (rubric, group_name)",
    "CREATE INDEX rubric_applies_to_type ON rubric_applies_to (product_type)",
    "CREATE INDEX rubric_screens_screen ON rubric_screens (screen)",
]
SOURCE_FIELDS = ("doc", "loc", "quote", "snapshot", "official_url")


def rubric_schema_problems(items: list[dict], screen_field: str) -> list[str]:
    """Every way the yaml differs from the table schema. Nothing is coerced."""
    fields = {
        "code": str,
        "group": str,
        "applies_to": list,
        screen_field: list,
        "applies_condition": (str, type(None)),
        "binding": str,
        "criterion": str,
        "sources": list,
    }
    problems = []
    for n, item in enumerate(items):
        where = f"item {n} ({item.get('code')})"
        if set(item) != set(fields):
            problems.append(
                f"{where}: missing {sorted(set(fields) - set(item))},"
                f" extra {sorted(set(item) - set(fields))}"
            )
        for key, kind in fields.items():
            if key in item and not isinstance(item[key], kind):
                problems.append(f"{where}: {key} is {type(item[key]).__name__}")
        for key in ("applies_to", screen_field):
            if isinstance(item.get(key), list) and not all(isinstance(v, str) for v in item[key]):
                problems.append(f"{where}: {key} has a non-string value")
        for m, source in enumerate(item.get("sources") or []):
            if not isinstance(source, dict) or set(source) != set(SOURCE_FIELDS):
                problems.append(
                    f"{where} source {m}:"
                    f" keys {sorted(source) if isinstance(source, dict) else source!r}"
                )
            elif not all(isinstance(v, str) for v in source.values()):
                problems.append(f"{where} source {m}: non-string value")
    return problems


def build_rubric_db(rubric_dir: str | Path, db_path: str | Path) -> dict[str, int]:
    loaded, problems = {}, []
    for name, screen_field in RUBRICS.items():
        items = yaml.safe_load((Path(rubric_dir) / f"{name}.yaml").read_text())["items"]
        problems += [f"{name}: {p}" for p in rubric_schema_problems(items, screen_field)]
        loaded[name] = items
    codes = Counter(item.get("code") for items in loaded.values() for item in items)
    problems += [
        f"code {code} appears {count} times across the rubric files"
        for code, count in codes.items()
        if count > 1
    ]
    if problems:
        raise ValueError(
            "the rubric yaml files do not fit the rubric tables:\n" + "\n".join(problems)
        )
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path, isolation_level=None)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN")
        try:
            for statement in RUBRIC_SCHEMA:
                conn.execute(statement)
            for name, items in loaded.items():
                conn.execute(
                    "INSERT INTO rubrics VALUES (?, ?, ?)", (name, f"{name}.yaml", RUBRICS[name])
                )
                for position, item in enumerate(items):
                    code = item["code"]
                    conn.execute(
                        "INSERT INTO rubric_items VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            code,
                            name,
                            position,
                            item["group"],
                            item["applies_condition"],
                            item["binding"],
                            item["criterion"],
                        ),
                    )
                    conn.executemany(
                        "INSERT INTO rubric_applies_to VALUES (?, ?, ?)",
                        [(code, k, v) for k, v in enumerate(item["applies_to"])],
                    )
                    conn.executemany(
                        "INSERT INTO rubric_screens VALUES (?, ?, ?)",
                        [(code, k, v) for k, v in enumerate(item[RUBRICS[name]])],
                    )
                    conn.executemany(
                        "INSERT INTO rubric_sources VALUES (?, ?, ?, ?, ?, ?, ?)",
                        [
                            (code, k, *(s[f] for f in SOURCE_FIELDS))
                            for k, s in enumerate(item["sources"])
                        ],
                    )
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return {name: len(items) for name, items in loaded.items()}
