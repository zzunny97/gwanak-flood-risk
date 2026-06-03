"""주소/지번 → 위경도 — Kakao Local API

Endpoint: https://dapi.kakao.com/v2/local/search/address.json
Free tier: 일 300,000건. 한국 주소 정확도 최고.

사용:
  export KAKAO_REST_API_KEY="..."
  python geocode.py "서울특별시 관악구 신림로 340"
"""
import os
import sys
import json
import time
from pathlib import Path
import requests

KEY = os.environ.get("KAKAO_REST_API_KEY", "")
if not KEY:
    raise SystemExit("환경변수 KAKAO_REST_API_KEY 필요. 카카오 developers → 플랫폼 키 → REST API 키")

URL = "https://dapi.kakao.com/v2/local/search/address.json"
HEADERS = {"Authorization": f"KakaoAK {KEY}"}

# 디스크 캐시 — 한 번 변환한 주소는 다시 호출 안 함
CACHE_PATH = Path("geocode_cache.json")
CACHE = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}


def geocode(addr: str) -> dict | None:
    """주소 → {lon, lat, road_addr, jibun_addr} 또는 None"""
    if addr in CACHE:
        return CACHE[addr]
    r = requests.get(URL, headers=HEADERS, params={"query": addr}, timeout=10)
    r.raise_for_status()
    data = r.json()
    docs = data.get("documents", [])
    if not docs:
        result = None
    else:
        d = docs[0]
        result = {
            "lon": float(d["x"]),
            "lat": float(d["y"]),
            "road_addr": (d.get("road_address") or {}).get("address_name"),
            "jibun_addr": (d.get("address") or {}).get("address_name"),
        }
    CACHE[addr] = result
    CACHE_PATH.write_text(json.dumps(CACHE, ensure_ascii=False, indent=2))
    return result


def batch(addrs: list[str], delay: float = 0.1) -> list[dict | None]:
    out = []
    for a in addrs:
        out.append(geocode(a))
        time.sleep(delay)
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "서울특별시 관악구 신림로 340"
    print(f"질의: {query}")
    result = geocode(query)
    if result:
        print(f"  위경도: ({result['lat']:.6f}, {result['lon']:.6f})")
        print(f"  도로명: {result['road_addr']}")
        print(f"  지번:   {result['jibun_addr']}")
    else:
        print("  결과 없음")
