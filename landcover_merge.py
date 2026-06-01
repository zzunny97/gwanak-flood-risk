"""세분류 토지피복지도 도엽 15장 → 하나로 통합"""
import zipfile
from pathlib import Path
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

mpl.rcParams["font.family"] = "AppleGothic"
mpl.rcParams["axes.unicode_minus"] = False

SRC = Path.home() / "Downloads"
DST = Path("landcover")
DST.mkdir(exist_ok=True)

# 1. 압축 풀기
zips = sorted(SRC.glob("SG05_*.zip"))
print(f"zip 파일 {len(zips)}개")
for z in zips:
    out = DST / z.stem
    if not out.exists():
        out.mkdir()
        with zipfile.ZipFile(z) as zf:
            zf.extractall(out)
    print(f"  {z.name} → {out.name}")

# 2. shp 파일 다 찾기
shps = sorted(DST.rglob("*.shp"))
print(f"\nshp 파일 {len(shps)}개")

# 3. 합치기
dfs = []
for shp in shps:
    g = gpd.read_file(shp, encoding="cp949")
    g["sheet"] = shp.stem
    dfs.append(g)
    print(f"  {shp.stem}: {len(g)}행, CRS={g.crs}, cols={list(g.columns)[:6]}")

lc = gpd.GeoDataFrame(pd.concat(dfs, ignore_index=True), crs=dfs[0].crs)
print(f"\n전체 폴리곤: {len(lc):,}개")
print(f"CRS: {lc.crs}")
print(f"컬럼: {list(lc.columns)}")
print(f"\n클래스 코드 분포 (TOP):")
# 일반적으로 L3_CODE 또는 L3_NAME 컬럼
code_col = None
for c in lc.columns:
    if "L3" in c.upper() or "CODE" in c.upper() or "분류" in c:
        code_col = c
        break
if code_col:
    print(lc[code_col].value_counts().head(15).to_string())
    print(f"\n→ 분류 컬럼: {code_col}")

# 4. WGS84로 변환 후 저장
lc_wgs = lc.to_crs("EPSG:4326")
out_path = "landcover_merged.geojson"
lc_wgs.to_file(out_path, driver="GeoJSON")
print(f"\n저장: {out_path}")
print(f"bbox: {lc_wgs.total_bounds}")
