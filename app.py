"""도시계획 기반 리스크 진단 대시보드 (도시재생종합정보체계 2024)"""
import re
import pandas as pd
import geopandas as gpd
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium

st.set_page_config(
    page_title="도시쇠퇴 리스크 진단",
    page_icon="🏙️",
    layout="wide",
)


@st.cache_data
def load_boundary():
    gdf = gpd.read_file("admdong.geojson")
    gdf["adm_cd"] = gdf["adm_cd"].astype(str).str.zfill(8)

    def normalize(adm_nm):
        parts = adm_nm.split(" ")
        sido, sigungu = parts[0], parts[1]
        m = re.match(r"(.+시)[가-힣]+구$", sigungu)
        if m:
            sigungu = m.group(1)
        return f"{sido} {sigungu}"

    gdf["시군구명"] = gdf["adm_nm"].apply(normalize)
    sigungu = gdf.dissolve(by="시군구명", as_index=False)[["시군구명", "geometry"]]
    return gdf, sigungu


@st.cache_data
def load_indicators():
    act = pd.read_csv("activate_sigungu.csv", encoding="cp949")
    dec = pd.read_csv("decline_sigungu.csv", encoding="cp949")
    pot = pd.read_csv("potential_sigungu.csv", encoding="cp949")
    act_emd = pd.read_csv("activate_emd.csv", encoding="utf-8-sig")
    act_emd["읍면동코드"] = act_emd["읍면동코드"].astype(str).str.zfill(8)
    return act, dec, pot, act_emd


def compute_quadrant(act, pot, year_act, year_pot, w_pop, w_biz, w_old, pot_cols):
    act_y = act[act["연도"] == year_act].copy()
    act_y["노후_q"] = pd.qcut(
        act_y["노후건축물비율"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]
    ).astype(float)
    weights = pd.Series({"최근인구변화": w_pop, "최근사업체변화": w_biz, "노후_q": w_old})
    weights = weights / weights.sum()
    act_y["쇠퇴등급"] = (act_y[weights.index] * weights).sum(axis=1)

    pot_y = pot[pot["연도"] == year_pot].copy()
    pot_y["잠재력등급"] = pot_y[pot_cols].mean(axis=1)

    df = act_y[["시군구명", "쇠퇴등급", "노후건축물비율", "최근인구변화", "최근사업체변화"]].merge(
        pot_y[["시군구명", "잠재력등급"]], on="시군구명", how="inner"
    )
    dec_med, pot_med = df["쇠퇴등급"].median(), df["잠재력등급"].median()

    def classify(row):
        hd = row["쇠퇴등급"] >= dec_med
        hp = row["잠재력등급"] >= pot_med
        if hd and hp: return "재생가능"
        if hd and not hp: return "고위험"
        if not hd and hp: return "유망"
        return "안정"

    df["분류"] = df.apply(classify, axis=1)
    return df, dec_med, pot_med


COLOR_MAP = {
    "고위험": "#d62728",
    "재생가능": "#ff7f0e",
    "유망": "#2ca02c",
    "안정": "#1f77b4",
}

# ========================================================================
st.title("🏙️ 도시계획 기반 리스크 진단 대시보드")
st.caption("출처: 국토교통부 도시재생종합정보체계 (시군구·읍면동 2024) · 행정동 GeoJSON: vuski/admdongkor")

with st.spinner("데이터 로딩..."):
    full_gdf, sigungu_gdf = load_boundary()
    act, dec, pot, act_emd = load_indicators()

# ===== 사이드바 =====
st.sidebar.header("⚙️ 분석 설정")
year_act = st.sidebar.selectbox("활성화지표 연도 (쇠퇴축)",
                                 sorted(act["연도"].unique(), reverse=True), index=0)
year_pot_options = [y for y in sorted(pot["연도"].unique(), reverse=True)
                    if pot[pot["연도"] == y].notna().mean().mean() > 0.7]
year_pot = st.sidebar.selectbox("잠재력지표 연도", year_pot_options,
                                 index=year_pot_options.index(2020) if 2020 in year_pot_options else 0)

st.sidebar.subheader("쇠퇴등급 가중치")
w_pop = st.sidebar.slider("최근 인구변화", 0.0, 2.0, 1.0, 0.1)
w_biz = st.sidebar.slider("최근 사업체변화", 0.0, 2.0, 1.0, 0.1)
w_old = st.sidebar.slider("노후건축물비율", 0.0, 2.0, 1.0, 0.1)

st.sidebar.subheader("잠재력 지표 구성")
all_pot_cols = ["1인당지역내총생산등급", "특허출원건수등급", "20세미만인구성장률등급",
                "1인당주민세등급", "재정자립도등급", "대졸인구비율등급", "여성종사자비율등급"]
pot_cols = st.sidebar.multiselect("잠재력 등급 평균에 포함할 지표",
                                    all_pot_cols, default=all_pot_cols[:5])
if not pot_cols:
    st.sidebar.error("잠재력 지표 최소 1개 선택")
    st.stop()

# ===== 계산 =====
df, dec_med, pot_med = compute_quadrant(act, pot, year_act, year_pot,
                                          w_pop, w_biz, w_old, pot_cols)
df["color"] = df["분류"].map(COLOR_MAP)
merged = sigungu_gdf.merge(df, on="시군구명", how="left")

# ===== 탭 =====
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 시군구 4분면", "🔍 읍면동 줌인", "📈 시계열 비교", "🗺️ 인터랙티브 지도"
])

# ===== 탭 1: 4분면 =====
with tab1:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("쇠퇴 vs 잠재력 산점도")
        fig = px.scatter(
            df, x="잠재력등급", y="쇠퇴등급", color="분류",
            color_discrete_map=COLOR_MAP, hover_name="시군구명",
            hover_data={"노후건축물비율": ":.1f"},
            height=500,
        )
        fig.add_vline(x=pot_med, line_dash="dash", line_color="grey")
        fig.add_hline(y=dec_med, line_dash="dash", line_color="grey")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("분류 지도")
        import matplotlib.pyplot as plt
        import matplotlib as mpl
        mpl.rcParams["font.family"] = "AppleGothic"
        mpl.rcParams["axes.unicode_minus"] = False

        fig2, ax = plt.subplots(figsize=(7, 7))
        m = merged.copy()
        m["color"] = m["color"].fillna("#dddddd")
        m.plot(ax=ax, color=m["color"], edgecolor="white", linewidth=0.3)
        ax.set_axis_off()
        st.pyplot(fig2)

    st.subheader("분류별 시군구 수")
    counts = df["분류"].value_counts().reindex(["고위험", "재생가능", "유망", "안정"]).fillna(0).astype(int)
    cols = st.columns(4)
    for i, (cat, n) in enumerate(counts.items()):
        cols[i].metric(cat, f"{n}개", help=f"{cat} 시군구 수")

    st.subheader("워스트 10 (쇠퇴등급 ↑)")
    worst = df.nlargest(10, "쇠퇴등급")[
        ["시군구명", "분류", "쇠퇴등급", "잠재력등급", "노후건축물비율", "최근인구변화", "최근사업체변화"]
    ]
    st.dataframe(worst, use_container_width=True, hide_index=True)

# ===== 탭 2: 읍면동 줌인 =====
with tab2:
    cities = {
        "서울특별시": (126.78, 127.18, 37.42, 37.70),
        "부산광역시": (128.85, 129.30, 35.05, 35.40),
        "대구광역시": (128.45, 128.78, 35.78, 36.05),
        "인천광역시": (126.40, 126.78, 37.38, 37.60),
        "광주광역시": (126.75, 127.00, 35.10, 35.27),
        "대전광역시": (127.30, 127.50, 36.25, 36.50),
    }
    city = st.selectbox("도시 선택", list(cities.keys()))
    bbox = cities[city]

    emd_year = st.selectbox("읍면동 데이터 연도",
                             sorted(act_emd["연도"].unique(), reverse=True), index=0)
    act_emd_y = act_emd[act_emd["연도"] == emd_year].copy()
    emd_merged = full_gdf.merge(act_emd_y, left_on="adm_cd", right_on="읍면동코드", how="left")
    city_data = emd_merged[emd_merged["adm_nm"].str.startswith(city)].copy()

    metric = st.radio("지표 선택",
                       ["최근인구변화", "최근사업체변화", "노후건축물비율"],
                       horizontal=True)
    cmap_map = {"최근인구변화": "Reds", "최근사업체변화": "Reds", "노후건축물비율": "Purples"}

    fig3, ax3 = plt.subplots(figsize=(10, 8))
    city_data.plot(column=metric, ax=ax3, cmap=cmap_map[metric], legend=True,
                    edgecolor="white", linewidth=0.3,
                    missing_kwds={"color": "lightgrey"})
    ax3.set_xlim(bbox[0], bbox[1])
    ax3.set_ylim(bbox[2], bbox[3])
    ax3.set_title(f"{city} — {metric} ({emd_year})", fontsize=13)
    ax3.set_axis_off()
    st.pyplot(fig3)

    st.subheader(f"{city} 워스트 10 — {metric}")
    asc = metric != "노후건축물비율"  # 인구/사업체는 등급 작을수록 좋음? 사실 등급↑=감소↑
    top_emd = city_data.nlargest(10, metric)[["adm_nm", metric, "노후건축물비율"]]
    st.dataframe(top_emd, use_container_width=True, hide_index=True)

# ===== 탭 3: 시계열 =====
with tab3:
    st.subheader("쇠퇴진단지표 시계열 변화 (2020 → 2024)")

    target = st.selectbox("지표 선택",
                           ["노후건축물비율", "노령화지수(주민등록인구통계)", "인구변화율(주민등록인구통계)"])

    dec_2020 = dec[dec["연도"] == 2020][["시군구명", target]].rename(columns={target: f"{target}_2020"})
    dec_2024 = dec[dec["연도"] == 2024][["시군구명", target]].rename(columns={target: f"{target}_2024"})
    ts = dec_2020.merge(dec_2024, on="시군구명", how="inner")
    ts["증가"] = ts[f"{target}_2024"] - ts[f"{target}_2020"]
    ts_geo = sigungu_gdf.merge(ts, on="시군구명", how="left")

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**2020**")
        fig_a, ax_a = plt.subplots(figsize=(6, 7))
        ts_geo.plot(column=f"{target}_2020", ax=ax_a, cmap="OrRd", legend=True,
                     edgecolor="white", linewidth=0.2,
                     missing_kwds={"color": "lightgrey"})
        ax_a.set_axis_off()
        st.pyplot(fig_a)

    with col_r:
        st.markdown("**2024**")
        fig_b, ax_b = plt.subplots(figsize=(6, 7))
        ts_geo.plot(column=f"{target}_2024", ax=ax_b, cmap="OrRd", legend=True,
                     edgecolor="white", linewidth=0.2,
                     missing_kwds={"color": "lightgrey"})
        ax_b.set_axis_off()
        st.pyplot(fig_b)

    st.markdown(f"**증가량 (2024 - 2020)** — 빨강일수록 악화 가속")
    fig_c, ax_c = plt.subplots(figsize=(10, 7))
    ts_geo.plot(column="증가", ax=ax_c, cmap="RdBu_r", legend=True,
                 edgecolor="white", linewidth=0.2,
                 missing_kwds={"color": "lightgrey"})
    ax_c.set_axis_off()
    st.pyplot(fig_c)

    st.subheader(f"악화 가속 워스트 10 — {target}")
    st.dataframe(ts.nlargest(10, "증가"), use_container_width=True, hide_index=True)

# ===== 탭 4: 인터랙티브 지도 =====
with tab4:
    st.subheader("시군구 클릭으로 상세 정보 보기")
    st.caption("지도에서 시군구를 클릭하면 모든 지표가 팝업으로 표시됩니다.")

    fmap = folium.Map(location=[36.5, 127.8], zoom_start=7, tiles="CartoDB positron")
    for _, row in merged.iterrows():
        if row.geometry is None or row.geometry.is_empty:
            continue
        color = row.get("color") if pd.notna(row.get("color")) else "#dddddd"
        popup_html = f"""
        <div style='font-size:12px; min-width:220px'>
          <b style='font-size:14px'>{row['시군구명']}</b><hr style='margin:4px 0'/>
          <b>분류:</b> {row.get('분류', 'N/A')}<br>
          <b>쇠퇴등급:</b> {row.get('쇠퇴등급', float('nan')):.2f}<br>
          <b>잠재력등급:</b> {row.get('잠재력등급', float('nan')):.2f}<br>
          <b>노후건축물비율:</b> {row.get('노후건축물비율', float('nan')):.1f}%<br>
          <b>최근 인구변화 등급:</b> {row.get('최근인구변화', float('nan')):.1f}<br>
          <b>최근 사업체변화 등급:</b> {row.get('최근사업체변화', float('nan')):.1f}<br>
        </div>
        """
        folium.GeoJson(
            row.geometry.__geo_interface__,
            style_function=lambda x, c=color: {
                "fillColor": c, "color": "white", "weight": 0.5, "fillOpacity": 0.7,
            },
            highlight_function=lambda x: {"weight": 2, "color": "black", "fillOpacity": 0.9},
            tooltip=row["시군구명"],
            popup=folium.Popup(popup_html, max_width=300),
        ).add_to(fmap)

    st_folium(fmap, width=1100, height=700, returned_objects=[])

st.sidebar.markdown("---")
st.sidebar.caption("쇠퇴등급↑ = 쇠퇴 심각 (1~10)\n잠재력등급↑ = 회복력 강함 (1~10)")
