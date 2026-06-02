"""README.md 의 D-day 섹션 자동 업데이트.

`<!-- DDAY:START -->` 와 `<!-- DDAY:END -->` 마커 사이를 매일 자동 교체.
"""
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
today = datetime.now(KST).date()

# 마일스톤 (수정 시 여기만)
MILESTONES = [
    ("중간 발표", datetime(2026, 6, 4).date()),
    ("기말 발표", datetime(2026, 6, 18).date()),
]


def fmt_dday(delta_days: int) -> str:
    if delta_days > 0:
        return f"**D-{delta_days}**"
    if delta_days == 0:
        return "**D-DAY** 🎯"
    return f"D+{-delta_days} (지남)"


lines = ["| 마일스톤 | 날짜 | D-day |", "|---|---|---|"]
for name, date in MILESTONES:
    delta = (date - today).days
    lines.append(f"| {name} | {date.isoformat()} | {fmt_dday(delta)} |")
lines.append("")
lines.append(f"_마지막 자동 갱신: {today.isoformat()} KST_")

table = "\n".join(lines)

readme = Path("README.md")
content = readme.read_text(encoding="utf-8")

new_content = re.sub(
    r"<!-- DDAY:START -->.*?<!-- DDAY:END -->",
    f"<!-- DDAY:START -->\n{table}\n<!-- DDAY:END -->",
    content,
    flags=re.DOTALL,
)

if new_content == content:
    print("변경 없음")
else:
    readme.write_text(new_content, encoding="utf-8")
    print("README.md D-day 섹션 업데이트 완료:")
    print(table)
