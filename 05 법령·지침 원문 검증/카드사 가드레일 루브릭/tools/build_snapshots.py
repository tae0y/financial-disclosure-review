"""Build plain-text snapshots of the official sources behind the card guardrail rubric.

Statutes and the supervisory regulation are fetched live from law.go.kr (the version ids
below are the ones law.go.kr resolved as current on 2026-09-26). Association and FSC
documents are read from the local copies under 원문 스냅샷/원본파일/, whose SHA-256 was
matched against the issuer's download on 2026-09-26 (see manifest.csv's raw_sha256 column).

Run from this folder's parent:
    uv run --with olefile python tools/build_snapshots.py
    uv run --with olefile python tools/build_snapshots.py --only ai_act,fsc_ai_guideline
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import re
import struct
import subprocess
import sys
import tempfile
import urllib.request
import zlib
from pathlib import Path

import olefile

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "원문 스냅샷"
LOCAL = OUT / "원본파일"
UA = {"User-Agent": "Mozilla/5.0"}

SOURCES = [
    # id, title, kind, url, local file
    ("kfcpa", "금융소비자 보호에 관한 법률 [시행 2026. 1. 2.]", "html",
     "https://www.law.go.kr/LSW/lsInfoR.do?lsiSeq=277247&chrClsCd=010202&urlMode=lsInfoP&efYd=20260102&ancYnChk=0", None),
    ("kfcpa_decree", "금융소비자 보호에 관한 법률 시행령 [시행 2026. 4. 28.]", "html",
     "https://www.law.go.kr/LSW/lsInfoR.do?lsiSeq=285715&chrClsCd=010202&urlMode=lsInfoP&efYd=20260428&ancYnChk=0", None),
    ("fsc_rule", "금융소비자 보호에 관한 감독규정 [시행 2026. 4. 2.]", "html",
     "https://www.law.go.kr/LSW/admRulInfoR.do?admRulSeq=2100000276850&chrClsCd=010201", None),
    ("fsc_rule_app5", "금융소비자 보호에 관한 감독규정 [별표 5] (현행 첨부 PDF)", "pdf_url",
     "https://www.law.go.kr/LSW/flDownload.do?flSeq=163377581", None),
    ("yeojeon", "여신전문금융업법 [시행 2025. 10. 1.]", "html",
     "https://www.law.go.kr/LSW/lsInfoR.do?lsiSeq=277267&chrClsCd=010202&urlMode=lsInfoP&efYd=20251001&ancYnChk=0", None),
    ("yeojeon_decree", "여신전문금융업법 시행령 [시행 2026. 5. 6.]", "html",
     "https://www.law.go.kr/LSW/lsInfoR.do?lsiSeq=285799&chrClsCd=010202&urlMode=lsInfoP&efYd=20260506&ancYnChk=0", None),
    ("crefia_reg", "여신전문금융회사 등의 광고에 관한 규정 (2022.05.02. 개정)", "hwp_local",
     "https://m.crefia.or.kr/mobile/infocenter/regulation/selfRegulation.xx",
     "여신전문금융회사_등의_광고에_관한_규정(게시용)_FN.hwp"),
    ("crefia_guide", "여신전문금융회사 등의 광고에 관한 규정 세부지침 (2022.05.02. 개정)", "hwp_local",
     "https://m.crefia.or.kr/mobile/infocenter/regulation/selfRegulation.xx",
     "여신전문금융회사_등의_광고에_관한_규정_세부지침(게시용).hwp"),
    ("fsc_ad_guideline", "금융위원회·금융감독원 금융광고규제 가이드라인 (2021. 6. 8.)", "hwp_local",
     "https://www.fsc.go.kr/no010101/76045", "금융위원회_금융광고규제_가이드라인.hwp"),
    ("fsc_online_explain", "금융위원회 온라인 설명의무 가이드라인", "pdf_local",
     "https://www.fsc.go.kr/no010101/78276", "금융위원회_온라인_설명의무_가이드라인.pdf"),
    ("fsc_explain", "금융위원회 금융상품 설명의무의 합리적 이행을 위한 가이드라인", "pdf_local",
     "https://www.fsc.go.kr/po0201101/76243", "금융위원회_금융상품_설명의무_가이드라인.pdf"),
    # Added 2026-09-26 for the plain-language service axis (03 대조표). Local copies under
    # 원문 스냅샷/원본파일/ were matched against the issuer's download by SHA-256 on 2026-09-26.
    ("ai_act", "인공지능 발전과 신뢰 기반 조성 등에 관한 기본법 [시행 2026. 1. 22.]", "html",
     "https://www.law.go.kr/LSW/lsInfoR.do?lsiSeq=282791&chrClsCd=010202&urlMode=lsInfoP&efYd=20260122&ancYnChk=0", None),
    ("ai_act_decree", "인공지능 발전과 신뢰 기반 조성 등에 관한 기본법 시행령 [시행 2026. 8. 20.]", "html",
     "https://www.law.go.kr/LSW/lsInfoR.do?lsiSeq=288781&chrClsCd=010202&urlMode=lsInfoP&efYd=20260820&ancYnChk=0", None),
    # pdf_local_raw: `-layout` scatters this PDF's punctuation onto separate lines, so read it in text order.
    ("fsc_ai_guideline", "금융위원회 금융분야 인공지능 가이드라인 (2026. 6. 18. 발표)", "pdf_local_raw",
     "https://www.fsc.go.kr/no010101/87142", "금융위원회_금융분야_인공지능_가이드라인_2026.pdf"),
    ("nikl_public_lang", "국립국어원 한눈에 알아보는 공공언어 바로 쓰기(개정판, 2022)", "pdf_local",
     "https://www.korean.go.kr/front/etcData/etcDataView.do?mn_id=&etc_seq=699&pageIndex=1",
     "국립국어원_한눈에_알아보는_공공언어_바로_쓰기_개정판.pdf"),
    # Added 2026-09-26 while reviewing 여전법 시행령 coverage: the supervisory regulation fixes the
    # 평균연회비 used by G01, and 별표 1의3 (신용카드업자 금지행위) was collected to confirm it has no
    # consumer-page items (its body is only an attachment, so it is fetched as the law.go.kr PDF).
    ("yeojeon_rule", "여신전문금융업감독규정 [시행 2026. 5. 6.]", "html",
     "https://www.law.go.kr/LSW/admRulInfoR.do?admRulSeq=2100000279156&chrClsCd=010201", None),
    ("yeojeon_decree_app13", "여신전문금융업법 시행령 [별표 1의3] (현행 첨부 PDF)", "pdf_url",
     "https://www.law.go.kr/LSW/flDownload.do?flSeq=163876115&bylClsCd=110201", None),
]

BLOCK = re.compile(r"<\s*(/p|/div|/li|/tr|/h\d|br\s*/?|p\b[^>]*|div\b[^>]*)>", re.I)


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def html_to_text(raw: bytes) -> str:
    t = raw.decode("utf-8", errors="replace")
    t = re.sub(r"<(script|style)\b.*?</\1>", "", t, flags=re.S | re.I)
    t = BLOCK.sub("\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    lines = [re.sub(r"[ \t ]+", " ", ln).strip() for ln in t.splitlines()]
    return "\n".join(ln for ln in lines if ln)


# HWP 5.x control characters: these occupy 8 WCHARs (16 bytes) inside PARA_TEXT.
_WIDE = {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23}


def hwp_to_text(raw: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".hwp") as f:
        f.write(raw)
        f.flush()
        ole = olefile.OleFileIO(f.name)
        compressed = bool(ole.openstream("FileHeader").read()[36] & 1)
        sections = sorted((s for s in ole.listdir() if s[0] == "BodyText"), key=lambda s: int(s[1][7:]))
        paras: list[str] = []
        for sec in sections:
            data = ole.openstream(sec).read()
            if compressed:
                data = zlib.decompress(data, -15)
            i = 0
            while i < len(data):
                (h,) = struct.unpack_from("<I", data, i)
                i += 4
                tag, size = h & 0x3FF, (h >> 20) & 0xFFF
                if size == 0xFFF:
                    (size,) = struct.unpack_from("<I", data, i)
                    i += 4
                rec, i = data[i : i + size], i + size
                if tag != 67:  # HWPTAG_PARA_TEXT
                    continue
                out, j = [], 0
                while j + 1 < len(rec):
                    (c,) = struct.unpack_from("<H", rec, j)
                    if c in _WIDE:
                        out.append("\t" if c == 9 else "")
                        j += 16
                    elif c < 32:
                        out.append("\n" if c in (10, 13) else "")
                        j += 2
                    else:
                        out.append(chr(c))
                        j += 2
                paras.append("".join(out).rstrip("\n"))
    text = "\n".join(paras).encode("utf-8", "replace").decode("utf-8")
    return "\n".join(ln.rstrip() for ln in text.splitlines() if ln.strip())


def pdf_to_text(raw: bytes, layout: bool = True) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(raw)
        f.flush()
        res = subprocess.run(["pdftotext", *(["-layout"] if layout else []), f.name, "-"], capture_output=True, check=True)
    return "\n".join(ln.rstrip() for ln in res.stdout.decode("utf-8").splitlines() if ln.strip())


def local_path(local: str) -> Path:
    return LOCAL / local


def main() -> None:
    OUT.mkdir(exist_ok=True)
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M KST")
    # `--only id1,id2` rebuilds just those snapshots and keeps the other manifest rows as they are.
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    manifest = OUT / "manifest.csv"
    kept: dict[str, list[str]] = {}
    if only and manifest.exists():
        with manifest.open(encoding="utf-8") as f:
            kept = {r[0]: r for r in list(csv.reader(f))[1:]}
    rows = []
    for sid, title, kind, url, local in SOURCES:
        if only and sid not in only:
            if sid in kept:
                rows.append(kept[sid])
            continue
        raw = local_path(local).read_bytes() if local else fetch(url)
        if kind == "html":
            text = html_to_text(raw)
        elif kind == "hwp_local":
            text = hwp_to_text(raw)
        else:
            text = pdf_to_text(raw, layout=kind != "pdf_local_raw")
        origin = f"local copy: {local_path(local).relative_to(ROOT.parent)}" if local else f"fetched: {url}"
        header = f"# {title}\n# {origin}\n# official page: {url}\n# raw sha256: {hashlib.sha256(raw).hexdigest()}\n# snapshot: {now}\n"
        (OUT / f"{sid}.txt").write_text(header + text + "\n", encoding="utf-8")
        rows.append([sid, title, kind, url, local or "", hashlib.sha256(raw).hexdigest(), now, len(text.splitlines())])
        print(f"{sid}: {len(text.splitlines())} lines", file=sys.stderr)
    with (OUT / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "title", "kind", "official_url", "local_file", "raw_sha256", "snapshot_at", "lines"])
        w.writerows(rows)


if __name__ == "__main__":
    main()
