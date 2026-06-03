"""관악구 침수 리스크 — 통계(RF) + 시각(GPT-4o-mini) 하이브리드 통합 대시보드"""
import json
from pathlib import Path
import pandas as pd
import geopandas as gpd
import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="홍수 리스크 — 하이브리드", page_icon="🌊", layout="wide")


@st.cache_data
def load_data():
    points = json.loads(Path("demo_points_full.json").read_text())
    cells = gpd.read_file("features_with_proba.geojson")
    with open("model_summary.json") as f:
        meta = json.load(f)
    return points, cells, meta


points, cells, meta = load_data()
labels = [f"#{i+1}  ({p['lat']:.4f}, {p['lon']:.4f})  ·  {p['hybrid']['total']:.1f}점"
          for i, p in enumerate(points)]

st.title("🌊 관악구 침수 리스크 — 하이브리드 진단")
st.caption(f"통계(RF AUC {meta['auc']:.3f}) × 시각(GPT-4o-mini) × LLM 진단 · 박루나 점수표 100점 만점")

# ===== 사이드바 — 지점 선택 =====
st.sidebar.header("📍 데모 지점")
idx = st.sidebar.radio("지점 선택", options=list(range(len(points))),
                        format_func=lambda i: labels[i], label_visibility="collapsed")
p = points[idx]
st.sidebar.markdown("---")
st.sidebar.markdown("**기본 정보**")
st.sidebar.markdown(f"- 좌표: ({p['lat']:.5f}, {p['lon']:.5f})")
st.sidebar.markdown(f"- 셀 ID: `{p['cell_id']}`")
st.sidebar.markdown(f"- 촬영일: {p.get('sv_date', 'N/A')}")
st.sidebar.markdown("---")
st.sidebar.markdown("**데이터 출처**")
st.sidebar.markdown("- 침수: 행안부 (2002~2018)\n- 토지피복: 환경부 (2025)\n- DEM: ESA Copernicus\n- 사진: Google Street View\n- Vision: OpenAI GPT-4o-mini")

# ===== 메인 상단 — 총점 큰 카드 =====
total = p["hybrid"]["total"]
risk_label = "🔴 고위험" if total >= 70 else "🟠 중위험" if total >= 50 else "🟢 저위험"
c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
c1.metric("🎯 하이브리드 위험 점수", f"{total:.1f} / 100", help="박루나 점수표 기준, 높을수록 위험")
c2.metric("RF 침수 확률", f"{p['flood_proba']:.2f}")
c3.metric("Vision 위험도", f"{p['vision']['risk_qualitative']}/10")
c4.metric("등급", risk_label)

st.divider()

# ===== 좌: 지도, 우: 4방향 사진 =====
col_map, col_imgs = st.columns([1, 1])

with col_map:
    st.subheader("📍 위치")
    m = folium.Map(location=[p["lat"], p["lon"]], zoom_start=15, tiles="CartoDB positron")
    # 관악구 침수 확률 ≥ 0.5 셀 표시 (배경)
    bg = cells[cells["flood_proba"] >= 0.5].copy()
    for _, row in bg.iterrows():
        if row.geometry is None or row.geometry.is_empty:
            continue
        prob = row["flood_proba"]
        color = "#9d0208" if prob > 0.7 else "#e63946" if prob > 0.5 else "#ff9966"
        folium.GeoJson(row.geometry.__geo_interface__, style_function=lambda x, c=color: {
            "fillColor": c, "color": c, "weight": 0, "fillOpacity": 0.4,
        }).add_to(m)
    # 8개 지점 핀
    for i, pt in enumerate(points, 1):
        is_selected = (i - 1) == idx
        folium.CircleMarker(
            [pt["lat"], pt["lon"]],
            radius=12 if is_selected else 7,
            color="#000" if is_selected else "#222",
            weight=3 if is_selected else 1.5,
            fill=True, fillColor="#ffd60a" if is_selected else "#4cc9f0",
            fillOpacity=1.0,
            tooltip=f"#{i} · {pt['hybrid']['total']:.0f}점",
        ).add_to(m)
    st_folium(m, width=500, height=500, returned_objects=[])

with col_imgs:
    st.subheader("📷 Street View 4방향")
    if p.get("images"):
        labels_dir = {0: "북 (N)", 90: "동 (E)", 180: "남 (S)", 270: "서 (W)"}
        # 2x2 그리드
        for r in [(0, 90), (180, 270)]:
            cols = st.columns(2)
            for j, h in enumerate(r):
                path = p["images"].get(str(h)) or p["images"].get(h)
                if path and Path(path).exists():
                    cols[j].image(path, caption=labels_dir[h], use_container_width=True)
    else:
        st.info("이미지 없음")

st.divider()

# ===== Vision LLM 시각 분석 + Hybrid 점수 breakdown =====
col_v, col_h = st.columns(2)

with col_v:
    st.subheader("👁️ Vision LLM 시각 분석 (GPT-4o-mini)")
    v = p["vision"]
    vt = pd.DataFrame({
        "항목": ["불투수면", "배수구 상태", "평지 정도", "식생 피복", "보도 상태", "종합 위험도"],
        "값": [f"{v['impervious_pct']}%",
                f"{v['drainage_score']}/10",
                f"{v['flatness_score']}/10",
                f"{v['vegetation_pct']}%",
                f"{v['sidewalk_score']}/10",
                f"{v['risk_qualitative']}/10"],
    })
    st.dataframe(vt, hide_index=True, use_container_width=True)
    st.caption(f"📝 **관찰**: {v.get('notes')}")

with col_h:
    st.subheader("🧮 하이브리드 점수 breakdown")
    comps = p["hybrid"]["components"]
    ht = pd.DataFrame({
        "박루나 점수표 항목": list(comps.keys()),
        "획득 점수": list(comps.values()),
        "비율": [f"{v / float(k.split('(')[-1].rstrip(')')) * 100:.0f}%"
                 for k, v in comps.items()],
    })
    st.dataframe(ht, hide_index=True, use_container_width=True)
    st.caption(f"**총점: {total:.1f}/100점** ({risk_label})")

st.divider()

# ===== LLM 진단 보고서 =====
st.subheader("📋 종합 진단 + 정책 권고 (GPT-4o-mini 자동 생성)")
report = p.get("report")
if report:
    st.markdown(f"**진단**: {report['diagnosis']}")
    st.markdown("**정책 권고**:")
    for r in report["policy"]:
        st.markdown(f"- {r}")
else:
    st.warning("진단 보고서 없음 (`report_gen.py` 실행 필요)")

# ===== 전체 비교 (사이드바 아래 expander) =====
with st.expander("📊 8 데모 지점 전체 비교"):
    comparison = pd.DataFrame([{
        "지점": f"#{i+1}",
        "위경도": f"({pt['lat']:.4f}, {pt['lon']:.4f})",
        "총점": pt["hybrid"]["total"],
        "RF확률": pt["flood_proba"],
        "Vision위험": pt["vision"]["risk_qualitative"],
        "불투수%": pt["vision"]["impervious_pct"],
        "촬영일": pt.get("sv_date", "-"),
    } for i, pt in enumerate(points)])
    st.dataframe(comparison.style.background_gradient(subset=["총점"], cmap="OrRd"),
                  hide_index=True, use_container_width=True)
