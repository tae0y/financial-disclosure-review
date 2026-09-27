#!/bin/sh
# Build the reference DB on first boot, then hand off to uvicorn.
#
# `data/*.sqlite` is gitignored and the rubric yaml lives outside the repo, so neither can be
# baked into the image. The rubric folder is mounted read-only; this builds the DB into the data
# volume once and skips the work on every later boot.
set -eu

DB_PATH="${FDR_DB_PATH:-${FDR_DATA_DIR:-/app/data}/reference.sqlite}"
RUBRIC_DIR="${FDR_RUBRIC_DIR:-/app/rubrics}"

if [ -f "$DB_PATH" ]; then
    echo "entrypoint: reference DB present at $DB_PATH"
elif [ -d "$RUBRIC_DIR" ]; then
    echo "entrypoint: building reference DB from $RUBRIC_DIR"
    python -m financial_disclosure_review build-db \
        --rubric-dir "$RUBRIC_DIR" \
        --db-path "$DB_PATH"
else
    echo "entrypoint: WARNING no reference DB and no rubric dir at $RUBRIC_DIR;" \
         "rubric-backed judgments will come back 판정 불가" >&2
fi

exec "$@"
