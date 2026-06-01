"""flood_all.json (38k) → GeoJSON (EPSG:4326)"""
import json
import pandas as pd
import geopandas as gpd
from shapely import wkt

raw = json.loads(open("flood_all.json").read())
df = pd.DataFrame(raw["body"])
print(f"총 {len(df):,}건")

# GEOM 파싱
df["geometry"] = df["GEOM"].apply(wkt.loads)
gdf = gpd.GeoDataFrame(df.drop(columns=["GEOM"]), geometry="geometry", crs="EPSG:3857").to_crs("EPSG:4326")
print(f"CRS: {gdf.crs}")
print(f"bbox: {gdf.total_bounds}")

# 시군구 단위 통계 추가
sido_map = {"11":"서울","26":"부산","27":"대구","28":"인천","29":"광주","30":"대전","31":"울산","36":"세종",
            "41":"경기","42":"강원","43":"충북","44":"충남","45":"전북","46":"전남","47":"경북","48":"경남","50":"제주"}
gdf["시도명"] = gdf["STDG_CTPV_CD"].astype(str).map(sido_map)

gdf.to_file("flood_all.geojson", driver="GeoJSON")
print(f"\n저장: flood_all.geojson ({len(gdf):,} 폴리곤)")

# 관악구만 따로
gwanak = gdf[gdf["STDG_SGG_CD"] == "11620"].copy()
gwanak.to_file("flood_gwanak.geojson", driver="GeoJSON")
print(f"저장: flood_gwanak.geojson ({len(gwanak):,} 폴리곤)")

# 강남권(현재 토지피복도 영역)만
gangnam_sgg = ["11680", "11650", "11710"]  # 강남/서초/송파
gangnam = gdf[gdf["STDG_SGG_CD"].isin(gangnam_sgg)].copy()
gangnam.to_file("flood_gangnam.geojson", driver="GeoJSON")
print(f"저장: flood_gangnam.geojson ({len(gangnam):,} 폴리곤)")
