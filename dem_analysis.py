"""Copernicus DEM 30m → 강남권 경사도 계산 + 시각화"""
import rasterio
from rasterio.windows import from_bounds
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import geopandas as gpd

mpl.rcParams["font.family"] = "AppleGothic"
mpl.rcParams["axes.unicode_minus"] = False

DEM_PATH = "dem/seoul_dem.tif"

# 강남권 bbox (토지피복도 받은 영역과 동일)
BBOX = (127.0, 37.45, 127.125, 37.55)  # (minx, miny, maxx, maxy)

with rasterio.open(DEM_PATH) as src:
    print(f"DEM info: shape={src.shape}, crs={src.crs}, res={src.res}")
    print(f"bounds: {src.bounds}")
    # 강남권 crop
    window = from_bounds(*BBOX, transform=src.transform)
    dem = src.read(1, window=window)
    transform = src.window_transform(window)
    print(f"crop shape: {dem.shape}")
    print(f"elevation: min={dem.min():.1f}m, max={dem.max():.1f}m, mean={dem.mean():.1f}m")

# 경사도 계산 (3x3 윈도우, degrees)
def slope_degrees(dem, dx, dy):
    """dem: 2D elevation array (m), dx/dy: pixel size (m)"""
    gy, gx = np.gradient(dem.astype(float), dy, dx)
    slope_rad = np.arctan(np.hypot(gx, gy))
    return np.degrees(slope_rad)

# 위도에 따라 1° = 111km, 경도 1°= 111*cos(lat) km
pixel_lon, pixel_lat = abs(transform.a), abs(transform.e)  # degrees
mean_lat = (BBOX[1] + BBOX[3]) / 2
dx_m = pixel_lon * 111000 * np.cos(np.radians(mean_lat))
dy_m = pixel_lat * 111000
print(f"\n픽셀 크기: dx={dx_m:.1f}m, dy={dy_m:.1f}m")

slope = slope_degrees(dem, dx_m, dy_m)
print(f"경사도: min={slope.min():.2f}°, max={slope.max():.2f}°, mean={slope.mean():.2f}°")
print(f"  >5° 비율: {(slope>5).mean()*100:.1f}%")
print(f"  >10° 비율: {(slope>10).mean()*100:.1f}%")

# 시각화
fig, axes = plt.subplots(1, 2, figsize=(18, 8))

extent = [BBOX[0], BBOX[2], BBOX[1], BBOX[3]]

# 좌: 고도
ax = axes[0]
im = ax.imshow(dem, cmap="terrain", extent=extent, aspect="auto", origin="upper")
plt.colorbar(im, ax=ax, label="고도 (m)", shrink=0.7)
ax.set_title(f"Copernicus DEM 30m — 강남권 고도\n(min={dem.min():.0f}m, max={dem.max():.0f}m)",
              fontsize=13)
ax.set_xlabel("경도"); ax.set_ylabel("위도")

# 우: 경사도
ax = axes[1]
im2 = ax.imshow(slope, cmap="YlOrRd", extent=extent, aspect="auto", origin="upper", vmin=0, vmax=20)
plt.colorbar(im2, ax=ax, label="경사도 (°)", shrink=0.7)
ax.set_title(f"경사도 — 평지(파랑)일수록 침수 위험↑\n(mean={slope.mean():.1f}°, >5°={((slope>5).mean()*100):.0f}%)",
              fontsize=13)
ax.set_xlabel("경도"); ax.set_ylabel("위도")

plt.tight_layout()
plt.savefig("dem_slope.png", dpi=130, bbox_inches="tight")
print("\nSaved: dem_slope.png")

# 결과를 numpy로 저장 (RF 모델 학습용 feature로 쓸 수 있게)
np.savez("dem/slope_gangnam.npz", dem=dem, slope=slope,
         extent=np.array(extent), transform=np.array([transform.a, transform.b, transform.c,
                                                       transform.d, transform.e, transform.f]))
print("Saved: dem/slope_gangnam.npz")
