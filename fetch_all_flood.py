"""전체 침수흔적도(38003건) 페이지네이션 수집 — retry 포함"""
import requests, json, urllib3, time
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
URL = "https://www.safetydata.go.kr/V2/api/DSSP-IF-00117"
import os
KEY = os.environ.get("SAFETY_DATA_KEY", "")
if not KEY:
    raise SystemExit("환경변수 SAFETY_DATA_KEY 필요")
OUT = Path("flood_all.json")

def fetch_with_retry(params, retries=8, base_delay=5):
    """connection timeout 대응: exponential backoff"""
    for attempt in range(retries):
        try:
            r = requests.get(URL, params=params, verify=False, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            wait = base_delay * (2 ** attempt) if attempt > 0 else base_delay
            wait = min(wait, 60)
            print(f"    재시도 {attempt+1}/{retries} ({type(e).__name__}) → {wait}s 대기")
            time.sleep(wait)
    return None

# 페이지별 캐시: 이미 받은 페이지는 스킵 (재시작 가능하게)
CACHE_DIR = Path("flood_pages")
CACHE_DIR.mkdir(exist_ok=True)

# totalCount 확인
print("총 건수 확인 중...")
r0 = fetch_with_retry({"serviceKey": KEY, "returnType": "json", "pageNo": 1, "numOfRows": 1})
if r0 is None:
    raise SystemExit("API 응답 실패. 잠시 후 다시 시도하세요.")
total = r0["totalCount"]
pages = (total + 999) // 1000
print(f"총 {total}건, {pages}페이지 수집 시작\n")

for p in range(1, pages + 1):
    cache = CACHE_DIR / f"page_{p:03d}.json"
    if cache.exists():
        print(f"  page {p}: 캐시 사용 (skip)")
        continue
    print(f"  page {p} 요청...")
    d = fetch_with_retry({"serviceKey": KEY, "returnType": "json",
                          "pageNo": p, "numOfRows": 1000})
    if d is None or d["header"]["resultCode"] != "00":
        print(f"  page {p} 실패 — 다음 페이지 진행")
        continue
    rows = d["body"]
    cache.write_text(json.dumps(rows, ensure_ascii=False))
    print(f"  page {p}: {len(rows)}건 저장")
    time.sleep(2.0)  # 서버 부하 방지

# 합치기
all_rows = []
for p in range(1, pages + 1):
    cache = CACHE_DIR / f"page_{p:03d}.json"
    if cache.exists():
        all_rows.extend(json.loads(cache.read_text()))
OUT.write_text(json.dumps({"body": all_rows, "totalCount": len(all_rows)}, ensure_ascii=False))
print(f"\n저장: {OUT} ({len(all_rows)}건)")
