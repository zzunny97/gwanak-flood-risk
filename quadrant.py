import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import re

mpl.rcParams["font.family"] = "AppleGothic"
mpl.rcParams["axes.unicode_minus"] = False

# === 1. 시군구 boundary ===
print("Loading boundary...")
gdf = gpd.read_file("admdong.geojson")

def normalize(adm_nm):
    parts = adm_nm.split(" ")
    sido, sigungu = parts[0], parts[1]
    m = re.match(r"(.+시)[가-힣]+구$", sigungu)
    if m:
        sigungu = m.group(1)
    return f"{sido} {sigungu}"

gdf["시군구명"] = gdf["adm_nm"].apply(normalize)
sigungu = gdf.dissolve(by="시군구명", as_index=False)[["시군구명", "geometry"]]
print(f"  시군구 boundary {len(sigungu)}")

# === 2. 쇠퇴 점수 (activate 2024) ===
act = pd.read_csv("activate_sigungu.csv", encoding="cp949")
act24 = act[act["연도"] == 2024].copy()
# 등급: 1(좋음) ~ 10(나쁨). 인구/사업체 감소 + 노후건축물 평균.
# 노후건축물비율은 값 그대로 → 분위수로 등급화
act24["노후_q"] = pd.qcut(act24["노후건축물비율"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(float)
act24["쇠퇴등급"] = act24[["최근인구변화", "최근사업체변화", "노후_q"]].mean(axis=1)
print(f"\n쇠퇴등급 분포: min={act24['쇠퇴등급'].min():.2f}, max={act24['쇠퇴등급'].max():.2f}, mean={act24['쇠퇴등급'].mean():.2f}")

# === 3. 잠재력 점수 (potential 2020) ===
pot = pd.read_csv("potential_sigungu.csv", encoding="cp949")
pot20 = pot[pot["연도"] == 2020].copy()
pot_cols = ["1인당지역내총생산등급", "특허출원건수등급", "20세미만인구성장률등급", "1인당주민세등급", "재정자립도등급"]
# 등급: 1(낮음) ~ 10(높음) — 잠재력은 높을수록 양호
pot20["잠재력등급"] = pot20[pot_cols].mean(axis=1)
print(f"잠재력등급 분포: min={pot20['잠재력등급'].min():.2f}, max={pot20['잠재력등급'].max():.2f}, mean={pot20['잠재력등급'].mean():.2f}")

# === 4. 조인 ===
df = act24[["시군구명", "쇠퇴등급", "노후건축물비율", "최근인구변화"]].merge(
    pot20[["시군구명", "잠재력등급"]], on="시군구명", how="inner"
)
print(f"\n조인 시군구: {len(df)}")

# 4분면 분류 (median 기준)
dec_med = df["쇠퇴등급"].median()
pot_med = df["잠재력등급"].median()

def classify(row):
    high_decline = row["쇠퇴등급"] >= dec_med
    high_potential = row["잠재력등급"] >= pot_med
    if high_decline and high_potential:
        return "재생가능 (쇠퇴↑ 잠재력↑)"
    if high_decline and not high_potential:
        return "고위험 (쇠퇴↑ 잠재력↓)"
    if not high_decline and high_potential:
        return "유망 (쇠퇴↓ 잠재력↑)"
    return "안정 (쇠퇴↓ 잠재력↓)"

df["분류"] = df.apply(classify, axis=1)
print("\n분면별 시군구 수:")
print(df["분류"].value_counts().to_string())

# 지도와 조인
mapped = sigungu.merge(df, on="시군구명", how="left")

# === 5. 시각화: 좌(산점도) + 우(지도) ===
fig = plt.figure(figsize=(20, 11))
gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.2])
ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1])

color_map = {
    "고위험 (쇠퇴↑ 잠재력↓)": "#d62728",
    "재생가능 (쇠퇴↑ 잠재력↑)": "#ff7f0e",
    "유망 (쇠퇴↓ 잠재력↑)": "#2ca02c",
    "안정 (쇠퇴↓ 잠재력↓)": "#1f77b4",
}

# 좌측: 산점도
for cat, color in color_map.items():
    sub = df[df["분류"] == cat]
    ax1.scatter(sub["잠재력등급"], sub["쇠퇴등급"], c=color, s=60, alpha=0.7,
                edgecolor="white", linewidth=0.5, label=f"{cat} (n={len(sub)})")

ax1.axvline(pot_med, color="grey", linestyle="--", alpha=0.5)
ax1.axhline(dec_med, color="grey", linestyle="--", alpha=0.5)
ax1.set_xlabel("잠재력 등급 (높을수록 잠재력↑)", fontsize=12)
ax1.set_ylabel("쇠퇴 등급 (높을수록 쇠퇴↑)", fontsize=12)
ax1.set_title("시군구 4분면 분류 — 쇠퇴 vs 잠재력", fontsize=14, fontweight="bold")
ax1.legend(loc="upper left", fontsize=9, framealpha=0.95)
ax1.grid(alpha=0.3)

# 워스트 5 라벨
worst = df.nlargest(5, "쇠퇴등급")
for _, r in worst.iterrows():
    ax1.annotate(r["시군구명"].split()[-1], (r["잠재력등급"], r["쇠퇴등급"]),
                 fontsize=8, ha="left", xytext=(4, 4), textcoords="offset points")

# 우측: 지도
mapped_colored = mapped.copy()
mapped_colored["color"] = mapped_colored["분류"].map(color_map).fillna("#dddddd")
mapped_colored.plot(ax=ax2, color=mapped_colored["color"], edgecolor="white", linewidth=0.3)

# 범례
from matplotlib.patches import Patch
patches = [Patch(facecolor=c, label=k) for k, c in color_map.items()]
patches.append(Patch(facecolor="#dddddd", label="데이터없음"))
ax2.legend(handles=patches, loc="lower left", fontsize=10, framealpha=0.95)
ax2.set_title("4분면 분류 지도", fontsize=14, fontweight="bold")
ax2.set_axis_off()

plt.suptitle("도시계획 리스크 진단 — 활성화지표(2024) × 잠재력지표(2020) 4분면",
             fontsize=16, fontweight="bold", y=1.0)
plt.tight_layout()
plt.savefig("quadrant_map.png", dpi=140, bbox_inches="tight")
print("\nSaved: quadrant_map.png")

# 분면별 대표 시군구
print("\n=== 분면별 대표 시군구 ===")
for cat in ["고위험 (쇠퇴↑ 잠재력↓)", "재생가능 (쇠퇴↑ 잠재력↑)", "유망 (쇠퇴↓ 잠재력↑)", "안정 (쇠퇴↓ 잠재력↓)"]:
    sub = df[df["분류"] == cat].sort_values("쇠퇴등급", ascending=False).head(5)
    print(f"\n[{cat}]")
    print(sub[["시군구명", "쇠퇴등급", "잠재력등급", "노후건축물비율"]].to_string(index=False))
