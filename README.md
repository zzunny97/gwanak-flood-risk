# 도시 홍수 리스크 평가 — 기말 프로젝트

학교 기말 프로젝트 (도시 분야). **관악구**를 데모 지역으로, 통계 기반 ML 모델 + 멀티모달 Vision AI 하이브리드로 도시 홍수 리스크를 평가한다.

## 📅 일정

<!-- DDAY:START -->
| 마일스톤 | 날짜 | D-day |
|---|---|---|
| 중간 발표 | 2026-06-04 | D+51 (지남) |
| 기말 발표 | 2026-06-18 | D+37 (지남) |

_마지막 자동 갱신: 2026-07-25 KST_
<!-- DDAY:END -->

*위 D-day는 `.github/workflows/update-dday.yml`이 매일 KST 00:05에 자동 갱신.*

## 🎯 프로젝트 정의

**문제**: 어느 지역이 침수에 취약한가, 그리고 왜 그런가?

**접근**:
1. **통계 모델 (RF + SHAP)** — 침수흔적도(label) + 토지피복(불투수면) + DEM(경사도) + 하수관거(인프라)로 침수 발생 확률 학습. 가중치를 임의로 정하지 않고 데이터에서 학습된 SHAP feature importance로 산출.
2. **멀티모달 Vision AI** — Google Street View 이미지를 GPT-4o/Claude Vision에 넣어 통계 데이터에 없는 시각 변수(배수구 상태, 식생 피복, 보도 노후도) 추출.
3. **하이브리드 점수** — 통계 점수 + 시각 점수 결합 → 위치별 100점 만점 침수 리스크.

**스코프**: 관악구 (1,002 침수 폴리곤, 신림동 2022 반지하 사건 사례 포함).

---

## 📦 데이터 카탈로그

### A. 메인 (홍수 리스크 분석용)

| 데이터 | 출처 | 단위 | 연도 | 파일 | 상태 |
|---|---|---|---|---|---|
| **침수흔적도** | 행안부 safetydata.go.kr API (DSSP-IF-00117) | 폴리곤 (전국 38,003) | 2002~2018 | `flood_all.json`, `flood_all.geojson` (생성 중) | ✅ |
| **침수흔적도 — 관악구** | 위에서 필터링 | 폴리곤 (1,002) | — | `flood_gwanak.geojson` (생성 중) | 🔄 |
| **세분류 토지피복지도 — 관악구** | EGIS / aid.mcee.go.kr (사업종류 "세분류 2025 전국") | 1m 폴리곤 (104,371) | 2025 | `landcover_gwanak.geojson` | ✅ |
| **DEM (고도/경사도)** | Copernicus DEM GLO-30 (AWS S3 public) | 30m 픽셀 (3600×3600) | 최신 | `dem/seoul_dem.tif`, `dem/slope_gangnam.npz` | ✅ (강남) / 🔜 (관악) |
| **하수관거** | 서울 열린데이터광장 | 자치구별 연단위 (관악구만) | 2006~2023 | `sewer.csv` | ✅ |

### B. 서브 (이전 도시쇠퇴 4분면 분석 — Phase 1)

| 데이터 | 출처 | 단위 | 파일 |
|---|---|---|---|
| 도시쇠퇴 진단지표 | 국토부 city.go.kr | 시군구 (229) | `decline_sigungu.csv` (85 컬럼) |
| 도시 활성화 지표 | 국토부 city.go.kr | 시군구 (229) | `activate_sigungu.csv` (11 컬럼) |
| 잠재력 지표 | 국토부 city.go.kr | 시군구 (229) | `potential_sigungu.csv` (41 컬럼) |
| 활성화 — 읍면동 | 국토부 city.go.kr | 읍면동 (32,051) | `activate_emd.csv` |
| 쇠퇴 — 읍면동 | 국토부 city.go.kr | 읍면동 (17MB) | `decline_emd.csv` |
| 쇠퇴 — 집계구 | 국토부 city.go.kr | 집계구 (458MB) | `decline_jip.csv` (사용 안 함, 너무 큼) |
| 행정동 경계 | GitHub vuski/admdongkor | 3,558 행정동 | `admdong.geojson` (33MB) |

### C. 추가 받아야 할 (선택)

- **Google Street View Static API** — 기말용. Cloud Console에서 신용카드 등록, $200/월 무료
- **OpenAI / Claude Vision API 키** — 기말용
- **읍면동·동 단위 하수관거** — 가능하면 (현재는 자치구 단위만)

---

## 🛠️ 스크립트 — 무엇이 어떤 거 하는지

### 데이터 수집 (`fetch_*.py`)
| 파일 | 역할 |
|---|---|
| `fetch_curl.py` ⭐ | 침수흔적도 38k cURL 페이지네이션 (subprocess) |
| `fetch_flood.py` | 침수흔적도 1000건 표본 (deprecated, 초기 테스트용) |
| `fetch_all_flood.py` | requests 기반 (deprecated, Python 3.13에서 timeout) |

### 데이터 가공
| 파일 | 역할 |
|---|---|
| `landcover_merge.py` | 강남권 15개 도엽 → 통합 (`landcover_merged.geojson`) |
| `landcover_gwanak.py` ⭐ | 관악구 11개 도엽 → 통합 (`landcover_gwanak.geojson`) |
| `build_flood_geojson.py` ⭐ | 38k JSON → GeoJSON + 관악구/강남 필터 분리본 |
| `dem_analysis.py` | DEM crop + 경사도 계산 |

### 분석/시각화 — Phase 1 (도시쇠퇴, 사용 안 함)
| 파일 | 역할 |
|---|---|
| `quadrant.py` | 시군구 4분면 분류 (쇠퇴 × 잠재력) |
| `emd_zoom.py` | 도시별 읍면동 핫스팟 |
| `timeseries.py` | 2020 vs 2024 시계열 비교 |
| `interactive_map.py` | folium 인터랙티브 지도 (HTML) |
| `build_map.py`, `check_data.py` | 초기 탐색 |
| `app.py` | Streamlit 통합 대시보드 (4탭) |

### 분석/시각화 — Phase 2 (홍수, 메인)
| 파일 | 역할 |
|---|---|
| `analyze_flood.py` | 침수흔적도 EDA |
| `landcover_viz.py` | 토지피복도 + 불투수면 시각화 |
| `dem_merge.py` | DEM 두 타일 머지 |
| `build_features.py` ⭐ | 100m 그리드 + feature 결합 (label/feature 생성) |
| `train_rf.py` ⭐ | RF 학습 + SHAP + 시각화 4종 |
| `app_flood.py` ⭐ | 침수 리스크 Streamlit 대시보드 (4탭) |
| (기말) `vision_score.py` | Street View + Vision LLM — 미작성 |

---

## ✅ 진척 — 어디까지 했나

### 완료
- [x] 침수흔적도 38,003건 전체 다운로드 (`flood_all.json`, 47MB) + 관악구/강남 필터 GeoJSON
- [x] 관악구 세분류 토지피복도 11개 도엽 → 1m 폴리곤 104k개 통합
- [x] Copernicus DEM 30m 두 타일(N37E126+N37E127) 머지 → 관악구 커버
- [x] 관악구 하수관거 시계열 (2006~2023)
- [x] Phase 1: 도시쇠퇴 4분면 Streamlit 대시보드 (`app.py`)
- [x] **100m 그리드 + feature 결합** (9,324 셀, 침수 셀 382) → `features_gwanak.csv/geojson`
- [x] **RF 베이스라인 학습 → AUC 0.922** + SHAP feature importance
- [x] **시각화 4종** (`rf_proba_map.png`, `shap_summary.png`, `feature_importance.png`, `rf_metrics.png`)
- [x] **Streamlit 침수 대시보드** (`app_flood.py`) — 4탭, 임계값 슬라이더
- [x] 결과 요약 markdown (`RESULT_BASELINE.md`)

### 기말발표 (6/18) 풀스택 완성
- [x] Kakao Geocoding API (주소 → 좌표) — `geocode.py`
- [x] Google Street View Static API (좌표 → 4방향 사진) — `streetview.py`
- [x] 데모 지점 8곳 자동 추출 + 32장 사전 캐싱 — `demo_points.py`
- [x] OpenAI GPT-4o-mini Vision (사진 → 6요소 점수) — `vision_score.py`
- [x] 박루나 점수표 100점 만점 hybrid score — `hybrid_score.py`
- [x] LLM 자연어 진단 + 정책 권고 자동 생성 — `report_gen.py`
- [x] 통합 Streamlit 대시보드 — `app_hybrid.py`
- [ ] (옵션) Spatial CV로 더 견고한 성능 평가
- [ ] 발표 자료 (PPT)

---

## 🚀 실행

### 환경 세팅
```bash
# Python 환경
uv venv && source .venv/bin/activate
uv pip install geopandas matplotlib streamlit folium streamlit-folium plotly \
                rasterio rioxarray shap scikit-learn pyogrio mapclassify

# 행안부 침수흔적도 API 키 (https://www.safetydata.go.kr)
export SAFETY_DATA_KEY="여기에_본인_키"
```

### 큰 데이터 재생성 (gitignore되어 있음)
```bash
# 1) 침수흔적도 (행안부 API, 1~2분, totalCount 38,003건)
python fetch_curl.py
python build_flood_geojson.py

# 2) 토지피복도 (EGIS aid.mcee.go.kr 회원가입 + 관악구 신청 → ~/Downloads 에 zip)
python landcover_gwanak.py

# 3) DEM (Copernicus AWS S3, 자동 다운로드)
python dem_merge.py

# 4) 행정동 경계 (Phase 1용, 선택)
curl -sL -o admdong.geojson \
  "https://raw.githubusercontent.com/vuski/admdongkor/master/ver20260401/HangJeongDong_ver20260401.geojson"

# 5) 메인 파이프라인
python build_features.py    # 9,324 셀 + feature
python train_rf.py          # RF + SHAP + 시각화 4종
```

### Phase 2 침수 리스크 대시보드 (메인)
```bash
cd ~/gis-viz/korea
streamlit run app_flood.py
# → http://localhost:8501
```

### Phase 1 도시쇠퇴 대시보드 (서브)
```bash
streamlit run app.py
```

### Phase 2 데이터 재생성
```bash
# 침수흔적도 (이미 받음. 다시 받을 일 거의 없음)
python fetch_curl.py               # → flood_pages/, flood_all.json

# 침수 GeoJSON 변환
python build_flood_geojson.py     # → flood_all.geojson, flood_gwanak.geojson

# 토지피복도 (관악구)
python landcover_gwanak.py        # → landcover_gwanak.geojson

# DEM 경사도
python dem_analysis.py            # → dem/slope_gangnam.npz, dem_slope.png
```

---

## ⚠️ 알려진 제약

1. **침수흔적도 연도 한계** — 2002~2018만 있음, 최근 2022 침수 없음 → "신림동 2022 반지하 사건" 스토리는 발표용 narrative로만 활용
2. **하수관거 단위** — 자치구 단위만 (관악구 1개 값). 동·블록 단위 차이를 feature로 못 씀 → RF 모델에서는 가중치 0 또는 정성 분석으로만
3. **API 안정성** — `safetydata.go.kr`은 Python `requests`로 산발적 timeout. **cURL subprocess가 안정적** (`fetch_curl.py` 참고)
4. **연도 불일치** — 데이터별 연도 다름 (침수 2002~2018, 토지피복 2025, DEM 최근). ML 학습엔 무방하지만 발표 시 한계점 명시
5. **로컬 환경 제약** — CNN/ViT 직접 학습 불가능. Vision은 API 호출(GPT-4o/Claude)로 우회

---

## 📂 디렉토리 구조

```
~/gis-viz/                         # venv 루트
├── .venv/                         # Python 환경
└── korea/                         # 프로젝트 루트
    ├── README.md                  # 이 파일
    │
    ├── app.py                     # Phase 1 Streamlit 앱
    │
    ├── # ─── 데이터 (원본) ─────
    ├── flood_all.json             # 침수흔적 38k (raw)
    ├── flood_pages/               # 페이지별 캐시 (재실행 대비)
    ├── sewer.csv                  # 하수관거 (관악구)
    ├── landcover_gwanak/          # 관악 토지피복 zip 풀린 것
    ├── landcover/                 # 강남 토지피복 zip 풀린 것
    ├── dem/                       # DEM tif + npz
    ├── decline_*.csv              # 도시쇠퇴 (Phase 1)
    ├── activate_*.csv, potential_*.csv
    ├── admdong.geojson            # 행정동 경계
    │
    ├── # ─── 데이터 (가공) ─────
    ├── flood_all.geojson          # 38k 침수 (생성 중)
    ├── flood_gwanak.geojson       # 관악구만
    ├── flood_gangnam.geojson      # 강남권만
    ├── landcover_merged.geojson   # 강남 토지피복
    ├── landcover_gwanak.geojson   # 관악 토지피복 ⭐
    │
    ├── # ─── 스크립트 ─────
    ├── fetch_curl.py              # 침수 API ⭐
    ├── build_flood_geojson.py     # GeoJSON 빌드 ⭐
    ├── landcover_gwanak.py        # 관악 토지피복 빌드 ⭐
    ├── dem_analysis.py            # 경사도
    ├── analyze_flood.py           # 침수 EDA
    ├── landcover_viz.py           # 토지피복 시각화
    ├── quadrant.py, emd_zoom.py, timeseries.py, interactive_map.py  # Phase 1
    │
    └── # ─── 산출물 (PNG) ─────
        ├── flood_eda.png
        ├── landcover_viz.png
        ├── dem_slope.png
        ├── quadrant_map.png
        ├── emd_zoom.png
        ├── timeseries.png
        ├── decline_map.png
        └── interactive_map.html
```

---

_마지막 업데이트: 2026-05-28_
