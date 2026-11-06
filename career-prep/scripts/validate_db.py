#!/usr/bin/env python3
"""이력 DB 검증 (Rubric D1, D3, D5, D7의 기계 검사 부분).

사용:  python3 -I scripts/validate_db.py career-db/experiences.md
종료 코드: 0 = 오류 없음 (경고는 있을 수 있음), 1 = 오류 있음
"""
import re
import sys

HEADER = re.compile(r"^##\s+(EXP-\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*$")
FIELD = re.compile(r"^-\s*([^:]+?):\s*(.*)$")

REQUIRED = ["프로젝트", "원문", "정리", "역할", "지표", "키워드", "상태", "최종확인일", "출처"]
ROLES = {"led", "managed", "built", "operated", "contributed", "supported"}
STATES = {"확정", "미검증", "폐기"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# 민감 정보가 DB에 들어가지 않게 하는 경고용 단어 (경고만 한다)
SENSITIVE = ["퇴사", "휴직", "병가", "우울", "연봉", "협상", "불만", "해고", "갈등", "퇴직금"]


def parse(path):
    entries, cur = [], None
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\n")
            m = HEADER.match(line)
            if m:
                cur = {"id": m.group(1), "line": n, "fields": {}, "header": line}
                entries.append(cur)
                continue
            if cur is not None:
                fm = FIELD.match(line)
                if fm:
                    cur["fields"][fm.group(1).strip()] = fm.group(2).strip()
    return entries


def check_metric(value):
    """지표: 값 / 단위 / 기간 / 귀속 / 분모. 앞 4개는 필수."""
    if value in ("없음", ""):
        return None
    parts = [p.strip() for p in value.split("/")]
    if len(parts) < 4:
        return "지표는 '값 / 단위 / 기간 / 귀속 / 분모' 형식이어야 합니다 (최소 4칸)"
    if any(p == "" for p in parts[:4]):
        return "지표의 값, 단위, 기간, 귀속 중 빈 칸이 있습니다"
    return None


def main(path):
    errors, warns = [], []
    entries = parse(path)
    if not entries:
        print("항목이 없습니다. 헤더 형식: ## EXP-001 | 회사 | 직함 | 기간")
        return 1

    seen = set()
    for e in entries:
        eid, f, ln = e["id"], e["fields"], e["line"]
        if eid in seen:
            errors.append(f"{eid} (줄 {ln}): ID가 중복됩니다")
        seen.add(eid)

        for k in REQUIRED:
            if k not in f or f[k] == "":
                errors.append(f"{eid}: 필수 필드 '{k}' 누락")

        if f.get("역할") and f["역할"] not in ROLES:
            errors.append(f"{eid}: 역할 '{f['역할']}' 은 {sorted(ROLES)} 중 하나여야 합니다")
        if f.get("상태") and f["상태"] not in STATES:
            errors.append(f"{eid}: 상태 '{f['상태']}' 은 {sorted(STATES)} 중 하나여야 합니다")
        if f.get("최종확인일") and not DATE.match(f["최종확인일"]):
            errors.append(f"{eid}: 최종확인일은 YYYY-MM-DD 형식이어야 합니다")

        if "지표" in f:
            msg = check_metric(f["지표"])
            if msg:
                # 확정 항목은 오류, 미검증·폐기 항목은 경고
                (errors if f.get("상태") == "확정" else warns).append(f"{eid}: {msg}")
            if "미확인" in f["지표"] and f.get("상태") == "확정":
                errors.append(f"{eid}: 지표에 '미확인'이 있는데 상태가 '확정'입니다 (미검증으로 바꾸세요)")

        text = " ".join(f.values())
        for w in SENSITIVE:
            if w in text:
                warns.append(f"{eid}: 민감어 '{w}' 포함. DB에 두어도 되는 내용인지 확인하세요")

    print(f"항목 {len(entries)}개 검사: 오류 {len(errors)}건, 경고 {len(warns)}건")
    for m in errors:
        print("  [오류]", m)
    for m in warns:
        print("  [경고]", m)
    return 1 if errors else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용: python3 -I scripts/validate_db.py <experiences.md>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
