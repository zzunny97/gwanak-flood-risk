"""관악구 데모 지점 자동 추출 + 사전 사진 캐싱

전략:
  - features_with_proba.geojson 에서 침수 확률 상위 셀 추출
  - 다양한 위치 분산 (한 지점에 몰리지 않게)
  - 각 셀 중심 좌표 → Street View 4방향 다운로드
"""
import geopandas as gpd
import numpy as np
from pathlib import Path
import json

from streetview import fetch_4dir, check_coverage

OUT_DEMO = Path("demo_points.json")

# 1. RF 결과 로드
gdf = gpd.read_file("features_with_proba.geojson")
print(f"전체 셀: {len(gdf):,}")
print(f"실제 침수 셀: {gdf['flood_label'].sum()}")
print(f"예측 확률 > 0.5: {(gdf['flood_proba'] > 0.5).sum()}")

# 2. 후보 셀: 실제 침수 + 예측 확률 높음 (TP에 가까운 셀)
gdf["centroid"] = gdf.geometry.centroid
candidates = gdf[(gdf["flood_label"] == 1) & (gdf["flood_proba"] > 0.5)].copy()
print(f"TP 후보(실제 침수 + 예측↑): {len(candidates)}")

# 3. 공간 분산을 위해 셀 ID 그리드 위치 기준 sampling
candidates = candidates.sort_values("flood_proba", ascending=False)

# 8개 데모 지점, 최소 거리 보장 (250m 이상 떨어지게)
selected = []
MIN_DIST_DEG = 0.0025  # ~280m

for _, row in candidates.iterrows():
    c = row["centroid"]
    too_close = any(
        abs(c.x - s["lon"]) < MIN_DIST_DEG and abs(c.y - s["lat"]) < MIN_DIST_DEG
        for s in selected
    )
    if not too_close:
        selected.append({
            "lon": c.x, "lat": c.y,
            "cell_id": row["cell_id"],
            "flood_proba": float(row["flood_proba"]),
            "impervious_ratio": float(row["impervious_ratio"]),
            "veg_ratio": float(row["veg_ratio"]),
            "elev_mean": float(row["elev_mean"]),
            "slope_mean": float(row["slope_mean"]),
        })
    if len(selected) >= 8:
        break

print(f"\n선정 데모 지점: {len(selected)}")
for i, s in enumerate(selected, 1):
    print(f"  [{i}] ({s['lat']:.5f}, {s['lon']:.5f}) "
          f"proba={s['flood_proba']:.2f}, 불투수={s['impervious_ratio']*100:.0f}%, "
          f"고도={s['elev_mean']:.0f}m, 경사={s['slope_mean']:.1f}°")

# 4. 각 지점 커버리지 확인 + 4방향 다운로드
print("\n=== Street View 다운로드 ===")
for i, s in enumerate(selected, 1):
    print(f"\n[{i}/{len(selected)}] ({s['lat']:.5f}, {s['lon']:.5f})")
    meta = check_coverage(s["lat"], s["lon"])
    s["coverage"] = meta.get("status")
    s["sv_date"] = meta.get("date")
    if meta.get("status") != "OK":
        print(f"  Street View 없음 ({meta.get('status')})")
        s["images"] = {}
        continue
    print(f"  촬영일: {meta.get('date')}")
    files = fetch_4dir(s["lat"], s["lon"])
    s["images"] = {h: str(p) for h, p in files.items()}
    print(f"  4방향 다운로드 완료: {list(files.keys())}")

OUT_DEMO.write_text(json.dumps(selected, ensure_ascii=False, indent=2))
print(f"\n저장: {OUT_DEMO}")
print(f"이미지 저장: streetview_cache/")
