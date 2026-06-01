"""DEM 두 타일(N37E126 + N37E127) 머지 → 서울 전체 커버"""
import rasterio
from rasterio.merge import merge

paths = ["dem/seoul_dem_w.tif", "dem/seoul_dem.tif"]
srcs = [rasterio.open(p) for p in paths]
mosaic, transform = merge(srcs)
profile = srcs[0].profile
profile.update({"height": mosaic.shape[1], "width": mosaic.shape[2], "transform": transform})

with rasterio.open("dem/seoul_dem_merged.tif", "w", **profile) as dst:
    dst.write(mosaic)

print(f"merged shape: {mosaic.shape}, bounds: ({transform.c}, {transform.f + transform.e*mosaic.shape[1]}, {transform.c + transform.a*mosaic.shape[2]}, {transform.f})")
for s in srcs: s.close()
print("저장: dem/seoul_dem_merged.tif")
