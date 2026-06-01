"""cURL 기반 침수흔적도 38k 페이지네이션 — subprocess로 호출"""
import subprocess, json, time
from pathlib import Path

import os
KEY = os.environ.get("SAFETY_DATA_KEY", "")
if not KEY:
    raise SystemExit("환경변수 SAFETY_DATA_KEY가 비어있습니다. safetydata.go.kr에서 API 키 발급 후 export 하세요.")
URL = "https://www.safetydata.go.kr/V2/api/DSSP-IF-00117"
CACHE = Path("flood_pages")
CACHE.mkdir(exist_ok=True)
OUT = Path("flood_all.json")

def fetch_page(page, retries=3):
    for attempt in range(retries):
        try:
            r = subprocess.run([
                "curl", "-s", "--max-time", "90",
                f"{URL}?serviceKey={KEY}&returnType=json&pageNo={page}&numOfRows=1000",
            ], capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                print(f"  curl returncode={r.returncode}")
                time.sleep(5)
                continue
            d = json.loads(r.stdout)
            if d.get("header", {}).get("resultCode") == "00":
                return d.get("body", [])
            print(f"  API 오류: {d.get('header', {}).get('resultMsg')}")
        except Exception as e:
            print(f"  시도 {attempt+1}: {type(e).__name__}: {e}")
            time.sleep(5)
    return None

# 총 페이지 수 (totalCount=38003)
TOTAL = 38003
PAGES = (TOTAL + 999) // 1000  # = 39
print(f"총 {TOTAL}건, {PAGES}페이지")

for p in range(1, PAGES + 1):
    cache = CACHE / f"page_{p:03d}.json"
    if cache.exists():
        print(f"  page {p}: skip (캐시)")
        continue
    t = time.time()
    rows = fetch_page(p)
    if rows is None:
        print(f"  page {p}: FAIL")
        continue
    cache.write_text(json.dumps(rows, ensure_ascii=False))
    print(f"  page {p}: {len(rows)}건 ({time.time()-t:.1f}s)")
    time.sleep(0.5)

# 합치기
all_rows = []
for p in range(1, PAGES + 1):
    cache = CACHE / f"page_{p:03d}.json"
    if cache.exists():
        all_rows.extend(json.loads(cache.read_text()))
OUT.write_text(json.dumps({"body": all_rows, "totalCount": len(all_rows)}, ensure_ascii=False))
print(f"\n✅ 저장: {OUT} ({len(all_rows):,}건)")
