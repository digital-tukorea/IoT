"""평가용 실행 context와 가짜 도메인 서비스.

``tests/unit/test_agents_tools.py``의 ``_Automation``/``_Wled`` 패턴을 그대로
재사용한다. 다만 unit test와 달리 여기서는 tool을 직접 부르지 않는다. 어떤
tool을 어떤 인자로 부를지는 전적으로 model이 정하고, 이 fake들은 그 선택을
기록하는 역할만 한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

from smart_desk.modules.assistant.agents_tools import SmartDeskAgentContext
from smart_desk.modules.assistant.context import CurrentUserSessionManager
from smart_desk.modules.assistant.turns import AssistantTurnStore
from smart_desk.modules.identity.models import SessionKind
from smart_desk.modules.identity.session import CurrentUserSessionService


class _Automation:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    async def stop_motion(self) -> None:
        self.calls.append(("stop_motion", (), {}))

    async def hold(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("hold", args, kwargs))

    async def set_target(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("set_target", args, kwargs))

    async def set_control_mode(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("set_control_mode", args, kwargs))

    async def set_activity_mode(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("set_activity_mode", args, kwargs))


class _Wled:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self.on = True
        self.brightness = 128

    async def _call(self, name: str, *args: Any, **kwargs: Any) -> SimpleNamespace:
        self.calls.append((name, args, kwargs))
        return SimpleNamespace(on=self.on, brightness=self.brightness, mode=None)

    async def refresh_state(self) -> SimpleNamespace:
        return await self._call("refresh_state")

    async def refresh_capabilities(self) -> SimpleNamespace:
        self.calls.append(("refresh_capabilities", (), {}))
        return SimpleNamespace(effects=WLED_EFFECTS, palettes=WLED_PALETTES)

    async def turn_on(self, *a: Any, **k: Any) -> SimpleNamespace: return await self._call("turn_on", *a, **k)
    async def turn_off(self, *a: Any, **k: Any) -> SimpleNamespace: return await self._call("turn_off", *a, **k)
    async def set_brightness(self, *a: Any, **k: Any) -> SimpleNamespace: return await self._call("set_brightness", *a, **k)
    async def set_solid(self, *a: Any, **k: Any) -> SimpleNamespace: return await self._call("set_solid", *a, **k)
    async def set_effect(self, *a: Any, **k: Any) -> SimpleNamespace: return await self._call("set_effect", *a, **k)


# get_wled_capabilities가 돌려주는 고정 목록. 평가셋의 효과 이름은 여기서만 온다.
WLED_EFFECTS: tuple[SimpleNamespace, ...] = (
    SimpleNamespace(id=0, name="Solid"),
    SimpleNamespace(id=2, name="Breathe"),
    SimpleNamespace(id=9, name="Rainbow"),
    SimpleNamespace(id=38, name="Aurora"),
    SimpleNamespace(id=45, name="Fire Flicker"),
)
WLED_PALETTES: tuple[SimpleNamespace, ...] = (
    SimpleNamespace(id=0, name="Default"),
    SimpleNamespace(id=3, name="Party"),
    SimpleNamespace(id=8, name="Ocean"),
)


# 등록 사용자에게 이미 쌓여 있을 법한 장기 기억. 운영에서는 매 turn Mem0를
# 검색해 이 내용을 사용자 메시지에 붙이므로, 평가도 같은 조건이어야 한다.
# 특히 "앉을 수 있게 해줘"처럼 사용자별 높이를 알아야 답할 수 있는 발화는
# 이 기억이 없으면 model이 되물을 수밖에 없다.
SEEDED_PROFILE_MEMORIES: tuple[dict[str, str], ...] = (
    {"id": "mem-00000001", "memory": "앉아서 일할 때 책상 높이는 72센티미터를 좋아한다"},
    {"id": "mem-00000002", "memory": "서서 일할 때 책상 높이는 110센티미터를 좋아한다"},
    {"id": "mem-00000003", "memory": "조명은 따뜻한 색을 선호한다"},
    {"id": "mem-00000004", "memory": "선호하는 틸팅 단계는 2단계다"},
    {"id": "mem-00000005", "memory": "모니터를 두 대 사용한다"},
)
# 시드에 넣은 사실은 remember_fact 발화의 대상과 겹치면 안 된다. 이미 기억하고
# 있으면 model이 저장하지 않고 "이미 알고 있다"고 답하는 게 옳기 때문이다.
# 반대로 forget_fact 발화는 시드에 있는 사실만 가리켜야 한다.


class _Memory:
    def __init__(self, stored: tuple[dict[str, str], ...] = SEEDED_PROFILE_MEMORIES) -> None:
        self.saved: list[tuple[str, str, bool]] = []
        self.deleted: list[str] = []
        self.stored: list[dict[str, Any]] = [dict(item) for item in stored]

    async def remember(self, profile_id: str, fact: str, *, explicit: bool, **_kwargs: object) -> bool:
        self.saved.append((profile_id, fact, explicit))
        return True

    async def search(self, profile_id: str, query: str) -> list[dict[str, Any]]:
        del profile_id, query
        return list(self.stored)

    async def delete(self, profile_id: str, memory_id: str, **_kwargs: object) -> None:
        del profile_id
        self.deleted.append(memory_id)


class _Tilt:
    """``get_snapshot``/``set_target``/``stop_motion``만 노출하는 최소 틸트 fake."""

    def __init__(self, *, level: int = 0, state: str = "IDLE", position_valid: bool = True) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self.level = level
        self.target_level = level
        self.state = state
        self.position_valid = position_valid

    def get_snapshot(self) -> SimpleNamespace:
        return SimpleNamespace(
            state=self.state,
            level=self.level,
            target_level=self.target_level,
            position_valid=self.position_valid,
        )

    async def set_target(self, level: int) -> None:
        self.calls.append(("set_target", (level,), {}))
        self.target_level = level

    async def stop_motion(self, reason: str = "") -> None:
        self.calls.append(("stop_motion", (reason,), {}))


@dataclass(frozen=True, slots=True)
class ActivityModeFixture:
    """``list_activity_modes``가 읽는 속성만 가진 작업 모드."""

    key: str
    name: str
    description: str | None
    led_color: str | None
    led_brightness: int | None
    tilt_level: int | None


# 실제 custom 작업 모드의 key는 ``mode-<32자리 hex>``인 불투명 ID다. 사람이 읽을
# 수 있는 key를 쓰면 model이 list_activity_modes 없이도 찍어 맞힐 수 있어,
# "이름을 듣고 key를 조회한다"는 정작 검증하려는 동작이 평가에서 빠진다.
ACTIVITY_MODE_CATALOG: tuple[ActivityModeFixture, ...] = (
    ActivityModeFixture("default", "기본", "프로필 기본값", "FFFFFF", 128, 0),
    ActivityModeFixture(
        "mode-11111111111111111111111111111111", "공부 모드", "앉아서 집중할 때", "FFF4D6", 200, 1
    ),
    ActivityModeFixture(
        "mode-22222222222222222222222222222222", "게임 모드", "게임할 때 쓰는 조명", "6C2BD9", 180, 1
    ),
    ActivityModeFixture(
        "mode-33333333333333333333333333333333", "휴식 모드", "잠깐 쉴 때 은은하게", "FFB86C", 60, 2
    ),
    ActivityModeFixture(
        "mode-44444444444444444444444444444444", "스탠딩 모드", "서서 일할 때", "FFFFFF", 220, 0
    ),
)


class _ActivityModes:
    def __init__(self, catalog: tuple[ActivityModeFixture, ...] = ACTIVITY_MODE_CATALOG) -> None:
        self.catalog = catalog
        self.calls: list[str] = []

    async def list_effective_modes(self, profile_id: str) -> list[ActivityModeFixture]:
        self.calls.append(profile_id)
        return list(self.catalog)


@dataclass(slots=True)
class EvalFixtures:
    """평가 turn 하나의 context와, 무엇이 실제로 실행됐는지 볼 참조들."""

    context: SmartDeskAgentContext
    sessions: CurrentUserSessionManager
    turns: AssistantTurnStore
    automation: _Automation
    wled: _Wled
    memory: _Memory
    tilt: _Tilt
    activity_modes: _ActivityModes
    users: CurrentUserSessionService = field(repr=False)

    async def close(self) -> None:
        await self.turns.stop()
        await self.sessions.stop()


async def build_eval_fixtures(
    *, tilt_level_range: tuple[int, int] = (0, 3), profile_id: str = "profile-eval"
) -> EvalFixtures:
    """등록 사용자 turn context 하나를 새로 만든다.

    평가 case마다 새로 만든다. 하나를 재사용하면 앞 발화의 SDK session 기록이
    다음 발화에 남는데, 실제 음성 turn은 Wake Word마다 새 ``VoicePipeline``
    실행이라 그런 누적이 없다.
    """

    users = CurrentUserSessionService()
    sessions = CurrentUserSessionManager(users)
    turns = AssistantTurnStore(users)
    await sessions.start()
    await turns.start()
    selected = await users.select(SessionKind.REGISTERED, profile_id, "eval")
    captured = await sessions.capture()
    turn = await turns.create(selected.session_id, captured.profile_id)
    automation, wled, memory = _Automation(), _Wled(), _Memory()
    # 최저 단계에서 시작하면 "기울기 좀 줄여줘"류가 물리적으로 불가능해져서,
    # model이 옳게 거절해도 평가에서는 오답으로 보인다. 중간 단계에서 시작한다.
    tilt, activity_modes = _Tilt(level=2), _ActivityModes()
    context = SmartDeskAgentContext(
        turn_context=captured,
        sessions=sessions,
        memory=memory,  # type: ignore[arg-type]
        turns=turns,
        turn_id=turn.turn_id,
        turn_sequence=turn.sequence,
        automation=automation,  # type: ignore[arg-type]
        wled=wled,  # type: ignore[arg-type]
        tilt=tilt,
        activity_modes=activity_modes,
        tilt_level_range=tilt_level_range,
    )
    return EvalFixtures(
        context=context,
        sessions=sessions,
        turns=turns,
        automation=automation,
        wled=wled,
        memory=memory,
        tilt=tilt,
        activity_modes=activity_modes,
        users=users,
    )
