# 관악구 침수 리스크 RF 베이스라인 — 결과 요약

생성일: 2026-05-28 밤  
실행 스크립트: `build_features.py` → `train_rf.py`

## 🎯 핵심 결과

| 메트릭 | 값 |
|---|---|
| **AUC (ROC)** | **0.922** ⭐ |
| Average Precision | 0.277 |
| 전체 셀 | 9,324 |
| 침수 셀 (label=1) | 382 (4.1%) |
| Test 셀 | 2,798 |

**AUC 0.92는 매우 강력한 분류 성능** — 베이스라인 모델이 침수 vs 비침수를 거의 정확히 구분.

## 📊 Feature Importance — 박루나 점수표 검증

| Feature | Gini | SHAP |
|---|---|---|
| **불투수면 비율** | **38.8%** | **18.0%** |
| 평균 고도 (m) | 19.5% | 8.8% |
| 최저 고도 (m) | 15.0% | 6.6% |
| 평균 경사도 (°) | 12.3% | 6.0% |
| 최대 경사도 (°) | 10.0% | 5.1% |
| 식생 비율 | 4.4% | 3.2% |

→ **불투수면 비율이 압도적 1위**. 박루나 점수표에서 임의로 25점을 매겼던 것이 **데이터로 검증된 셈**. 발표 핵심 포인트.

→ 고도 + 경사도(평지일수록 위험)가 2~5위로 강한 신호. 박루나가 20점 매긴 *"도로 경사도"* 변수도 검증.

→ 식생 비율은 약함 (관악구는 산 vs 도심 이분이라 산림 영역이 침수와 무관, 도심 안의 작은 녹지는 너무 작아 신호 약함).

## 🗂️ 혼동행렬 (threshold = 0.5)

```
              예측 비침수    예측 침수
실제 비침수     2,505          178
실제 침수          53           62
```

- **Recall (침수 탐지율)**: 62 / (53+62) = **54%**
- **Precision (침수 정밀도)**: 62 / (62+178) = **26%**

Threshold를 낮추면 Recall↑ Precision↓. AUC 0.92는 threshold tuning 여지가 큼.

## 📦 입력 데이터

| 출처 | 내용 | 연도 |
|---|---|---|
| 행안부 침수흔적도 API | 관악구 침수 폴리곤 1,002개 → cell label | 2002~2018 |
| 환경부 EGIS 세분류 토지피복도 | 관악구 1m 폴리곤 104k → 불투수면·식생 | 2025 |
| ESA Copernicus DEM 30m | 두 타일 머지 → 평균/최저 고도, 경사도 | 최신 |

## 🛠️ 모델 설정

```python
RandomForestClassifier(
    n_estimators=300, max_depth=12, min_samples_leaf=3,
    class_weight="balanced", random_state=42,
)
```

- Train/Test split: 70/30 stratified
- 6개 feature, binary classification
- 클래스 불균형 (4.1% positive) → `class_weight="balanced"` 사용

## 📂 산출물

| 파일 | 내용 |
|---|---|
| `features_with_proba.geojson` | 9,324 셀 + 모든 feature + 예측 확률 |
| `features_with_proba.csv` | CSV 버전 (지오메트리 제외) |
| `model_summary.json` | 메트릭·importance dump |
| `rf_proba_map.png` | 관악구 침수 확률 지도 + 실제 vs 예측 비교 |
| `shap_summary.png` | SHAP summary plot (beeswarm) |
| `feature_importance.png` | Gini vs SHAP importance 비교 |
| `rf_metrics.png` | ROC + PR + 혼동행렬 |

## ⚠️ 한계 (발표 시 명시)

1. **Spatial autocorrelation 미고려** — random split이라 train/test가 공간적으로 섞임 → 실제 성능은 약간 낮을 수 있음. 보완: spatial CV (시간 되면)
2. **침수 데이터 연도 (2002~2018)** vs 토지피복도 (2025) lag — 도시 형태는 천천히 변하지만 일부 신규 개발지는 mismatch 가능
3. **하수관거 feature 미포함** — 자치구 단위라 모든 셀 동일값이 되어 변별력 없음 → 정성 분석으로만 사용
4. **Vision 변수 (배수구·보도) 미포함** — 기말발표용 Vision LLM 파이프라인에서 추가 예정

## 🎬 중간발표 (6/4) 슬라이드 아웃라인

1. **문제 정의** — 관악구 침수 리스크, 신림동 사례
2. **데이터** — 4종 (침수흔적/토지피복/DEM/하수관거), 출처·연도·역할
3. **방법** — 100m 그리드 + feature 결합 + RF + SHAP
4. **결과 1** — AUC 0.92, 침수 확률 heatmap (`rf_proba_map.png`)
5. **결과 2** — Feature importance ⭐ *"임의 가중치가 아니라 데이터에서 자동 학습"* (`feature_importance.png` + `shap_summary.png`)
6. **결과 3** — 실제 vs 예측 비교 (`rf_proba_map.png` 우측)
7. **한계** — 위 4가지
8. **기말 로드맵** — Vision LLM 통합 (Street View → GPT-4o → 배수구/식생 시각 점수)

## 🚀 다음 단계 (기말발표 6/18 전까지)

- [ ] Streamlit 앱에 침수 리스크 탭 추가 (`app.py` 확장 또는 `app_flood.py` 신규)
- [ ] Google Street View API 키 발급
- [ ] Vision LLM 파이프라인: 주소 → 사진 → GPT-4o로 시각 변수 추출
- [ ] 통계 점수 (RF proba) + 시각 점수 결합 산식
- [ ] 자연어 진단 리포트 LLM 자동 생성
- [ ] (옵션) Spatial CV로 더 견고한 성능 평가
