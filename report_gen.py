"""각 지점에 대해 GPT-4o-mini가 한국어 진단 + 정책 권고 자동 생성"""
import os
import json
from pathlib import Path
from openai import OpenAI

KEY = os.environ.get("OPENAI_API_KEY", "")
if not KEY:
    raise SystemExit("환경변수 OPENAI_API_KEY 필요")

client = OpenAI(api_key=KEY)
MODEL = "gpt-4o-mini"

SRC = Path("demo_points_hybrid.json")
OUT = Path("demo_points_full.json")

points = json.loads(SRC.read_text())

SYSTEM = """당신은 도시 홍수 리스크 분석가다. 입력으로 받은 좌표·통계 점수·시각 분석 결과를 종합해
간결한 진단 보고서를 작성한다. 출력 JSON 형식:
{
  "diagnosis": "3~4문장의 종합 진단 (왜 이 지역이 위험한지, 어떤 신호가 두드러지는지)",
  "policy": ["권고 1", "권고 2", "권고 3"]
}
권고는 실행 가능한 도시계획·인프라 액션 (예: 투수성 포장재 교체, 우수받이 추가, 녹지 확충, 침수경보 설치).
JSON만 출력, 다른 텍스트 금지."""


def make_report(p: dict) -> dict:
    v = p.get("vision", {})
    h = p.get("hybrid", {})
    prompt = f"""[지점 정보]
좌표: ({p['lat']:.5f}, {p['lon']:.5f})
RF 통계 모델 침수확률: {p['flood_proba']:.2f}
RF 입력 feature:
  - 불투수면 비율: {p['impervious_ratio']*100:.0f}%
  - 식생 비율: {p['veg_ratio']*100:.0f}%
  - 평균 고도: {p['elev_mean']:.0f}m
  - 평균 경사도: {p['slope_mean']:.1f}°

[Vision LLM 시각 분석]
  - 불투수면: {v.get('impervious_pct')}%
  - 배수구 상태: {v.get('drainage_score')}/10
  - 평지 정도: {v.get('flatness_score')}/10
  - 식생 피복: {v.get('vegetation_pct')}%
  - 보도 상태: {v.get('sidewalk_score')}/10
  - 시각 관찰: {v.get('notes')}

[종합 점수 (박루나 점수표 100점 만점)]
{json.dumps(h.get('components', {}), ensure_ascii=False, indent=2)}
총점: {h.get('total')}/100

위 정보를 종합해 진단과 정책 권고를 작성하라."""

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=600,
    )
    return json.loads(resp.choices[0].message.content)


for i, p in enumerate(points, 1):
    print(f"\n[{i}/{len(points)}] ({p['lat']:.5f}, {p['lon']:.5f}) 총점 {p['hybrid'].get('total')}/100")
    if not p.get("vision"):
        print("  vision 없음 — skip")
        continue
    try:
        report = make_report(p)
        p["report"] = report
        print(f"  진단: {report['diagnosis'][:120]}...")
        print(f"  권고: {len(report['policy'])}개")
        for r in report["policy"]:
            print(f"    • {r}")
    except Exception as e:
        print(f"  오류: {e}")
        p["report_error"] = str(e)

OUT.write_text(json.dumps(points, ensure_ascii=False, indent=2))
print(f"\n저장: {OUT}")
