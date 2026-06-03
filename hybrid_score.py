"""RF 통계 점수 + Vision LLM 점수 → 박루나 점수표 100점 만점

박루나 점수표 가중치:
  불투수면 25 / 배수구 20 / 도로경사 20 / 침수흔적 20 / 식생 10 / 보도 5

모든 항목: 점수 높을수록 침수 위험 ↑
"""
import json
from pathlib import Path

SRC = Path("demo_points_scored.json")
OUT = Path("demo_points_hybrid.json")

points = json.loads(SRC.read_text())


def hybrid(p: dict) -> dict:
    v = p.get("vision", {})
    if not v:
        return {"total": None, "components": {}, "note": "vision 분석 실패"}

    # 6요소 점수 (높을수록 위험)
    s_impervious = v["impervious_pct"] / 100 * 25
    s_drainage   = (10 - v["drainage_score"]) / 10 * 20     # 배수 부실↑ → 위험↑
    s_flatness   = v["flatness_score"] / 10 * 20             # 평지↑ → 위험↑
    s_flood_hist = p["flood_proba"] * 20                      # RF 침수확률
    s_vegetation = (100 - v["vegetation_pct"]) / 100 * 10    # 식생 부족↑ → 위험↑
    s_sidewalk   = (10 - v["sidewalk_score"]) / 10 * 5       # 보도 부실↑ → 위험↑

    components = {
        "불투수면 (25)":   round(s_impervious, 1),
        "배수구 (20)":     round(s_drainage, 1),
        "도로경사 (20)":   round(s_flatness, 1),
        "침수흔적 (20)":   round(s_flood_hist, 1),
        "식생 피복 (10)":  round(s_vegetation, 1),
        "보도 상태 (5)":   round(s_sidewalk, 1),
    }
    total = round(sum(components.values()), 1)
    return {"total": total, "components": components}


for p in points:
    p["hybrid"] = hybrid(p)
    if p["hybrid"]["total"] is not None:
        print(f"[{p['cell_id']}] ({p['lat']:.4f}, {p['lon']:.4f}): "
              f"총점 {p['hybrid']['total']:.1f}/100  ←  "
              f"불투수={p['hybrid']['components']['불투수면 (25)']}, "
              f"배수={p['hybrid']['components']['배수구 (20)']}, "
              f"경사={p['hybrid']['components']['도로경사 (20)']}, "
              f"침수={p['hybrid']['components']['침수흔적 (20)']}, "
              f"식생={p['hybrid']['components']['식생 피복 (10)']}, "
              f"보도={p['hybrid']['components']['보도 상태 (5)']}")

OUT.write_text(json.dumps(points, ensure_ascii=False, indent=2))
print(f"\n저장: {OUT}")

# 요약
totals = [p["hybrid"]["total"] for p in points if p["hybrid"]["total"] is not None]
print(f"\n총점 분포: min={min(totals):.1f}, max={max(totals):.1f}, mean={sum(totals)/len(totals):.1f}")
