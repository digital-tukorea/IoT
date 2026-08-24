"""측정한 실행을 기준선으로 굳히고 다음 실행과 비교한다.

실패율 하나만 보면 좋아졌는지 알 수 없다. 같은 7.2%라도 고쳐진 발화와 새로
깨진 발화가 맞바꿔진 것일 수 있다. 그래서 발화 단위로 통과 여부를 저장하고,
다음 실행에서 **어떤 발화가 뒤집혔는지**를 본다.

case를 발화 문자열로 식별한다. ``dataset[index]``는 발화를 하나 끼워 넣기만
해도 뒤 번호가 전부 밀려서 기준선이 통째로 어긋난다.

``agents``/``openai``를 import하지 않으므로 API key 없이 비교만 할 수 있다.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from tests.eval.schema import CaseResult


BASELINE_PATH = Path(__file__).parent / "baseline.json"
SCHEMA_VERSION = 1


class BaselineError(ValueError):
    """기준선 파일이 스키마를 위반했다."""


@dataclass(frozen=True, slots=True)
class BaselineCase:
    utterance: str
    expected_tool: str
    passed: bool
    reason: str


@dataclass(frozen=True, slots=True)
class Baseline:
    generated_at: str
    model: str
    commit: str
    note: str
    cases: dict[str, BaselineCase]

    @property
    def total(self) -> int:
        return len(self.cases)

    @property
    def failed(self) -> int:
        return sum(1 for case in self.cases.values() if not case.passed)

    @property
    def failure_rate(self) -> float:
        return (self.failed / self.total) if self.total else 0.0


@dataclass(frozen=True, slots=True)
class Flip:
    """기준선과 결과가 갈린 발화 하나."""

    utterance: str
    expected_tool: str
    before: str
    after: str


@dataclass(slots=True)
class Comparison:
    regressions: list[Flip] = field(default_factory=list)
    fixes: list[Flip] = field(default_factory=list)
    still_failing: list[Flip] = field(default_factory=list)
    added: list[Flip] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    baseline_failure_rate: float = 0.0
    current_failure_rate: float = 0.0
    compared: int = 0

    @property
    def rate_delta(self) -> float:
        return self.current_failure_rate - self.baseline_failure_rate

    @property
    def has_regression(self) -> bool:
        return bool(self.regressions)


def build_baseline(
    results: Iterable[CaseResult], *, generated_at: str, model: str, commit: str, note: str = ""
) -> Baseline:
    cases = {
        result.case.utterance: BaselineCase(
            utterance=result.case.utterance,
            expected_tool=result.case.expected_tool,
            passed=result.passed,
            reason=result.reason,
        )
        for result in results
    }
    return Baseline(
        generated_at=generated_at, model=model, commit=commit, note=note, cases=cases
    )


def write_baseline(baseline: Baseline, path: Path = BASELINE_PATH) -> None:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": baseline.generated_at,
        "model": baseline.model,
        "commit": baseline.commit,
        "note": baseline.note,
        "summary": {
            "total": baseline.total,
            "passed": baseline.total - baseline.failed,
            "failed": baseline.failed,
            "failure_rate": round(baseline.failure_rate, 4),
        },
        "cases": [
            {
                "utterance": case.utterance,
                "expected_tool": case.expected_tool,
                "passed": case.passed,
                "reason": case.reason,
            }
            for case in sorted(baseline.cases.values(), key=lambda c: (c.expected_tool, c.utterance))
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_baseline(path: Path = BASELINE_PATH) -> Baseline:
    if not path.is_file():
        raise BaselineError(f"기준선 파일이 없습니다: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise BaselineError(f"{path.name}: 최상위는 mapping이어야 합니다.")
    version = raw.get("schema_version")
    if version != SCHEMA_VERSION:
        raise BaselineError(
            f"{path.name}: 지원하지 않는 schema_version {version!r} (이 코드는 {SCHEMA_VERSION})"
        )
    entries = raw.get("cases")
    if not isinstance(entries, list):
        raise BaselineError(f"{path.name}: cases는 list여야 합니다.")

    cases: dict[str, BaselineCase] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise BaselineError(f"{path.name}[{index}]: 각 case는 mapping이어야 합니다.")
        utterance = entry.get("utterance")
        expected_tool = entry.get("expected_tool")
        passed = entry.get("passed")
        if not isinstance(utterance, str) or not utterance:
            raise BaselineError(f"{path.name}[{index}]: utterance가 필요합니다.")
        if not isinstance(expected_tool, str) or not expected_tool:
            raise BaselineError(f"{path.name}[{index}]: expected_tool이 필요합니다.")
        if not isinstance(passed, bool):
            raise BaselineError(f"{path.name}[{index}]: passed는 boolean이어야 합니다.")
        if utterance in cases:
            raise BaselineError(f"{path.name}: 발화가 중복됩니다: {utterance!r}")
        reason = entry.get("reason")
        cases[utterance] = BaselineCase(
            utterance=utterance,
            expected_tool=expected_tool,
            passed=passed,
            reason=reason if isinstance(reason, str) else "",
        )
    return Baseline(
        generated_at=str(raw.get("generated_at", "")),
        model=str(raw.get("model", "")),
        commit=str(raw.get("commit", "")),
        note=str(raw.get("note", "")),
        cases=cases,
    )


def compare(
    baseline: Baseline, results: list[CaseResult], *, partial: bool = False
) -> Comparison:
    """기준선과 이번 결과를 발화 단위로 대조한다.

    ``partial``은 일부만 실행했다는 뜻이다. 이때 기준선에만 있는 발화는 사라진
    것이 아니라 이번에 안 돌린 것이므로 ``missing``으로 보고하지 않는다.
    """

    comparison = Comparison()
    seen: set[str] = set()
    # 실패율은 양쪽에 모두 있는 발화로만 계산한다. 일부만 돌렸을 때 250건짜리
    # 기준선 실패율과 63건짜리 이번 실패율을 나란히 놓으면 비교가 되지 않는다.
    scoped_current_failed = 0
    scoped_baseline_failed = 0

    for result in results:
        utterance = result.case.utterance
        seen.add(utterance)
        before = baseline.cases.get(utterance)
        after_state = "통과" if result.passed else result.reason
        if before is None:
            comparison.added.append(
                Flip(utterance, result.case.expected_tool, "기준선 없음", after_state)
            )
            continue
        comparison.compared += 1
        if not result.passed:
            scoped_current_failed += 1
        if not before.passed:
            scoped_baseline_failed += 1
        before_state = "통과" if before.passed else before.reason
        flip = Flip(utterance, result.case.expected_tool, before_state, after_state)
        if before.passed and not result.passed:
            comparison.regressions.append(flip)
        elif not before.passed and result.passed:
            comparison.fixes.append(flip)
        elif not before.passed and not result.passed:
            comparison.still_failing.append(flip)

    if not partial:
        comparison.missing = sorted(set(baseline.cases) - seen)

    scope = comparison.compared
    comparison.baseline_failure_rate = (scoped_baseline_failed / scope) if scope else 0.0
    comparison.current_failure_rate = (scoped_current_failed / scope) if scope else 0.0
    return comparison


def per_tool_delta(
    baseline: Baseline, results: list[CaseResult]
) -> dict[str, dict[str, float]]:
    """tool별로 기준선과 이번 실패 수를 나란히 놓는다.

    이번에 실행한 발화만 세므로, 일부만 돌려도 같은 기준으로 비교된다.
    """

    current: Counter[str] = Counter()
    current_failed: Counter[str] = Counter()
    before_total: Counter[str] = Counter()
    before_failed: Counter[str] = Counter()

    for result in results:
        tool = result.case.expected_tool
        current[tool] += 1
        if not result.passed:
            current_failed[tool] += 1
        entry = baseline.cases.get(result.case.utterance)
        if entry is not None:
            before_total[tool] += 1
            if not entry.passed:
                before_failed[tool] += 1

    delta: dict[str, dict[str, float]] = {}
    for tool in sorted(current):
        delta[tool] = {
            "total": current[tool],
            "failed": current_failed[tool],
            "baseline_total": before_total[tool],
            "baseline_failed": before_failed[tool],
        }
    return delta
