import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib as mpl

mpl.rcParams["font.family"] = "AppleGothic"
mpl.rcParams["axes.unicode_minus"] = False

print("Loading...")
gdf = gpd.read_file("admdong.geojson")
gdf["adm_cd"] = gdf["adm_cd"].astype(str).str.zfill(8)

act = pd.read_csv("activate_emd.csv", encoding="utf-8-sig")
act["읍면동코드"] = act["읍면동코드"].astype(str).str.zfill(8)
act24 = act[act["연도"] == 2024].copy()

merged = gdf.merge(act24, left_on="adm_cd", right_on="읍면동코드", how="left")
print(f"  매칭: {merged['노후건축물비율'].notna().sum()} / {len(merged)}")

# 도시별 줌
cities = {
    "서울특별시": (126.78, 127.18, 37.42, 37.70),
    "부산광역시": (128.85, 129.30, 35.05, 35.40),
    "대구광역시": (128.45, 128.78, 35.78, 36.05),
}

fig, axes = plt.subplots(3, 3, figsize=(18, 18))

metric_cols = ["최근인구변화", "최근사업체변화", "노후건축물비율"]
metric_cmaps = ["Reds", "Reds", "Purples"]
metric_titles = ["최근 인구 감소도 (등급↑=감소↑)", "최근 사업체 감소도 (등급↑=감소↑)", "노후건축물비율 (%)"]

for row, (city, bbox) in enumerate(cities.items()):
    city_data = merged[merged["adm_nm"].str.startswith(city)]
    for col, (metric, cmap, title) in enumerate(zip(metric_cols, metric_cmaps, metric_titles)):
        ax = axes[row, col]
        city_data.plot(
            column=metric, ax=ax, cmap=cmap, legend=True,
            edgecolor="white", linewidth=0.2,
            legend_kwds={"shrink": 0.6},
            missing_kwds={"color": "lightgrey"},
        )
        ax.set_xlim(bbox[0], bbox[1])
        ax.set_ylim(bbox[2], bbox[3])
        ax.set_title(f"{city} — {title}", fontsize=11, fontweight="bold")
        ax.set_axis_off()

plt.suptitle("읍면동 단위 도시쇠퇴 핫스팟 (활성화지표 2024)",
             fontsize=16, fontweight="bold", y=0.995)
plt.tight_layout()
plt.savefig("emd_zoom.png", dpi=130, bbox_inches="tight")
print("Saved: emd_zoom.png")

# 핫스팟 추출: 서울 노후건축물비율 워스트 10
print("\n=== 서울 읍면동 노후건축물 워스트 10 ===")
seoul = merged[merged["adm_nm"].str.startswith("서울특별시")]
top = seoul.nlargest(10, "노후건축물비율")[["adm_nm", "노후건축물비율", "최근인구변화", "최근사업체변화"]]
print(top.to_string(index=False))
