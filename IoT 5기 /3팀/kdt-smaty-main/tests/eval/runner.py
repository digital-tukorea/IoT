"""실제 Agent를 돌려 model이 고른 tool을 관찰한다.

tool을 직접 호출하지 않는다는 점이 unit test와의 핵심 차이다. 발화만 주고
``Runner.run()``이 만든 tool 호출을 그대로 읽어 기대값과 대조한다.

``agents``/``openai``는 함수 안에서만 import한다. 데이터셋 검증 test가 voice
optional dependency 없이도 이 package를 다룰 수 있어야 한다.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from tests.eval.schema import CaseResult, ParaphraseCase, ToolCall, evaluate_case


@dataclass(frozen=True, slots=True)
class RunnerOptions:
    """평가 실행 하나의 조정값."""

    model: str | None = None
    reasoning_effort: str | None = None
    include_web_search: bool = True
    max_turns: int = 8
    timeout_seconds: float = 90.0


def _tool_name(raw: Any) -> str:
    """function tool은 name을, hosted tool은 type을 이름으로 쓴다."""

    name = raw.get("name") if isinstance(raw, dict) else getattr(raw, "name", None)
    if isinstance(name, str) and name:
        return name
    raw_type = raw.get("type") if isinstance(raw, dict) else getattr(raw, "type", "")
    # "web_search_call" -> "web_search"
    return str(raw_type or "unknown").removesuffix("_call")


def _tool_arguments(raw: Any) -> dict[str, Any]:
    arguments = raw.get("arguments") if isinstance(raw, dict) else getattr(raw, "arguments", None)
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str) and arguments.strip():
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return {"__unparsed__": arguments}
        return parsed if isinstance(parsed, dict) else {"__value__": parsed}
    return {}


def extract_tool_calls(result: Any) -> list[ToolCall]:
    """SDK 실행 결과에서 tool 호출만 순서대로 뽑는다."""

    calls: list[ToolCall] = []
    for item in getattr(result, "new_items", []):
        if getattr(item, "type", "") != "tool_call_item":
            continue
        raw = getattr(item, "raw_item", None)
        if raw is None:
            continue
        calls.append(ToolCall(_tool_name(raw), _tool_arguments(raw)))
    return calls


def create_client(api_key: str) -> Any:
    from openai import AsyncOpenAI

    return AsyncOpenAI(api_key=api_key)


async def build_input_text(utterance: str, fixtures: Any) -> str:
    """운영 workflow와 같은 방식으로 장기 기억을 사용자 메시지에 붙인다.

    ``SmartDeskVoiceWorkflow.run``은 등록 사용자의 turn마다 Mem0를 검색해
    ``<profile_memory>`` 블록을 덧붙인다. 평가가 이걸 빼먹으면 model은 운영보다
    적은 정보로 판단하게 되고, 사용자별 높이 같은 건 알 도리가 없어진다.
    """

    context = fixtures.context
    if not context.turn_context.personalized:
        return utterance
    try:
        recalled = await context.memory.search(context.turn_context.profile_id, utterance)
    except Exception:
        return utterance

    references: list[str] = []
    remaining = 2_000
    for item in recalled:
        if not isinstance(item, dict):
            continue
        memory = item.get("memory")
        if not isinstance(memory, str):
            continue
        normalized = memory.strip()[:500][:remaining]
        if not normalized:
            continue
        references.append(normalized)
        remaining -= len(normalized)
    if not references:
        return utterance
    return utterance + "\n\n<profile_memory>\n" + "\n".join(references) + "\n</profile_memory>"


def build_config(options: RunnerOptions) -> Any:
    """운영 기본값에서 필요한 항목만 덮어쓴 voice config를 만든다."""

    from dataclasses import replace

    from smart_desk.modules.assistant.agents_runtime import AgentsVoiceConfig

    config = AgentsVoiceConfig()
    overrides: dict[str, Any] = {}
    if options.model:
        overrides["model"] = options.model
    if options.reasoning_effort:
        overrides["reasoning_effort"] = options.reasoning_effort
    return replace(config, **overrides) if overrides else config


async def run_case(case: ParaphraseCase, *, client: Any, options: RunnerOptions) -> CaseResult:
    """발화 하나를 새 context에서 실행하고 판정한다."""

    from agents import RunConfig, Runner

    from smart_desk.modules.assistant.agents_runtime import build_smart_desk_agent
    from smart_desk.modules.assistant.agents_tools import build_smart_desk_tools
    from tests.eval.fixtures import build_eval_fixtures

    # 운영 VoicePipeline과 같은 tracing 정책을 쓴다. 그쪽은 tracing_disabled=True와
    # trace_include_sensitive_data=False로 발화를 밖으로 내보내지 않는데, 평가만
    # 기본값으로 두면 같은 발화가 trace로 업로드된다.
    run_config = RunConfig(tracing_disabled=True, trace_include_sensitive_data=False)

    fixtures = await build_eval_fixtures()
    try:
        user_input = await build_input_text(case.utterance, fixtures)
        agent = build_smart_desk_agent(
            client,
            config=build_config(options),
            tools=build_smart_desk_tools(),
            include_web_search=options.include_web_search,
        )
        try:
            result = await asyncio.wait_for(
                Runner.run(
                    agent,
                    user_input,
                    context=fixtures.context,
                    max_turns=options.max_turns,
                    session=fixtures.context.turn_context.session,
                    run_config=run_config,
                ),
                timeout=options.timeout_seconds,
            )
        except asyncio.TimeoutError:
            return CaseResult(case, (), False, "run_error", f"{options.timeout_seconds}초 안에 끝나지 않음")
        except Exception as error:  # SDK/네트워크 오류는 오답과 구분해 보고한다.
            return CaseResult(case, (), False, "run_error", f"{type(error).__name__}: {error}")
        calls = extract_tool_calls(result)
        response = str(getattr(result, "final_output", "") or "")
        try:
            return evaluate_case(case, calls, response)
        except Exception as error:
            # 잘못된 matcher 하나 때문에 이미 비용을 쓴 실행 전체를 잃지 않는다.
            return CaseResult(
                case, tuple(calls), False, "run_error", f"채점 실패: {error}", response
            )
    finally:
        await fixtures.close()


async def run_cases(
    cases: list[ParaphraseCase],
    *,
    client: Any,
    options: RunnerOptions,
    concurrency: int = 4,
    on_result: Any = None,
) -> list[CaseResult]:
    """여러 발화를 제한된 동시 실행으로 돌리고 입력 순서대로 돌려준다."""

    semaphore = asyncio.Semaphore(max(1, concurrency))
    results: list[CaseResult | None] = [None] * len(cases)

    async def worker(index: int, case: ParaphraseCase) -> None:
        async with semaphore:
            try:
                result = await run_case(case, client=client, options=options)
            except Exception as error:
                # 발화 하나의 예상 못한 실패가 나머지 실행을 취소하지 않게 한다.
                result = CaseResult(case, (), False, "run_error", f"{type(error).__name__}: {error}")
        results[index] = result
        if on_result is not None:
            on_result(result)

    await asyncio.gather(*(worker(i, case) for i, case in enumerate(cases)))
    return [result for result in results if result is not None]
