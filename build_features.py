"""관악구 그리드 + feature 결합 (불투수면·경사도·고도·침수 label)"""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box
import rasterio
from rasterio.windows import from_bounds
from rasterio.features import geometry_mask
import time

print("=" * 60)
print("Step 1: 그리드 + Feature 결합")
print("=" * 60)

# 1. 관악구 bbox (토지피복도에서 확인)
GWANAK_BBOX = (126.875, 37.425, 127.0, 37.50)
print(f"\n관악구 bbox: {GWANAK_BBOX}")

# 2. 그리드 생성 (100m × 100m, WGS84 기준)
# 위도 1° ≈ 111km, 경도 1° × cos(37.5°) ≈ 88km
# → 100m 셀 = 약 0.0009° lat × 0.00113° lon
CELL_LAT = 0.0009  # ~100m
CELL_LON = 0.00113  # ~100m

minx, miny, maxx, maxy = GWANAK_BBOX
xs = np.arange(minx, maxx, CELL_LON)
ys = np.arange(miny, maxy, CELL_LAT)
print(f"그리드: {len(xs)} × {len(ys)} = {len(xs)*len(ys):,} 셀")

cells = []
for i, x in enumerate(xs):
    for j, y in enumerate(ys):
        cells.append({
            "cell_id": f"{i}_{j}",
            "ix": i, "iy": j,
            "geometry": box(x, y, x + CELL_LON, y + CELL_LAT)
        })
grid = gpd.GeoDataFrame(cells, crs="EPSG:4326")
print(f"GeoDataFrame: {len(grid):,} 셀")

# 미터 좌표계로도 보유 (면적 계산용)
grid_m = grid.to_crs("EPSG:5179")
grid["cell_area_m2"] = grid_m.geometry.area
print(f"평균 셀 면적: {grid['cell_area_m2'].mean():.0f} m² (목표 ~10000)")

# 3. 토지피복도 — 불투수면 비율
print("\n--- 불투수면 비율 (L1=100 시가화 + L1=600 나지) ---")
t = time.time()
lc = gpd.read_file("landcover_gwanak.geojson")
lc["impervious"] = lc["L1_CODE"].astype(str).isin(["100", "600"])
lc_imp = lc[lc["impervious"]][["geometry"]].copy()
# 불투수 폴리곤 통합 (dissolve)
print(f"  불투수 폴리곤: {len(lc_imp):,}")
# overlay
lc_imp = lc_imp.to_crs("EPSG:5179")
grid_m_w = grid_m.copy()
grid_m_w["cell_id"] = grid["cell_id"].values
# spatial join — 교차 영역
print("  intersection 계산 중...")
inter = gpd.overlay(grid_m_w, lc_imp, how="intersection", keep_geom_type=False)
inter["inter_area"] = inter.geometry.area
imp_by_cell = inter.groupby("cell_id")["inter_area"].sum().reset_index()
imp_by_cell.columns = ["cell_id", "impervious_area"]
grid = grid.merge(imp_by_cell, on="cell_id", how="left").fillna({"impervious_area": 0})
grid["impervious_ratio"] = grid["impervious_area"] / grid["cell_area_m2"]
print(f"  ({time.time()-t:.0f}s) 불투수면 평균: {grid['impervious_ratio'].mean()*100:.1f}%")

# 4. 식생 비율 (L1=300 산림 + L1=400 초지)
print("\n--- 식생 비율 (L1=300 산림 + L1=400 초지) ---")
t = time.time()
lc_veg = lc[lc["L1_CODE"].astype(str).isin(["300", "400"])][["geometry"]].to_crs("EPSG:5179")
inter_v = gpd.overlay(grid_m_w, lc_veg, how="intersection", keep_geom_type=False)
inter_v["inter_area"] = inter_v.geometry.area
veg_by_cell = inter_v.groupby("cell_id")["inter_area"].sum().reset_index()
veg_by_cell.columns = ["cell_id", "veg_area"]
grid = grid.merge(veg_by_cell, on="cell_id", how="left").fillna({"veg_area": 0})
grid["veg_ratio"] = grid["veg_area"] / grid["cell_area_m2"]
print(f"  ({time.time()-t:.0f}s) 식생 평균: {grid['veg_ratio'].mean()*100:.1f}%")

# 5. DEM — 셀별 평균 고도/경사도
print("\n--- DEM 고도/경사도 ---")
t = time.time()
DEM_PATH = "dem/seoul_dem_merged.tif"

with rasterio.open(DEM_PATH) as src:
    # 관악구 crop
    window = from_bounds(*GWANAK_BBOX, transform=src.transform)
    dem = src.read(1, window=window).astype(float)
    transform = src.window_transform(window)
    print(f"  DEM crop shape: {dem.shape}, 고도 {dem.min():.1f}~{dem.max():.1f}m")

# 경사도 계산
mean_lat = (miny + maxy) / 2
dx_m = abs(transform.a) * 111000 * np.cos(np.radians(mean_lat))
dy_m = abs(transform.e) * 111000
gy, gx = np.gradient(dem, dy_m, dx_m)
slope = np.degrees(np.arctan(np.hypot(gx, gy)))
print(f"  경사도 평균: {slope.mean():.2f}°")

# 그리드 셀별로 픽셀 추출
def cell_stats(row):
    cx_min, cy_min, cx_max, cy_max = row.geometry.bounds
    # 픽셀 인덱스
    px_min = int((cx_min - transform.c) / transform.a)
    py_min = int((cy_min - transform.f) / transform.e)
    px_max = int((cx_max - transform.c) / transform.a) + 1
    py_max = int((cy_max - transform.f) / transform.e) + 1
    # transform.e는 음수 (위에서 아래로)
    py_lo, py_hi = sorted([py_min, py_max])
    px_lo, px_hi = sorted([px_min, px_max])
    py_lo = max(0, py_lo); py_hi = min(dem.shape[0], py_hi)
    px_lo = max(0, px_lo); px_hi = min(dem.shape[1], px_hi)
    if py_hi <= py_lo or px_hi <= px_lo:
        return pd.Series({"elev_mean": np.nan, "elev_min": np.nan, "slope_mean": np.nan, "slope_max": np.nan})
    e = dem[py_lo:py_hi, px_lo:px_hi]
    s = slope[py_lo:py_hi, px_lo:px_hi]
    return pd.Series({
        "elev_mean": float(e.mean()),
        "elev_min": float(e.min()),
        "slope_mean": float(s.mean()),
        "slope_max": float(s.max()),
    })

stats = grid.apply(cell_stats, axis=1)
grid = pd.concat([grid, stats], axis=1)
print(f"  ({time.time()-t:.0f}s) 고도 결합 완료")

# 6. 침수 label
print("\n--- 침수 label ---")
t = time.time()
flood = gpd.read_file("flood_gwanak.geojson")
flood_m = flood[["geometry"]].to_crs("EPSG:5179")
print(f"  침수 폴리곤: {len(flood_m):,}")
inter_f = gpd.overlay(grid_m_w, flood_m, how="intersection", keep_geom_type=False)
inter_f["inter_area"] = inter_f.geometry.area
flood_by_cell = inter_f.groupby("cell_id")["inter_area"].sum().reset_index()
flood_by_cell.columns = ["cell_id", "flood_area"]
grid = grid.merge(flood_by_cell, on="cell_id", how="left").fillna({"flood_area": 0})
grid["flood_ratio"] = grid["flood_area"] / grid["cell_area_m2"]
# binary label: 셀의 1% 이상 침수 → 1
grid["flood_label"] = (grid["flood_ratio"] > 0.01).astype(int)
print(f"  ({time.time()-t:.0f}s) 침수셀 (>1%): {grid['flood_label'].sum():,} / {len(grid):,} ({grid['flood_label'].mean()*100:.1f}%)")

# 7. 저장
print("\n--- 저장 ---")
# 모든 셀 (관악구 bbox 안의 직사각형이라 외곽에 NaN 있음)
grid_clean = grid.dropna(subset=["elev_mean"]).copy()
print(f"NaN 제거 후: {len(grid_clean):,} 셀")

grid_clean.to_file("features_gwanak.geojson", driver="GeoJSON")
grid_clean.drop(columns=["geometry"]).to_csv("features_gwanak.csv", index=False)
print("저장: features_gwanak.geojson, features_gwanak.csv")

# 요약
print("\n=== Feature 요약 ===")
feat_cols = ["impervious_ratio", "veg_ratio", "elev_mean", "elev_min",
             "slope_mean", "slope_max", "flood_ratio", "flood_label"]
print(grid_clean[feat_cols].describe().round(3).to_string())
