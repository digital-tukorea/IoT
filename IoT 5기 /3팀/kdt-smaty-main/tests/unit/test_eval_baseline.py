"""기준선 저장과 회귀 비교 규칙을 API 호출 없이 검증한다."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.eval.baseline import (
    BASELINE_PATH,
    Baseline,
    BaselineCase,
    BaselineError,
    build_baseline,
    compare,
    load_baseline,
    per_tool_delta,
    write_baseline,
)
from tests.eval.schema import CaseResult, ParaphraseCase, load_all


def _case(utterance: str, tool: str = "set_desk_target") -> ParaphraseCase:
    return ParaphraseCase(utterance=utterance, expected_tool=tool, dataset="d", index=0)


def _result(utterance: str, passed: bool, tool: str = "set_desk_target") -> CaseResult:
    return CaseResult(_case(utterance, tool), (), passed, "ok" if passed else "tool_not_called", "")


def _baseline(entries: dict[str, bool], tool: str = "set_desk_target") -> Baseline:
    return Baseline(
        generated_at="2026-08-19T00:00:00+00:00",
        model="test",
        commit="abc1234",
        note="",
        cases={
            utterance: BaselineCase(utterance, tool, passed, "ok" if passed else "tool_not_called")
            for utterance, passed in entries.items()
        },
    )


def test_write_and_load_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    original = build_baseline(
        [_result("책상 올려줘", True), _result("책상 내려줘", False)],
        generated_at="2026-08-19T00:00:00+00:00",
        model="gpt-test",
        commit="deadbee",
        note="메모",
    )
    write_baseline(original, path)
    loaded = load_baseline(path)

    assert loaded.total == 2
    assert loaded.failed == 1
    assert loaded.failure_rate == pytest.approx(0.5)
    assert loaded.model == "gpt-test" and loaded.commit == "deadbee" and loaded.note == "메모"
    assert loaded.cases["책상 내려줘"].passed is False


def test_compare_separates_regressions_from_fixes() -> None:
    baseline = _baseline({"통과했던 발화": True, "실패했던 발화": False, "계속 실패": False})
    results = [
        _result("통과했던 발화", False),
        _result("실패했던 발화", True),
        _result("계속 실패", False),
    ]

    comparison = compare(baseline, results, partial=True)

    assert [flip.utterance for flip in comparison.regressions] == ["통과했던 발화"]
    assert [flip.utterance for flip in comparison.fixes] == ["실패했던 발화"]
    assert [flip.utterance for flip in comparison.still_failing] == ["계속 실패"]
    assert comparison.has_regression is True
    assert comparison.compared == 3


def test_equal_failure_rate_still_reports_a_swap() -> None:
    """실패율만 보면 같아 보이는 변화를 놓치지 않아야 한다."""

    baseline = _baseline({"가": True, "나": False})
    results = [_result("가", False), _result("나", True)]

    comparison = compare(baseline, results, partial=True)

    assert comparison.rate_delta == pytest.approx(0.0)
    assert len(comparison.regressions) == 1 and len(comparison.fixes) == 1


def test_new_utterance_is_added_not_a_regression() -> None:
    baseline = _baseline({"기존 발화": True})
    results = [_result("기존 발화", True), _result("새 발화", False)]

    comparison = compare(baseline, results, partial=True)

    assert not comparison.regressions
    assert [flip.utterance for flip in comparison.added] == ["새 발화"]


def test_partial_run_compares_failure_rates_on_the_same_utterances() -> None:
    """250건짜리 기준선 실패율을 63건짜리 이번 실패율과 나란히 놓으면 안 된다."""

    baseline = _baseline({"돌린 발화": False, "안 돌린 발화": False, "안 돌린 발화2": False})
    results = [_result("돌린 발화", True)]

    comparison = compare(baseline, results, partial=True)

    # 기준선 전체 실패율은 100%지만, 돌린 발화 하나로 좁히면 그것도 100%였다.
    assert comparison.compared == 1
    assert comparison.baseline_failure_rate == pytest.approx(1.0)
    assert comparison.current_failure_rate == pytest.approx(0.0)
    assert comparison.rate_delta == pytest.approx(-1.0)


def test_added_utterances_do_not_skew_the_rate_delta() -> None:
    baseline = _baseline({"기존": True})
    results = [_result("기존", True), _result("새 발화", False)]

    comparison = compare(baseline, results, partial=True)

    # 새 발화는 기준선에 없으니 비교 대상 실패율에 섞이지 않는다.
    assert comparison.compared == 1
    assert comparison.current_failure_rate == pytest.approx(0.0)


def test_partial_run_does_not_report_unrun_utterances_as_missing() -> None:
    baseline = _baseline({"돌린 발화": True, "안 돌린 발화": True})
    results = [_result("돌린 발화", True)]

    assert compare(baseline, results, partial=True).missing == []
    assert compare(baseline, results, partial=False).missing == ["안 돌린 발화"]


def test_per_tool_delta_counts_only_utterances_that_ran() -> None:
    baseline = Baseline(
        generated_at="", model="", commit="", note="",
        cases={
            "높이 발화": BaselineCase("높이 발화", "set_desk_target", False, "tool_not_called"),
            "조명 발화": BaselineCase("조명 발화", "turn_wled_on", True, "ok"),
        },
    )
    results = [_result("높이 발화", True, "set_desk_target")]

    delta = per_tool_delta(baseline, results)

    assert set(delta) == {"set_desk_target"}
    assert delta["set_desk_target"] == {
        "total": 1, "failed": 0, "baseline_total": 1, "baseline_failed": 1
    }


def test_unsupported_schema_version_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps({"schema_version": 99, "cases": []}), encoding="utf-8")

    with pytest.raises(BaselineError, match="schema_version"):
        load_baseline(path)


def test_duplicate_utterance_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    path.write_text(
        json.dumps({
            "schema_version": 1,
            "cases": [
                {"utterance": "같은 말", "expected_tool": "stop_desk", "passed": True},
                {"utterance": "같은 말", "expected_tool": "stop_desk", "passed": False},
            ],
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(BaselineError, match="중복"):
        load_baseline(path)


def test_missing_baseline_file_is_reported_clearly(tmp_path: Path) -> None:
    with pytest.raises(BaselineError, match="기준선 파일이 없습니다"):
        load_baseline(tmp_path / "없는파일.json")


def test_shipped_baseline_matches_the_current_dataset() -> None:
    """기준선이 지금 없는 발화를 가리키면 그만큼 비교 범위가 조용히 줄어든다."""

    baseline = load_baseline(BASELINE_PATH)
    utterances = {case.utterance for case in load_all()}
    stale = sorted(set(baseline.cases) - utterances)

    assert not stale, (
        f"기준선에만 있는 발화입니다. 데이터셋을 고쳤다면 --update-baseline으로 갱신하세요: {stale}"
    )
