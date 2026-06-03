"""좌표 → Google Street View Static API 이미지

요금: $7/1000 (월 $200 무료 크레딧 자동 적용 = ~28,500장 무료)

사용:
  export GOOGLE_MAPS_API_KEY="..."
  python streetview.py                  # 신림로 340 4방향 다운로드
  python streetview.py 37.4847 126.9301 # 임의 좌표
"""
import os
import sys
import hashlib
from pathlib import Path
import requests

KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
if not KEY:
    raise SystemExit("환경변수 GOOGLE_MAPS_API_KEY 필요")

URL = "https://maps.googleapis.com/maps/api/streetview"
META_URL = "https://maps.googleapis.com/maps/api/streetview/metadata"
CACHE_DIR = Path("streetview_cache")
CACHE_DIR.mkdir(exist_ok=True)


def cache_key(lat: float, lon: float, heading: int, size: str, fov: int) -> str:
    """좌표·각도 기반 고유 파일명"""
    raw = f"{lat:.6f}_{lon:.6f}_h{heading}_{size}_fov{fov}"
    return raw


def check_coverage(lat: float, lon: float) -> dict:
    """metadata API — 해당 좌표에 Street View 있는지 (무료, 비용 안 듦)"""
    r = requests.get(META_URL, params={
        "location": f"{lat},{lon}", "key": KEY,
    }, timeout=10)
    r.raise_for_status()
    return r.json()


def fetch(lat: float, lon: float, heading: int = 0,
          size: str = "640x640", fov: int = 90, pitch: int = 0) -> Path | None:
    """단일 사진 다운로드. 캐시 있으면 재호출 안 함. 반환: 저장 경로"""
    key_str = cache_key(lat, lon, heading, size, fov)
    out = CACHE_DIR / f"{key_str}.jpg"
    if out.exists() and out.stat().st_size > 1000:
        return out

    r = requests.get(URL, params={
        "size": size, "location": f"{lat},{lon}",
        "heading": heading, "pitch": pitch, "fov": fov,
        "key": KEY, "return_error_code": "true",
    }, timeout=15)
    if r.status_code != 200:
        print(f"  실패 ({lat},{lon}) heading={heading}: HTTP {r.status_code} {r.text[:100]}")
        return None
    out.write_bytes(r.content)
    return out


def fetch_4dir(lat: float, lon: float, **kwargs) -> dict[int, Path]:
    """0/90/180/270도 4방향 자동 다운로드. 반환: {heading: path}"""
    result = {}
    for h in (0, 90, 180, 270):
        p = fetch(lat, lon, heading=h, **kwargs)
        if p:
            result[h] = p
    return result


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        lat, lon = float(sys.argv[1]), float(sys.argv[2])
        label = f"좌표 ({lat}, {lon})"
    else:
        lat, lon = 37.484763, 126.930097
        label = "신림로 340 (기본)"

    print(f"=== {label} ===")
    meta = check_coverage(lat, lon)
    print(f"커버리지: status={meta.get('status')}, date={meta.get('date')}, pano_id={meta.get('pano_id', '')[:20]}...")
    if meta.get("status") != "OK":
        print("Street View 데이터 없음")
        sys.exit(1)

    print("4방향 다운로드 중...")
    files = fetch_4dir(lat, lon)
    for h, p in files.items():
        print(f"  heading={h:3d}°: {p} ({p.stat().st_size//1024}KB)")
    print(f"\n저장: {CACHE_DIR}/")
