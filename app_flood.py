"""관악구 침수 리스크 인터랙티브 대시보드"""
import json
import pandas as pd
import geopandas as gpd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="관악구 침수 리스크", page_icon="🌊", layout="wide")


@st.cache_data
def load_data():
    gdf = gpd.read_file("features_with_proba.geojson")
    with open("model_summary.json") as f:
        meta = json.load(f)
    return gdf, meta


gdf, meta = load_data()

st.title("🌊 관악구 침수 리스크 진단")
st.caption(f"AUC {meta['auc']:.3f} · {meta['n_cells']:,} 셀 · 침수 셀 {meta['n_positive']} ({meta['positive_ratio']*100:.1f}%) · 6 features · RandomForest")

# ===== Sidebar =====
st.sidebar.header("⚙️ 표시 옵션")
threshold = st.sidebar.slider("침수 확률 임계값", 0.0, 1.0, 0.5, 0.05,
                              help="이 값 이상의 셀을 '침수 예측'으로 표시")
show_actual = st.sidebar.checkbox("실제 침수 셀 표시", True)
opacity = st.sidebar.slider("지도 투명도", 0.3, 1.0, 0.75, 0.05)

st.sidebar.markdown("---")
st.sidebar.subheader("📌 데이터 출처")
st.sidebar.markdown("""
- **침수흔적도** (2002~2018) — 행안부
- **토지피복도 세분류** (2025) — 환경부
- **DEM 30m** — ESA Copernicus
- **하수관거** (2006~2023) — 서울 열린데이터광장
""")

# ===== Tabs =====
tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ 침수 확률 지도", "📊 모델 성능", "🧠 Feature Importance / SHAP", "📋 데이터"
])

# ----- Tab 1: 지도 -----
with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("관악구 침수 확률 heatmap")
        # folium 지도
        center_lat = gdf.geometry.centroid.y.mean()
        center_lon = gdf.geometry.centroid.x.mean()
        m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="CartoDB positron")

        # 컬러: 확률에 따라
        def color_for(p):
            # YlOrRd
            if p < 0.1: return "#fffaf0"
            if p < 0.3: return "#ffd699"
            if p < 0.5: return "#ff9966"
            if p < 0.7: return "#e63946"
            return "#9d0208"

        # 침수 확률이 threshold 이상인 셀만 표시 (성능)
        display = gdf[gdf["flood_proba"] >= max(threshold - 0.2, 0.05)].copy()
        st.caption(f"표시: {len(display):,} / {len(gdf):,} 셀 (proba ≥ {max(threshold-0.2, 0.05):.2f})")

        for _, row in display.iterrows():
            color = color_for(row["flood_proba"])
            folium.GeoJson(
                row.geometry.__geo_interface__,
                style_function=lambda x, c=color: {
                    "fillColor": c, "color": c, "weight": 0,
                    "fillOpacity": opacity,
                },
                tooltip=(f"proba={row['flood_proba']:.2f}, "
                          f"불투수={row['impervious_ratio']*100:.0f}%, "
                          f"고도={row['elev_mean']:.0f}m, "
                          f"경사={row['slope_mean']:.1f}°"),
            ).add_to(m)

        if show_actual:
            actual = gdf[gdf["flood_label"] == 1]
            for _, row in actual.iterrows():
                folium.GeoJson(
                    row.geometry.__geo_interface__,
                    style_function=lambda x: {
                        "fillColor": "none", "color": "#1f77b4",
                        "weight": 1.5, "fillOpacity": 0,
                    },
                ).add_to(m)

        st_folium(m, width=900, height=600, returned_objects=[])

    with col2:
        st.metric("AUC", f"{meta['auc']:.3f}")
        st.metric("침수 셀 수", f"{meta['n_positive']:,}")
        st.metric("전체 셀 수", f"{meta['n_cells']:,}")
        pred_count = int((gdf["flood_proba"] >= threshold).sum())
        st.metric(f"예측 침수 (≥{threshold:.2f})", f"{pred_count:,}")

        st.markdown("**범례**")
        st.markdown("""
        - 🟥 진한 빨강 — 침수 위험 高 (proba≥0.7)
        - 🟧 주황 — 중간 (0.5)
        - 🟨 연한 — 낮음
        - 🔵 파란 테두리 — 실제 침수 발생 셀
        """)


# ----- Tab 2: 모델 성능 -----
with tab2:
    st.subheader("모델 성능 메트릭")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("AUC (ROC)", f"{meta['auc']:.3f}")
    c2.metric("Average Precision", f"{meta['average_precision']:.3f}")
    c3.metric("Test 셀 수", f"{meta['test_size']:,}")
    c4.metric("Positive 비율", f"{meta['positive_ratio']*100:.1f}%")

    st.image("rf_metrics.png", caption="ROC Curve · Precision-Recall · 혼동행렬 (threshold=0.5)")

    st.subheader("실제 vs 예측 셀 분포")
    cm = meta["confusion_matrix"]
    df_cm = pd.DataFrame(cm, index=["실제 비침수", "실제 침수"], columns=["예측 비침수", "예측 침수"])
    st.dataframe(df_cm, use_container_width=False)
    st.markdown(f"""
    - **Recall (침수 탐지율)**: {cm[1][1]} / {cm[1][0]+cm[1][1]} = **{cm[1][1]/(cm[1][0]+cm[1][1])*100:.1f}%**
    - **Precision (침수 정밀도)**: {cm[1][1]} / {cm[0][1]+cm[1][1]} = **{cm[1][1]/(cm[0][1]+cm[1][1])*100:.1f}%**
    - 임계값 0.5 기준. 사이드바에서 임계값 조절하면 trade-off 가능
    """)


# ----- Tab 3: Feature Importance -----
with tab3:
    st.subheader("Feature Importance — 데이터에서 학습된 가중치")
    st.markdown("""
    > 박루나 점수표는 *"불투수면 25점, 배수구 20점, 경사도 20점..."* 처럼 **임의 가중치**였음.
    > 우리 모델은 **침수흔적 1,002건을 학습**해서 **각 변수의 실제 기여도**를 자동 산출.
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Gini Importance**")
        gini = pd.Series(meta["importance_gini"]).sort_values(ascending=True)
        fig = go.Figure(go.Bar(x=gini.values, y=gini.index, orientation="h",
                                marker_color="#2a9d8f"))
        fig.update_layout(height=400, margin=dict(l=120))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("**SHAP Importance (|SHAP| mean)**")
        shap_imp = pd.Series(meta["importance_shap"]).sort_values(ascending=True)
        fig = go.Figure(go.Bar(x=shap_imp.values, y=shap_imp.index, orientation="h",
                                marker_color="#e76f51"))
        fig.update_layout(height=400, margin=dict(l=120))
        st.plotly_chart(fig, use_container_width=True)

    st.image("shap_summary.png", caption="SHAP Summary — 각 셀별 feature가 침수 확률에 미치는 영향")


# ----- Tab 4: 데이터 -----
with tab4:
    st.subheader("Feature 분포")
    feat_cols = ["impervious_ratio", "veg_ratio", "elev_mean", "slope_mean"]
    feat_labels = ["불투수면 비율", "식생 비율", "평균 고도 (m)", "평균 경사도 (°)"]

    cols = st.columns(2)
    for i, (col, label) in enumerate(zip(feat_cols, feat_labels)):
        with cols[i % 2]:
            fig = px.histogram(gdf, x=col, color="flood_label",
                                color_discrete_map={0: "#cccccc", 1: "#d62728"},
                                marginal="box", nbins=40,
                                labels={col: label, "flood_label": "침수"})
            fig.update_layout(height=300, margin=dict(t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("워스트 20 셀 (침수 확률 ↑)")
    worst = gdf.nlargest(20, "flood_proba")[[
        "cell_id", "flood_proba", "flood_label",
        "impervious_ratio", "veg_ratio", "elev_mean", "slope_mean"
    ]]
    st.dataframe(worst, use_container_width=True, hide_index=True)
