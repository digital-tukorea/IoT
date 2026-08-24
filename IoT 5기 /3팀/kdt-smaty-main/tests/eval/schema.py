"""파라프레이즈 평가셋의 로딩과 채점 규칙.

이 모듈은 ``pyyaml``만 필요하고 ``agents``/``openai``를 import하지 않는다.
데이터셋 검증 test가 API key 없이도 돌아야 하기 때문이다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DATASET_DIR = Path(__file__).parent / "datasets"

# 사용자의 의도를 이루기 위해 model이 추가로 부를 수 있는 읽기 전용·보조 tool.
# 기대한 tool이 함께 호출되었다면 이들이 섞여 있어도 오답으로 보지 않는다.
AUXILIARY_TOOLS = frozenset(
    {
        "request_followup",
        "list_activity_modes",
        "get_tilt_state",
        "get_wled_state",
        "get_wled_capabilities",
        "web_search",
    }
)


class DatasetError(ValueError):
    """평가셋 파일이 스키마를 위반했다."""


@dataclass(frozen=True, slots=True)
class ParaphraseCase:
    """실제 발화 하나와 그 발화가 만들어야 하는 tool 호출."""

    utterance: str
    expected_tool: str
    expected_args_match: dict[str, Any] = field(default_factory=dict)
    # 제품 관점에서 똑같이 옳은 대안 tool. 인자는 검사하지 않는다.
    accept_also: tuple[str, ...] = ()
    notes: str | None = None
    dataset: str = ""
    index: int = -1

    @property
    def case_id(self) -> str:
        return f"{self.dataset}[{self.index}]"


@dataclass(frozen=True, slots=True)
class ToolCall:
    """model이 실제로 만든 tool 호출 하나."""

    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CaseResult:
    case: ParaphraseCase
    calls: tuple[ToolCall, ...]
    passed: bool
    reason: str
    detail: str
    # model이 사용자에게 실제로 한 말. 되물었는지 단정했는지가 여기서 갈린다.
    response: str = ""

    @property
    def observed_tools(self) -> list[str]:
        return [call.name for call in self.calls]


def _match_value(expected: Any, actual: Any) -> str | None:
    """기대값 matcher 하나를 검사하고, 실패 사유만 문자열로 돌려준다."""

    if isinstance(expected, dict):
        if "any_of" in expected:
            options = expected["any_of"]
            if not isinstance(options, list):
                raise DatasetError("any_of는 list여야 합니다.")
            # 각 후보를 같은 규칙으로 비교해 색상 hex의 대소문자와 실수 오차를 흡수한다.
            if any(_match_value(option, actual) is None for option in options):
                return None
            return f"{actual!r}가 {options!r} 중 하나가 아님"
        minimum, maximum = expected.get("min"), expected.get("max")
        if minimum is None and maximum is None:
            raise DatasetError(f"지원하지 않는 matcher: {expected!r}")
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            return f"{actual!r}는 숫자가 아님"
        if minimum is not None and actual < minimum:
            return f"{actual!r} < 최소 {minimum!r}"
        if maximum is not None and actual > maximum:
            return f"{actual!r} > 최대 {maximum!r}"
        return None
    if isinstance(expected, float) or isinstance(actual, float):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            return f"{actual!r}는 숫자가 아님"
        if math.isclose(float(expected), float(actual), rel_tol=0, abs_tol=1e-6):
            return None
        return f"{actual!r} != {expected!r}"
    if isinstance(expected, str) and isinstance(actual, str):
        # WLED 색상처럼 대소문자만 다른 값은 같은 값으로 본다.
        if expected.casefold() == actual.casefold():
            return None
        return f"{actual!r} != {expected!r}"
    if expected == actual:
        return None
    return f"{actual!r} != {expected!r}"


def match_arguments(expected: dict[str, Any], actual: dict[str, Any]) -> str | None:
    """부분 일치 검사. 기대한 key만 보고 나머지 인자는 자유롭게 둔다."""

    for key, matcher in expected.items():
        if key not in actual:
            return f"인자 {key!r} 없음"
        failure = _match_value(matcher, actual[key])
        if failure is not None:
            return f"인자 {key!r}: {failure}"
    return None


def evaluate_case(
    case: ParaphraseCase, calls: list[ToolCall], response: str = ""
) -> CaseResult:
    """한 발화의 실행 결과를 통과/실패로 판정한다."""

    frozen = tuple(calls)
    matched = [call for call in calls if call.name == case.expected_tool]
    mismatches: list[str] = []
    for call in matched:
        failure = match_arguments(case.expected_args_match, call.arguments)
        if failure is None:
            return CaseResult(case, frozen, True, "ok", "", response)
        mismatches.append(failure)

    alternatives = [call.name for call in calls if call.name in case.accept_also]
    if alternatives:
        return CaseResult(
            case, frozen, True, "accepted_alternative", f"대안 tool {alternatives[0]!r} 호출", response
        )

    if mismatches:
        return CaseResult(
            case, frozen, False, "args_mismatch", "; ".join(dict.fromkeys(mismatches)), response
        )

    meaningful = [call.name for call in calls if call.name not in AUXILIARY_TOOLS]
    observed = ", ".join(meaningful) if meaningful else "없음"
    return CaseResult(
        case, frozen, False, "tool_not_called",
        f"기대 tool 미호출 (실제 제어 tool: {observed})", response,
    )


def _parse_case(entry: Any, *, dataset: str, index: int) -> ParaphraseCase:
    where = f"{dataset}[{index}]"
    if not isinstance(entry, dict):
        raise DatasetError(f"{where}: 각 항목은 mapping이어야 합니다.")
    unknown = set(entry) - {
        "utterance",
        "expected_tool",
        "expected_args_match",
        "accept_also",
        "notes",
    }
    if unknown:
        raise DatasetError(f"{where}: 알 수 없는 key {sorted(unknown)}")

    utterance = entry.get("utterance")
    if not isinstance(utterance, str) or not utterance.strip():
        raise DatasetError(f"{where}: utterance가 필요합니다.")
    expected_tool = entry.get("expected_tool")
    if not isinstance(expected_tool, str) or not expected_tool.strip():
        raise DatasetError(f"{where}: expected_tool이 필요합니다.")

    args = entry.get("expected_args_match") or {}
    if not isinstance(args, dict):
        raise DatasetError(f"{where}: expected_args_match는 mapping이어야 합니다.")

    accept_also = entry.get("accept_also") or []
    if not isinstance(accept_also, list) or any(not isinstance(x, str) for x in accept_also):
        raise DatasetError(f"{where}: accept_also는 문자열 list여야 합니다.")

    notes = entry.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise DatasetError(f"{where}: notes는 문자열이어야 합니다.")

    return ParaphraseCase(
        utterance=utterance.strip(),
        expected_tool=expected_tool.strip(),
        expected_args_match=args,
        accept_also=tuple(accept_also),
        notes=notes,
        dataset=dataset,
        index=index,
    )


def load_cases(path: Path) -> list[ParaphraseCase]:
    """평가셋 파일 하나를 읽는다. 잘못된 항목은 파일/번호와 함께 보고한다."""

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise DatasetError(f"{path.name}: 최상위 YAML은 list여야 합니다.")
    return [_parse_case(entry, dataset=path.stem, index=i) for i, entry in enumerate(raw)]


def load_all(directory: Path = DATASET_DIR) -> list[ParaphraseCase]:
    """데이터셋 디렉터리 전체를 파일 이름 순으로 읽는다."""

    cases: list[ParaphraseCase] = []
    for path in sorted(directory.glob("*.yaml")):
        cases.extend(load_cases(path))
    if not cases:
        raise DatasetError(f"{directory}에 평가셋이 없습니다.")
    return cases
