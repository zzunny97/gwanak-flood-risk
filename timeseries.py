import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import re

mpl.rcParams["font.family"] = "AppleGothic"
mpl.rcParams["axes.unicode_minus"] = False

# boundary
gdf = gpd.read_file("admdong.geojson")
def normalize(adm_nm):
    parts = adm_nm.split(" ")
    sido, sigungu = parts[0], parts[1]
    m = re.match(r"(.+시)[가-힣]+구$", sigungu)
    if m: sigungu = m.group(1)
    return f"{sido} {sigungu}"
gdf["시군구명"] = gdf["adm_nm"].apply(normalize)
sigungu = gdf.dissolve(by="시군구명", as_index=False)[["시군구명", "geometry"]]

# decline 시계열
dec = pd.read_csv("decline_sigungu.csv", encoding="cp949")
print("decline 사용 가능 연도(>=90% 결측):", sorted(dec[dec["연도"].isin([2015,2018,2020,2022])]["연도"].unique()))

# 핵심 3개 지표 시계열로 보기 (결측 적은 컬럼)
target_cols = ["노후건축물비율", "노령화지수(주민등록인구통계)", "인구변화율(주민등록인구통계)"]
years = [2020, 2024]

# 피벗: 각 지표 × 연도
records = []
for yr in years:
    sub = dec[dec["연도"] == yr][["시군구명"] + target_cols].copy()
    sub["연도"] = yr
    records.append(sub)
ts = pd.concat(records, ignore_index=True)
print(f"\n시계열 데이터: {len(ts)}")

# 와이드로 변환
pv = ts.pivot_table(index="시군구명", columns="연도", values=target_cols)
print(f"피벗 shape: {pv.shape}")

# 노령화지수 가속도 계산 (2024 - 2015)
ageing = pv["노령화지수(주민등록인구통계)"]
delta = (ageing[2024] - ageing[2020]).rename("노령화_증가")
old_built = pv["노후건축물비율"]
delta_built = (old_built[2024] - old_built[2020]).rename("노후건축_증가")

worsened = pd.concat([ageing[2020], ageing[2024], delta, old_built[2020], old_built[2024], delta_built], axis=1)
worsened.columns = ["노령화_2020", "노령화_2024", "노령화_증가", "노후건축_2020", "노후건축_2024", "노후건축_증가"]

# 악화 가속 워스트 10 (노령화 증가)
print("\n=== 노령화 가속 워스트 10 (2020→2024 증가량) ===")
print(worsened.nlargest(10, "노령화_증가").to_string())

# 시각화
fig, axes = plt.subplots(2, 3, figsize=(20, 12))

# 1행: 노령화 2015 / 2024 / 증가량
for i, (col, title, cmap) in enumerate([
    ("노령화_2020", "노령화지수 2020", "OrRd"),
    ("노령화_2024", "노령화지수 2024", "OrRd"),
    ("노령화_증가", "노령화지수 증가 (2020→2024)", "RdPu"),
]):
    ax = axes[0, i]
    m = sigungu.merge(worsened.reset_index(), on="시군구명", how="left")
    m.plot(column=col, ax=ax, cmap=cmap, legend=True,
           edgecolor="white", linewidth=0.2,
           legend_kwds={"shrink": 0.6},
           missing_kwds={"color": "lightgrey"})
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_axis_off()

# 2행: 노후건축물 비율 시계열
for i, (col, title, cmap) in enumerate([
    ("노후건축_2020", "노후건축물비율 2020", "Purples"),
    ("노후건축_2024", "노후건축물비율 2024", "Purples"),
    ("노후건축_증가", "노후건축물비율 증가 (2020→2024)", "RdPu"),
]):
    ax = axes[1, i]
    m = sigungu.merge(worsened.reset_index(), on="시군구명", how="left")
    m.plot(column=col, ax=ax, cmap=cmap, legend=True,
           edgecolor="white", linewidth=0.2,
           legend_kwds={"shrink": 0.6},
           missing_kwds={"color": "lightgrey"})
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_axis_off()

plt.suptitle("시계열 비교 — 도시쇠퇴 악화 추이 (2020 → 2024)",
             fontsize=16, fontweight="bold", y=0.995)
plt.tight_layout()
plt.savefig("timeseries.png", dpi=130, bbox_inches="tight")
print("\nSaved: timeseries.png")
