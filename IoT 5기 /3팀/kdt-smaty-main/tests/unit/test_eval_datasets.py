"""평가셋이 실제 tool 계약과 어긋나지 않는지 API 호출 없이 검사한다.

파라프레이즈 평가 자체는 OpenAI를 호출하므로 opt-in 스크립트로 분리돼 있다.
그래도 tool 이름이나 인자 이름 오탈자는 돈을 쓰지 않고 잡을 수 있어야 한다.
"""

from __future__ import annotations

from collections import Counter

from smart_desk.modules.assistant.agents_tools import build_smart_desk_tools
from tests.eval.fixtures import (
    ACTIVITY_MODE_CATALOG,
    WLED_EFFECTS,
    WLED_PALETTES,
    build_eval_fixtures,
)
from tests.eval.schema import AUXILIARY_TOOLS, DATASET_DIR, load_all


def _tool_schemas() -> dict[str, dict]:
    return {tool.name: tool.params_json_schema for tool in build_smart_desk_tools()}


def test_every_expected_tool_exists() -> None:
    schemas = _tool_schemas()
    unknown = {
        case.case_id: case.expected_tool
        for case in load_all(DATASET_DIR)
        if case.expected_tool not in schemas
    }
    assert not unknown, f"존재하지 않는 tool을 기대하고 있습니다: {unknown}"


def test_every_alternative_tool_exists() -> None:
    schemas = _tool_schemas()
    unknown = {
        case.case_id: name
        for case in load_all(DATASET_DIR)
        for name in case.accept_also
        if name not in schemas
    }
    assert not unknown, f"존재하지 않는 대안 tool입니다: {unknown}"


def test_expected_arguments_exist_in_tool_schema() -> None:
    schemas = _tool_schemas()
    problems: list[str] = []
    for case in load_all(DATASET_DIR):
        properties = schemas.get(case.expected_tool, {}).get("properties", {})
        for key in case.expected_args_match:
            if key not in properties:
                problems.append(f"{case.case_id}: {case.expected_tool}에 인자 {key!r} 없음")
    assert not problems, problems


def _declared_types(schema: dict) -> set[str]:
    """``type``이든 ``anyOf``/``oneOf``든 선언된 JSON 타입을 모은다."""

    declared: set[str] = set()
    value = schema.get("type")
    if isinstance(value, str):
        declared.add(value)
    elif isinstance(value, list):
        declared.update(item for item in value if isinstance(item, str))
    for key in ("anyOf", "oneOf"):
        for variant in schema.get(key, []):
            if isinstance(variant, dict):
                declared |= _declared_types(variant)
    return declared


def test_range_matchers_only_target_numeric_arguments() -> None:
    """min/max matcher를 문자열 인자에 걸어두면 그 case는 영원히 실패한다."""

    schemas = _tool_schemas()
    problems: list[str] = []
    for case in load_all(DATASET_DIR):
        properties = schemas.get(case.expected_tool, {}).get("properties", {})
        for key, matcher in case.expected_args_match.items():
            if not isinstance(matcher, dict) or "any_of" in matcher:
                continue
            declared = _declared_types(properties.get(key, {}))
            # 타입을 못 읽은 경우는 넘어간다. 스키마 표현이 바뀌었다고 해서
            # 평가셋이 틀렸다고 단정할 근거는 없다.
            if declared and not declared & {"integer", "number"}:
                problems.append(
                    f"{case.case_id}: {case.expected_tool}.{key}의 타입이 {sorted(declared)}인데 범위 matcher를 씀"
                )
    assert not problems, problems


def test_expected_activity_mode_keys_come_from_the_fixture_catalog() -> None:
    """평가셋의 key가 fixture 목록에 없으면 model이 절대 맞힐 수 없다."""

    known = {mode.key for mode in ACTIVITY_MODE_CATALOG}
    problems = [
        f"{case.case_id}: {case.expected_args_match['key']!r}"
        for case in load_all(DATASET_DIR)
        if case.expected_tool == "set_activity_mode" and "key" in case.expected_args_match
        and case.expected_args_match["key"] not in known
    ]
    assert not problems, f"fixture 목록에 없는 작업 모드 key입니다: {problems}"


def test_expected_wled_ids_come_from_the_fixture_capabilities() -> None:
    effects = {effect.id for effect in WLED_EFFECTS}
    palettes = {palette.id for palette in WLED_PALETTES}
    problems: list[str] = []
    for case in load_all(DATASET_DIR):
        if case.expected_tool != "set_wled_effect":
            continue
        effect_id = case.expected_args_match.get("effect_id")
        if isinstance(effect_id, int) and effect_id not in effects:
            problems.append(f"{case.case_id}: 알 수 없는 effect_id {effect_id}")
        palette_id = case.expected_args_match.get("palette_id")
        if isinstance(palette_id, int) and palette_id not in palettes:
            problems.append(f"{case.case_id}: 알 수 없는 palette_id {palette_id}")
    assert not problems, problems


def test_utterances_are_unique() -> None:
    counts = Counter(case.utterance for case in load_all(DATASET_DIR))
    duplicates = {utterance: n for utterance, n in counts.items() if n > 1}
    assert not duplicates, f"중복된 발화가 있습니다: {duplicates}"


def test_auxiliary_tool_names_are_real_tools() -> None:
    """보조 tool 이름이 틀리면 채점이 조용히 관대해진다."""

    schemas = _tool_schemas()
    # web_search는 hosted tool이라 build_smart_desk_tools()에 없다.
    unknown = {name for name in AUXILIARY_TOOLS if name not in schemas} - {"web_search"}
    assert not unknown, f"존재하지 않는 보조 tool입니다: {unknown}"


async def test_eval_context_is_wired_only_to_fakes() -> None:
    """평가는 필요한 모듈만 실제로 동작시킨다.

    import 여부로는 이 성질을 확인할 수 없다. 이 프로젝트의 package
    ``__init__``들이 하위 모듈을 즉시 re-export해서, assistant tool 하나만
    가져와도 aiomqtt·cv2·pyserial까지 import 그래프에 딸려온다. 그래도 broker나
    카메라에 실제로 연결하지는 않는다.

    그래서 확인해야 할 것은 "무엇이 import됐나"가 아니라 "무엇이 turn context에
    실제로 연결됐나"다. 여기에 진짜 서비스가 하나라도 들어오면 평가가 운영
    장비를 건드리기 시작한다.
    """

    fixtures = await build_eval_fixtures()
    try:
        context = fixtures.context
        assert context.automation is fixtures.automation
        assert context.wled is fixtures.wled
        assert context.tilt is fixtures.tilt
        assert context.activity_modes is fixtures.activity_modes
        assert context.memory is fixtures.memory
        # context를 만드는 것만으로는 어떤 도메인 호출도 일어나지 않는다.
        assert not fixtures.automation.calls
        assert not fixtures.wled.calls
        assert not fixtures.tilt.calls
        assert not fixtures.activity_modes.calls
        assert not fixtures.memory.saved
    finally:
        await fixtures.close()


def test_dataset_covers_the_mutating_tools_we_care_about() -> None:
    """주요 제어 tool에 발화가 하나도 없으면 평가가 조용히 비어 버린다."""

    covered = {case.expected_tool for case in load_all(DATASET_DIR)}
    required = {
        "set_desk_target",
        "hold_desk",
        "stop_desk",
        "set_control_mode",
        "set_activity_mode",
        "set_tilt_level",
        "stop_tilt",
        "turn_wled_on",
        "turn_wled_off",
        "set_wled_brightness",
        "set_wled_color",
        "set_wled_effect",
        "remember_fact",
    }
    assert not required - covered, f"발화가 없는 tool: {sorted(required - covered)}"
