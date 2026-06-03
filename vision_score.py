"""Street View 이미지 → GPT-4o-mini Vision → 6요소 시각 점수

박루나 점수표 6요소를 LLM이 사진에서 추정:
  - 불투수면 비율 (0~100, %)
  - 배수구 상태 (0~10, 10=양호)
  - 경사도 인지 (0~10, 10=완전 평지=위험)
  - 식생 피복 (0~100, %)
  - 보도 노후도 (0~10, 10=신규)
  - 침수 위험 정성 평가 (0~10, 10=위험 높음)

지점당 4방향 사진을 한 호출에 같이 넘겨 종합 판단.
"""
import os
import sys
import json
import base64
from pathlib import Path
from openai import OpenAI

KEY = os.environ.get("OPENAI_API_KEY", "")
if not KEY:
    raise SystemExit("환경변수 OPENAI_API_KEY 필요")

client = OpenAI(api_key=KEY)
MODEL = "gpt-4o-mini"

SYSTEM = """You are an urban flood risk assessor analyzing Korean street view images.
Given 4 directional photos (north/east/south/west) of one point, return JSON only:
{
  "impervious_pct": 0-100,        // 불투수면(아스팔트/콘크리트/건물) 비율
  "drainage_score": 0-10,         // 배수구 보임 + 상태, 10=많고 깨끗
  "flatness_score": 0-10,         // 평지일수록 높음 = 침수 취약, 10=완전 평지
  "vegetation_pct": 0-100,        // 식생(나무/잔디/녹지) 비율
  "sidewalk_score": 0-10,         // 보도 상태, 10=신규/넓음, 0=없거나 파손
  "risk_qualitative": 0-10,       // 종합 침수 위험도 시각 판단, 10=고위험
  "notes": "한국어 1~2문장 관찰"  // 무엇이 위험하거나 양호한지
}
No prose, JSON only.
"""


def encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def score_point(image_paths: dict[int, Path], verbose: bool = False) -> dict:
    """{heading: path} → 점수 JSON"""
    content = [{"type": "text", "text":
                "Analyze these 4 directional street view photos of one point. Return JSON only."}]
    for h in sorted(image_paths.keys()):
        content.append({"type": "text", "text": f"Direction {h}°:"})
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{encode_image(image_paths[h])}",
                           "detail": "low"},  # low로 비용 절감 (per image ~$0.001)
        })

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": content},
        ],
        response_format={"type": "json_object"},
        max_tokens=400,
    )
    raw = resp.choices[0].message.content
    if verbose:
        print(f"  raw: {raw}")
    return json.loads(raw)


def score_all_demo(demo_json: str = "demo_points.json") -> list[dict]:
    points = json.loads(Path(demo_json).read_text())
    out = []
    for i, p in enumerate(points, 1):
        print(f"[{i}/{len(points)}] ({p['lat']:.5f}, {p['lon']:.5f}) RF proba={p['flood_proba']:.2f}")
        if not p.get("images"):
            print("  이미지 없음 — skip")
            continue
        image_paths = {int(h): Path(path) for h, path in p["images"].items()}
        try:
            scores = score_point(image_paths)
            p["vision"] = scores
            print(f"  → 불투수={scores['impervious_pct']}%, 배수={scores['drainage_score']}/10, "
                  f"평지={scores['flatness_score']}/10, 위험={scores['risk_qualitative']}/10")
            print(f"  📝 {scores.get('notes', '')[:80]}")
        except Exception as e:
            print(f"  오류: {e}")
            p["vision_error"] = str(e)
        out.append(p)
    Path("demo_points_scored.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\n저장: demo_points_scored.json")
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 첫 데모 지점 한 곳만 테스트
        points = json.loads(Path("demo_points.json").read_text())
        p = points[0]
        print(f"테스트: ({p['lat']}, {p['lon']})")
        image_paths = {int(h): Path(path) for h, path in p["images"].items()}
        scores = score_point(image_paths, verbose=True)
        print(json.dumps(scores, ensure_ascii=False, indent=2))
    else:
        score_all_demo()
