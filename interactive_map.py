import pandas as pd
import geopandas as gpd
import folium
import re

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

# 4분면 분류 결과 재계산 (quadrant.py 로직 압축)
act = pd.read_csv("activate_sigungu.csv", encoding="cp949")
act24 = act[act["연도"]==2024].copy()
act24["노후_q"] = pd.qcut(act24["노후건축물비율"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(float)
act24["쇠퇴등급"] = act24[["최근인구변화","최근사업체변화","노후_q"]].mean(axis=1)

pot = pd.read_csv("potential_sigungu.csv", encoding="cp949")
pot20 = pot[pot["연도"]==2020].copy()
pot_cols = ["1인당지역내총생산등급","특허출원건수등급","20세미만인구성장률등급","1인당주민세등급","재정자립도등급"]
pot20["잠재력등급"] = pot20[pot_cols].mean(axis=1)

df = act24[["시군구명","쇠퇴등급","노후건축물비율","최근인구변화","최근사업체변화"]].merge(
    pot20[["시군구명","잠재력등급"]], on="시군구명", how="inner")
dec_med, pot_med = df["쇠퇴등급"].median(), df["잠재력등급"].median()
def classify(row):
    hd, hp = row["쇠퇴등급"]>=dec_med, row["잠재력등급"]>=pot_med
    if hd and hp: return "재생가능"
    if hd and not hp: return "고위험"
    if not hd and hp: return "유망"
    return "안정"
df["분류"] = df.apply(classify, axis=1)
color_map = {"고위험":"#d62728","재생가능":"#ff7f0e","유망":"#2ca02c","안정":"#1f77b4"}
df["color"] = df["분류"].map(color_map)

merged = sigungu.merge(df, on="시군구명", how="left")
merged["color"] = merged["color"].fillna("#dddddd")

# folium 지도
m = folium.Map(location=[36.5, 127.8], zoom_start=7, tiles="CartoDB positron")

for _, row in merged.iterrows():
    if row.geometry is None or row.geometry.is_empty:
        continue
    popup_html = f"""
    <div style='font-family: AppleSDGothicNeo, sans-serif; font-size:12px; min-width:200px'>
      <b style='font-size:14px'>{row['시군구명']}</b><br>
      <hr style='margin:4px 0'/>
      <b>분류:</b> {row.get('분류', '데이터없음')}<br>
      <b>쇠퇴등급:</b> {row.get('쇠퇴등급', float('nan')):.2f}<br>
      <b>잠재력등급:</b> {row.get('잠재력등급', float('nan')):.2f}<br>
      <b>노후건축물비율:</b> {row.get('노후건축물비율', float('nan')):.1f}%<br>
      <b>최근 인구변화 등급:</b> {row.get('최근인구변화', float('nan')):.1f}<br>
      <b>최근 사업체변화 등급:</b> {row.get('최근사업체변화', float('nan')):.1f}<br>
    </div>
    """
    folium.GeoJson(
        row.geometry.__geo_interface__,
        style_function=lambda x, color=row["color"]: {
            "fillColor": color, "color": "white",
            "weight": 0.5, "fillOpacity": 0.7,
        },
        highlight_function=lambda x: {"weight": 2, "color": "black", "fillOpacity": 0.9},
        tooltip=row["시군구명"],
        popup=folium.Popup(popup_html, max_width=300),
    ).add_to(m)

# 범례
legend_html = """
<div style='position: fixed; bottom: 30px; left: 30px; z-index: 9999;
            background: white; padding: 10px 14px; border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2); font-family: sans-serif; font-size:13px'>
  <b>도시쇠퇴 4분면 분류</b><br>
  <span style='background:#d62728; padding:2px 10px; color:white'>&nbsp;</span> 고위험 (쇠퇴↑ 잠재력↓)<br>
  <span style='background:#ff7f0e; padding:2px 10px; color:white'>&nbsp;</span> 재생가능 (쇠퇴↑ 잠재력↑)<br>
  <span style='background:#2ca02c; padding:2px 10px; color:white'>&nbsp;</span> 유망 (쇠퇴↓ 잠재력↑)<br>
  <span style='background:#1f77b4; padding:2px 10px; color:white'>&nbsp;</span> 안정 (쇠퇴↓ 잠재력↓)<br>
  <span style='background:#dddddd; padding:2px 10px'>&nbsp;</span> 데이터 없음
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

m.save("interactive_map.html")
print("Saved: interactive_map.html")
