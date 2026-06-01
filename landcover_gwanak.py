"""관악구 세분류 토지피복지도 11개 도엽 → 통합"""
import zipfile
from pathlib import Path
import geopandas as gpd
import pandas as pd

SRC = Path.home() / "Downloads"
DST = Path("landcover_gwanak")
DST.mkdir(exist_ok=True)

# 관악구 도엽 (37612xxx 시리즈)
zips = sorted(SRC.glob("SG05_37612*.zip"))
print(f"관악구 zip {len(zips)}개")
for z in zips:
    out = DST / z.stem
    if not out.exists():
        out.mkdir()
        with zipfile.ZipFile(z) as zf:
            zf.extractall(out)

shps = sorted(DST.rglob("*.shp"))
print(f"shp {len(shps)}개")

dfs = []
for shp in shps:
    g = gpd.read_file(shp, encoding="cp949")
    g["sheet"] = shp.stem
    dfs.append(g)

lc = gpd.GeoDataFrame(pd.concat(dfs, ignore_index=True), crs=dfs[0].crs)
lc_wgs = lc.to_crs("EPSG:4326")
print(f"\n총 폴리곤: {len(lc):,}")
print(f"bbox (WGS84): {lc_wgs.total_bounds}")
print(f"\nL1 분포:")
print(lc["L1_CODE"].value_counts().sort_index().to_string())

lc_wgs.to_file("landcover_gwanak.geojson", driver="GeoJSON")
print(f"\n저장: landcover_gwanak.geojson")
