import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib as mpl

# 한글 폰트 설정 (macOS)
mpl.rcParams["font.family"] = "AppleGothic"
mpl.rcParams["axes.unicode_minus"] = False

print("Loading admdong geojson...")
gdf = gpd.read_file("admdong.geojson")
print(f"  행정동 {len(gdf)}개, CRS={gdf.crs}")

# 시군구명 추출 (광역시 자치구는 "서울특별시 종로구", 일반시 행정구는 "고양시덕양구"→"고양시"로)
import re
def normalize_sigungu(adm_nm: str) -> str:
    parts = adm_nm.split(" ")
    sido, sigungu = parts[0], parts[1]
    # 일반시 행정구 패턴: "○○시xx구" → "○○시"
    m = re.match(r"(.+시)[가-힣]+구$", sigungu)
    if m:
        sigungu = m.group(1)
    return f"{sido} {sigungu}"

gdf["시군구명"] = gdf["adm_nm"].apply(normalize_sigungu)

print("Dissolving to 시군구...")
sigungu = gdf.dissolve(by="시군구명", as_index=False)
print(f"  시군구 {len(sigungu)}개")

print("Loading 쇠퇴진단지표 (2024)...")
dec = pd.read_csv("decline_sigungu.csv", encoding="cp949")
dec_2024 = dec[dec["연도"] == 2024].copy()
print(f"  2024년 시군구 {len(dec_2024)}개")

# 종합 쇠퇴 점수 = 등급 컬럼 평균 (높을수록 쇠퇴 심각)
grade_cols = [c for c in dec_2024.columns if c.endswith("등급")]
print(f"  등급 컬럼 {len(grade_cols)}개로 종합점수 계산")
dec_2024["쇠퇴종합점수"] = dec_2024[grade_cols].mean(axis=1)

# 시군구 boundary와 조인 (시군구명으로)
merged = sigungu.merge(dec_2024, on="시군구명", how="left")
print(f"  조인 결과: 매칭 {merged['쇠퇴종합점수'].notna().sum()} / 전체 {len(merged)}")
unmatched = merged[merged["쇠퇴종합점수"].isna()]["시군구명"].tolist()
if unmatched:
    print(f"  미매칭 ({len(unmatched)}): {unmatched[:10]}")

# 시각화: 2x2 패널
fig, axes = plt.subplots(2, 2, figsize=(18, 18))

panels = [
    ("쇠퇴종합점수", "OrRd", "도시 쇠퇴 종합점수 (높을수록 쇠퇴 심각)", axes[0, 0]),
    ("노후건축물비율", "Purples", "노후건축물비율 (%)", axes[0, 1]),
    ("인구변화율(주민등록인구통계)", "RdBu", "인구변화율 (음수=감소)", axes[1, 0]),
    ("공가율", "YlOrBr", "공가율 (빈집 비율 %)", axes[1, 1]),
]

for col, cmap, title, ax in panels:
    if col not in merged.columns:
        ax.set_title(f"{title}\n(컬럼 없음)")
        ax.axis("off")
        continue
    merged.plot(
        column=col, ax=ax, cmap=cmap, legend=True,
        edgecolor="white", linewidth=0.2,
        missing_kwds={"color": "lightgrey", "label": "데이터 없음"},
        legend_kwds={"shrink": 0.6},
    )
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_axis_off()

plt.suptitle("도시계획 기반 리스크 시각화 — 국토부 쇠퇴진단지표 2024",
             fontsize=17, fontweight="bold", y=0.995)
plt.tight_layout()
plt.savefig("decline_map.png", dpi=140, bbox_inches="tight")
print("\nSaved: decline_map.png")

# 워스트 10
print("\n=== 쇠퇴종합점수 워스트 10 시군구 ===")
worst = merged.nlargest(10, "쇠퇴종합점수")[["시군구명", "쇠퇴종합점수", "노후건축물비율", "공가율", "인구변화율(주민등록인구통계)"]]
print(worst.to_string(index=False))
