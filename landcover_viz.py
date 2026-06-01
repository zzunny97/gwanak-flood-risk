"""세분류 토지피복도 시각화 + 불투수면 비율 계산"""
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib as mpl

mpl.rcParams["font.family"] = "AppleGothic"
mpl.rcParams["axes.unicode_minus"] = False

lc = gpd.read_file("landcover_merged.geojson")
print(f"폴리곤 {len(lc):,}개, bbox={lc.total_bounds}")

# L1 색상 (환경부 표준)
L1_COLOR = {
    "100": "#e63946",  # 시가화·건조 = 빨강
    "200": "#f9c74f",  # 농업 = 노랑
    "300": "#2a9d8f",  # 산림 = 진녹
    "400": "#90be6d",  # 초지 = 연녹
    "500": "#577590",  # 습지
    "600": "#adb5bd",  # 나지 = 회색
    "700": "#4cc9f0",  # 수역 = 파랑
}
L1_NAME = {
    "100": "시가화·건조", "200": "농업", "300": "산림", "400": "초지",
    "500": "습지", "600": "나지", "700": "수역",
}

lc["L1_CODE_str"] = lc["L1_CODE"].astype(str)
lc["color"] = lc["L1_CODE_str"].map(L1_COLOR).fillna("#cccccc")

# 불투수면 마스크 (L1=100 시가화 또는 L1=600 나지의 일부)
lc["impervious"] = lc["L1_CODE_str"].isin(["100", "600"])

# 면적 계산 (m² → 투영좌표계가 ITRF2000 TM이라 미터 단위)
lc_metric = lc.to_crs("EPSG:5179")
lc["area_m2"] = lc_metric.geometry.area
total_area = lc["area_m2"].sum()
imperv_area = lc[lc["impervious"]]["area_m2"].sum()
print(f"\n전체 면적: {total_area/1e6:.2f} km²")
print(f"불투수면(L1=100+600): {imperv_area/1e6:.2f} km² ({imperv_area/total_area*100:.1f}%)")

# 시각화
fig, axes = plt.subplots(1, 2, figsize=(20, 10))

# 좌: L1 분류 색칠
ax = axes[0]
lc.plot(ax=ax, color=lc["color"], edgecolor="none")
ax.set_title(f"세분류 토지피복도 — L1 대분류 ({len(lc):,} 폴리곤)", fontsize=13)
# 범례
from matplotlib.patches import Patch
patches = [Patch(facecolor=c, label=L1_NAME[k]) for k, c in L1_COLOR.items()]
ax.legend(handles=patches, loc="lower right", fontsize=9, framealpha=0.95)
ax.set_xlabel("경도"); ax.set_ylabel("위도")

# 우: 불투수면만
ax = axes[1]
lc.plot(ax=ax, color="#eeeeee", edgecolor="none")
lc[lc["impervious"]].plot(ax=ax, color="#e63946", edgecolor="none")
ax.set_title(f"불투수면 추출 (L1=100+600, {lc['impervious'].sum():,} 폴리곤, {imperv_area/total_area*100:.1f}%)",
              fontsize=13)
ax.set_xlabel("경도"); ax.set_ylabel("위도")

plt.tight_layout()
plt.savefig("landcover_viz.png", dpi=130, bbox_inches="tight")
print("Saved: landcover_viz.png")
