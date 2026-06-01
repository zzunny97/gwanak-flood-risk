"""행정안전부 침수흔적도 API 수집"""
import requests, json, urllib3, time
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://www.safetydata.go.kr/V2/api/DSSP-IF-00117"
import os
KEY = os.environ.get("SAFETY_DATA_KEY", "")
if not KEY:
    raise SystemExit("환경변수 SAFETY_DATA_KEY 필요")
OUT = Path("flood_traces.json")

# 일 1000건 한도 → 1 페이지 1000건으로 1번에 받기
r = requests.get(URL, params={
    "serviceKey": KEY, "returnType": "json",
    "pageNo": 1, "numOfRows": 1000,
}, verify=False, timeout=60)
data = r.json()

print(f"resultMsg: {data['header']['resultMsg']}")
print(f"totalCount: {data['totalCount']}")
print(f"받은 건수: {len(data['body'])}")

OUT.write_text(json.dumps(data, ensure_ascii=False, indent=None))
print(f"저장: {OUT}")
