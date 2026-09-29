#!/bin/sh
# Zero-cost end-to-end check against docker/docker-compose.mock.yml: submit one review with a
# free-text reader, poll it to the end, and print how the reader was chosen.
#
#     sh docker/mock-e2e.sh ["<reader free text>"] [url]
#
# Exits non-zero unless the job succeeds and the reader was chosen from the free text.
set -eu

BASE="${FDR_MOCK_BASE:-http://localhost:18000}"
TOKEN="${FDR_MOCK_API_TOKEN:-fdr_mock_local_test}"
READER="${1:-70대 은퇴자이고 카드론을 처음 알아보는 사람입니다.}"
URL="${2:-https://m.lottecard.co.kr/front/card/basic/credit/info/las-vegas?brand=city&pcYn=Y}"
PY="$(command -v python3 || command -v python)"

body=$("$PY" -c 'import json,sys; print(json.dumps({"url": sys.argv[1], "detail": "full",
  "persona": {"request": sys.argv[2], "uuid": None, "attributes": None}}, ensure_ascii=False))' \
  "$URL" "$READER")

job=$(curl -sS -X POST "$BASE/v1/reviews" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json; charset=utf-8' --data-binary "$body" \
  | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')
echo "job $job"

status=queued
for _ in $(seq 1 120); do
  status=$(curl -sS -H "Authorization: Bearer $TOKEN" "$BASE/v1/reviews/$job" \
    | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["status"])')
  [ "$status" != queued ] && [ "$status" != running ] && break
  sleep 5
done

curl -sS -H "Authorization: Bearer $TOKEN" "$BASE/v1/reviews/$job" | "$PY" -c '
import json, sys
job = json.load(sys.stdin)
print("status", job["status"])
if job["status"] != "succeeded":
    print("error", job.get("error"))
    sys.exit(1)
result = job["result"]
reader = result["summary"]["persona_explanation"]
selection = reader.get("selection") or {}
print("reader_chosen_by", reader["reader_chosen_by"])
print("profile", reader["profile"])
print("filters", json.dumps(selection.get("filters"), ensure_ascii=False))
print("match_count", selection.get("match_count"))
print("familiarity_hint", selection.get("familiarity_hint"))
print("metered_usd", result["cost"]["usd"], "(mock tokens; nothing was billed)")
sys.exit(0 if reader["reader_chosen_by"] == "agent" else 1)
'
