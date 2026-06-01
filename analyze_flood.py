"""침수흔적도 데이터 EDA + 시각화"""
import json
import pandas as pd
import geopandas as gpd
from shapely import wkt
import matplotlib.pyplot as plt
import matplotlib as mpl

mpl.rcParams["font.family"] = "AppleGothic"
mpl.rcParams["axes.unicode_minus"] = False

# 1. 로드
raw = json.loads(open("flood_traces.json").read())
df = pd.DataFrame(raw["body"])
print(f"=== 침수흔적도 1000건 ===")
print(f"컬럼: {list(df.columns)}")
print(f"shape: {df.shape}")
print()

# 2. 기본 통계
print("=== 침수연도 분포 (TOP 10) ===")
print(df["FLDN_YR"].value_counts().head(10).to_string())
print()
print("=== 침수등급 분포 ===")
print(df["FLDN_GRD"].value_counts().sort_index().to_string())
print()
print("=== 침수수심(m) 통계 ===")
print(df["FLDN_DOWA"].describe().round(2).to_string())
print()
print("=== 침수면적(㎡) 통계 ===")
print(df["FLDN_AREA"].describe().round(0).to_string())
print()
print("=== 시도코드별 사건 수 ===")
print(df["STDG_CTPV_CD"].value_counts().to_string())
print()
print("=== 침수재해명 TOP 10 ===")
print(df["FLDN_DST_NM"].value_counts().head(10).to_string())

# 3. GeoDataFrame으로 변환
df["geometry"] = df["GEOM"].apply(wkt.loads)
gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:3857").to_crs("EPSG:4326")
print(f"\n변환 후 CRS: {gdf.crs}")
print(f"전체 bbox: {gdf.total_bounds}")

# 4. 시각화 (2x2)
fig, axes = plt.subplots(2, 2, figsize=(18, 14))

# 4-1 전국 침수흔적 위치
ax = axes[0, 0]
gdf.plot(ax=ax, column="FLDN_GRD", cmap="Reds", markersize=8, legend=True,
          legend_kwds={"shrink": 0.6, "label": "침수등급"})
ax.set_title(f"침수흔적도 위치 분포 (n={len(gdf)}, 표본 1000건)", fontsize=13)
ax.set_xlabel("경도"); ax.set_ylabel("위도")
ax.grid(alpha=0.3)

# 4-2 연도별 사건 수
ax = axes[0, 1]
yr_counts = df["FLDN_YR"].value_counts().sort_index()
ax.bar(yr_counts.index.astype(str), yr_counts.values, color="#1f77b4")
ax.set_title("연도별 침수사건 (표본)", fontsize=13)
ax.set_xlabel("연도"); ax.set_ylabel("건수")
ax.tick_params(axis="x", rotation=45)
ax.grid(alpha=0.3, axis="y")

# 4-3 침수수심 분포
ax = axes[1, 0]
ax.hist(df["FLDN_DOWA"].dropna(), bins=40, color="#d62728", alpha=0.7, edgecolor="white")
ax.set_title(f"침수수심 분포 (m, mean={df['FLDN_DOWA'].mean():.2f}, max={df['FLDN_DOWA'].max():.2f})", fontsize=13)
ax.set_xlabel("침수수심 (m)"); ax.set_ylabel("빈도")
ax.grid(alpha=0.3, axis="y")

# 4-4 시도별
ax = axes[1, 1]
sido_map = {"11":"서울","26":"부산","27":"대구","28":"인천","29":"광주","30":"대전","31":"울산","36":"세종",
            "41":"경기","42":"강원","43":"충북","44":"충남","45":"전북","46":"전남","47":"경북","48":"경남","50":"제주",
            "51":"강원특자","52":"전북특자"}
df["시도"] = df["STDG_CTPV_CD"].astype(str).map(sido_map).fillna("기타")
sido_counts = df["시도"].value_counts()
ax.barh(sido_counts.index, sido_counts.values, color="#2ca02c")
ax.set_title("시도별 침수사건 (표본)", fontsize=13)
ax.set_xlabel("건수"); ax.invert_yaxis()
ax.grid(alpha=0.3, axis="x")

plt.suptitle("행정안전부 침수흔적도 — 1000건 표본 EDA", fontsize=15, fontweight="bold", y=0.995)
plt.tight_layout()
plt.savefig("flood_eda.png", dpi=130, bbox_inches="tight")
print("\nSaved: flood_eda.png")

# 5. GeoJSON 저장 (다음 분석용)
gdf.drop(columns=["GEOM"]).to_file("flood_traces.geojson", driver="GeoJSON")
print("Saved: flood_traces.geojson")
