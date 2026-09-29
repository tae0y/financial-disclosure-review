"""A tiny stand-in for the Nemotron parquet shards, written into tmp_path by the tests."""

from pathlib import Path
from typing import Any

import duckdb

from financial_disclosure_review.domain.persona_explanation.dataset import SHARDS, dataset_dir

COLUMNS = (
    "uuid",
    "professional_persona",
    "sports_persona",
    "arts_persona",
    "travel_persona",
    "culinary_persona",
    "family_persona",
    "persona",
    "cultural_background",
    "skills_and_expertise",
    "skills_and_expertise_list",
    "hobbies_and_interests",
    "hobbies_and_interests_list",
    "career_goals_and_ambitions",
    "sex",
    "age",
    "marital_status",
    "military_status",
    "family_type",
    "housing_type",
    "education_level",
    "bachelors_field",
    "occupation",
    "district",
    "province",
    "country",
)

# (uuid suffix, sex, age, education_level, occupation, province, family_type, housing_type,
#  marital_status)
_PEOPLE = (
    ("01", "여자", 74, "초등학교", "무직", "서울", "배우자와 거주", "아파트", "사별"),
    (
        "02",
        "남자",
        45,
        "4년제 대학교",
        "은행 사무원",
        "경기",
        "배우자·자녀와 거주",
        "아파트",
        "배우자있음",
    ),
    ("03", "여자", 23, "2~3년제 전문대학", "간호사", "부산", "부모와 동거", "다세대주택", "미혼"),
    ("04", "남자", 36, "고등학교", "보험 설계사", "서울", "혼자 거주", "아파트", "미혼"),
    ("05", "여자", 52, "대학원", "대학 교수", "대전", "배우자·자녀와 거주", "아파트", "배우자있음"),
    ("06", "남자", 81, "무학", "무직", "전라남", "혼자 거주", "단독주택", "사별"),
    ("07", "여자", 31, "4년제 대학교", "회계 사무원", "서울", "혼자 거주", "다세대주택", "미혼"),
    ("08", "남자", 58, "중학교", "택시 운전원", "경기", "배우자와 거주", "단독주택", "배우자있음"),
    ("09", "여자", 40, "고등학교", "주방 보조원", "인천", "자녀와 거주 (한부모)", "아파트", "이혼"),
)


def uuid_of(suffix: str) -> str:
    return "0" * 30 + suffix


def make_rows() -> list[dict]:
    rows = []
    for suffix, sex, age, education, occupation, province, family, housing, marital in _PEOPLE:
        row: dict[str, Any] = {column: f"{column} of {suffix}" for column in COLUMNS}
        row.update(
            uuid=uuid_of(suffix),
            persona=f"{age}세 {occupation}인 가상의 인물 {suffix}입니다.",
            sex=sex,
            age=age,
            marital_status=marital,
            military_status="비현역",
            family_type=family,
            housing_type=housing,
            education_level=education,
            bachelors_field="해당없음",
            occupation=occupation,
            district=f"{province}-중구",
            province=province,
            country="대한민국",
        )
        rows.append(row)
    return rows


def write_parquet(path: Path, rows: list[dict]) -> None:
    columns = ", ".join(f"{c} {'BIGINT' if c == 'age' else 'VARCHAR'}" for c in COLUMNS)
    con = duckdb.connect()
    con.execute(f"CREATE TABLE t ({columns})")
    marks = ", ".join("?" for _ in COLUMNS)
    con.executemany(f"INSERT INTO t VALUES ({marks})", [[r[c] for c in COLUMNS] for r in rows])
    path.parent.mkdir(parents=True, exist_ok=True)
    target = str(path).replace("'", "''")
    con.execute(f"COPY t TO '{target}' (FORMAT parquet)")
    con.close()


def write_store(folder: Path, rows: list[dict] | None = None) -> Path:
    """One parquet file holding every row; enough for PersonaStore."""
    write_parquet(folder / "rows.parquet", rows if rows is not None else make_rows())
    return folder


def write_dataset(data_dir: Path) -> Path:
    """Every pinned shard name present, one row each, as choose_profile expects on disk."""
    folder = dataset_dir(data_dir)
    for shard, row in zip(sorted(SHARDS), make_rows(), strict=True):
        write_parquet(folder / shard, [row])
    return folder
