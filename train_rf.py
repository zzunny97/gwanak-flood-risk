"""RF 학습 + SHAP + 시각화 4종"""
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib as mpl
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (roc_auc_score, roc_curve, confusion_matrix,
                              classification_report, precision_recall_curve, average_precision_score)
import shap

mpl.rcParams["font.family"] = "AppleGothic"
mpl.rcParams["axes.unicode_minus"] = False

print("=" * 60)
print("Step 2: RF 학습 + SHAP")
print("=" * 60)

# 1. 데이터 로드
df = pd.read_csv("features_gwanak.csv")
print(f"\n전체 셀: {len(df):,}")
print(f"침수 셀: {df['flood_label'].sum():,} ({df['flood_label'].mean()*100:.1f}%)")

FEATURES = ["impervious_ratio", "veg_ratio", "elev_mean", "elev_min",
            "slope_mean", "slope_max"]
FEATURE_LABELS = {
    "impervious_ratio": "불투수면 비율",
    "veg_ratio": "식생 비율",
    "elev_mean": "평균 고도(m)",
    "elev_min": "최저 고도(m)",
    "slope_mean": "평균 경사도(°)",
    "slope_max": "최대 경사도(°)",
}

X = df[FEATURES].values
y = df["flood_label"].values

# 2. train/test split (random)
X_tr, X_te, y_tr, y_te, idx_tr, idx_te = train_test_split(
    X, y, df.index, test_size=0.3, random_state=42, stratify=y
)
print(f"train {len(X_tr):,}, test {len(X_te):,}")
print(f"train 침수율 {y_tr.mean()*100:.1f}%, test 침수율 {y_te.mean()*100:.1f}%")

# 3. RF 학습
print("\n--- RF 학습 ---")
clf = RandomForestClassifier(
    n_estimators=300, max_depth=12, min_samples_leaf=3,
    class_weight="balanced", n_jobs=-1, random_state=42,
)
clf.fit(X_tr, y_tr)
proba_te = clf.predict_proba(X_te)[:, 1]
pred_te = (proba_te > 0.5).astype(int)

auc = roc_auc_score(y_te, proba_te)
ap = average_precision_score(y_te, proba_te)
print(f"AUC (ROC): {auc:.3f}")
print(f"AP (PR): {ap:.3f}")
print("\n혼동행렬:")
print(confusion_matrix(y_te, pred_te))
print("\n분류 리포트:")
print(classification_report(y_te, pred_te, target_names=["비침수", "침수"]))

# 4. 전체 셀에 대해 확률 예측 (시각화용)
df["flood_proba"] = clf.predict_proba(X)[:, 1]

# 5. SHAP
print("\n--- SHAP ---")
explainer = shap.TreeExplainer(clf)
# SHAP은 양성 클래스(1)에 대한 기여도
# 무거우니까 sample
sample_idx = np.random.RandomState(42).choice(len(X), size=min(1000, len(X)), replace=False)
shap_values = explainer.shap_values(X[sample_idx])
# 새 API는 (n,m,2), 옛 API는 list[2]
if isinstance(shap_values, list):
    shap_pos = shap_values[1]
elif shap_values.ndim == 3:
    shap_pos = shap_values[:, :, 1]
else:
    shap_pos = shap_values
print(f"SHAP shape: {shap_pos.shape}")

# Feature importance
imp_gain = pd.Series(clf.feature_importances_, index=[FEATURE_LABELS[f] for f in FEATURES]).sort_values(ascending=False)
imp_shap = pd.Series(np.abs(shap_pos).mean(axis=0), index=[FEATURE_LABELS[f] for f in FEATURES]).sort_values(ascending=False)
print("\n[Gini Importance]")
print(imp_gain.to_string())
print("\n[SHAP Importance (|SHAP| mean)]")
print(imp_shap.to_string())

# ===== 시각화 =====
print("\n=" * 30)
print("Step 3: 시각화")
print("=" * 60)

# (a) 침수 확률 heatmap (지도)
print("\n[a] 침수 확률 heatmap...")
gdf = gpd.read_file("features_gwanak.geojson")
gdf["flood_proba"] = df["flood_proba"].values
gdf["flood_label"] = df["flood_label"].values

fig, axes = plt.subplots(1, 2, figsize=(20, 10))
ax = axes[0]
gdf.plot(column="flood_proba", ax=ax, cmap="YlOrRd", legend=True,
          edgecolor="none", legend_kwds={"label": "침수 확률", "shrink": 0.7})
ax.set_title(f"관악구 침수 확률 (RF, AUC={auc:.3f})", fontsize=14, fontweight="bold")
ax.set_xlabel("경도"); ax.set_ylabel("위도")

ax = axes[1]
gdf.plot(ax=ax, color="lightgrey", edgecolor="none")
flood_actual = gdf[gdf["flood_label"] == 1]
flood_pred = gdf[gdf["flood_proba"] > 0.5]
flood_actual.plot(ax=ax, color="#1f77b4", alpha=0.7, edgecolor="none", label="실제 침수 셀")
flood_pred.plot(ax=ax, facecolor="none", edgecolor="#d62728", linewidth=0.5, label="예측 침수 (proba>0.5)")
ax.set_title("실제 vs 예측 비교", fontsize=14, fontweight="bold")
ax.legend(loc="lower right", fontsize=10)
ax.set_xlabel("경도"); ax.set_ylabel("위도")
plt.tight_layout()
plt.savefig("rf_proba_map.png", dpi=130, bbox_inches="tight")
print("  → rf_proba_map.png")

# (b) SHAP summary plot
print("\n[b] SHAP summary plot...")
fig = plt.figure(figsize=(11, 6))
shap.summary_plot(shap_pos, X[sample_idx],
                   feature_names=[FEATURE_LABELS[f] for f in FEATURES],
                   show=False, plot_size=None)
plt.title("SHAP Summary — 각 feature가 침수 확률에 미치는 영향", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig("shap_summary.png", dpi=130, bbox_inches="tight")
plt.close()
print("  → shap_summary.png")

# (c) Feature importance 비교 (Gini vs SHAP)
print("\n[c] Feature importance 비교...")
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
ax = axes[0]
imp_gain.plot(kind="barh", ax=ax, color="#2a9d8f")
ax.invert_yaxis()
ax.set_title("Gini Importance", fontsize=12, fontweight="bold")
ax.set_xlabel("중요도")

ax = axes[1]
imp_shap.plot(kind="barh", ax=ax, color="#e76f51")
ax.invert_yaxis()
ax.set_title("SHAP Importance (|SHAP| mean)", fontsize=12, fontweight="bold")
ax.set_xlabel("기여도")

plt.suptitle("Feature Importance — 두 방식 비교", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig("feature_importance.png", dpi=130, bbox_inches="tight")
print("  → feature_importance.png")

# (d) ROC + Precision-Recall + 혼동행렬
print("\n[d] ROC + PR + 혼동행렬...")
fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))

# ROC
ax = axes[0]
fpr, tpr, _ = roc_curve(y_te, proba_te)
ax.plot(fpr, tpr, color="#d62728", lw=2, label=f"RF (AUC={auc:.3f})")
ax.plot([0, 1], [0, 1], "--", color="grey", alpha=0.5)
ax.set_xlabel("False Positive Rate")
ax.set_ylabel("True Positive Rate")
ax.set_title("ROC Curve", fontsize=12, fontweight="bold")
ax.legend(loc="lower right")
ax.grid(alpha=0.3)

# PR
ax = axes[1]
prec, rec, _ = precision_recall_curve(y_te, proba_te)
ax.plot(rec, prec, color="#1f77b4", lw=2, label=f"AP={ap:.3f}")
ax.axhline(y_te.mean(), color="grey", linestyle="--", alpha=0.5, label=f"baseline ({y_te.mean()*100:.1f}%)")
ax.set_xlabel("Recall")
ax.set_ylabel("Precision")
ax.set_title("Precision-Recall Curve", fontsize=12, fontweight="bold")
ax.legend()
ax.grid(alpha=0.3)

# 혼동행렬
ax = axes[2]
cm = confusion_matrix(y_te, pred_te)
ax.imshow(cm, cmap="Blues")
ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
ax.set_xticklabels(["비침수", "침수"]); ax.set_yticklabels(["비침수", "침수"])
ax.set_xlabel("예측"); ax.set_ylabel("실제")
ax.set_title("혼동행렬 (threshold=0.5)", fontsize=12, fontweight="bold")
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{cm[i,j]:,}", ha="center", va="center",
                color="white" if cm[i,j] > cm.max()/2 else "black", fontsize=14)

plt.tight_layout()
plt.savefig("rf_metrics.png", dpi=130, bbox_inches="tight")
print("  → rf_metrics.png")

# 결과 저장
df.to_csv("features_with_proba.csv", index=False)
gdf.to_file("features_with_proba.geojson", driver="GeoJSON")
print("\n저장: features_with_proba.csv / .geojson")

# 모델 메트릭 요약 저장
summary = {
    "n_cells": len(df),
    "n_positive": int(df["flood_label"].sum()),
    "positive_ratio": float(df["flood_label"].mean()),
    "auc": float(auc),
    "average_precision": float(ap),
    "test_size": len(X_te),
    "features": FEATURES,
    "importance_gini": imp_gain.to_dict(),
    "importance_shap": imp_shap.to_dict(),
    "confusion_matrix": cm.tolist(),
}
import json
with open("model_summary.json", "w") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print("저장: model_summary.json")

print("\n" + "=" * 60)
print("완료. 산출물:")
print("  - rf_proba_map.png       (침수 확률 지도 + 실제vs예측)")
print("  - shap_summary.png       (SHAP summary plot)")
print("  - feature_importance.png (Gini vs SHAP)")
print("  - rf_metrics.png         (ROC + PR + 혼동행렬)")
print("  - features_with_proba.geojson")
print("  - model_summary.json")
print("=" * 60)
