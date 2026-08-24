"""추천 선택 모듈

옷장 인벤토리 중 오늘 입을 옷 3벌을 고르는 로직을 담당한다. 각 옷의
description(Gemini가 촬영 시 만들어둔 설명)과 날씨/캘린더 컨텍스트를
Gemini에게 함께 보여주고 3개 ID를 받아온다. 우선순위는 캘린더 일정이
1순위, 날씨가 2순위다. Gemini를 쓸 수 없거나 응답이 이상하면
choose_fallback_ids()로 결정적인 순환 선택을 한다.
"""

from __future__ import annotations

import json
from typing import Any

from config import logger
from gemini_service import GEMINI_MODEL_CANDIDATES, get_gemini_client

try:
    from google import genai
except Exception:
    genai = None


def get_weather_info() -> dict[str, Any]:
    """현재 날씨 정보. (실제 기상 API 연동 전까지의 고정값)"""
    return {
        "temperature_c": 10,
        "conditions": "Windy and Chilly",
    }


def parse_exclude_ids(exclude_ids: str | list[str] | None) -> set[int]:
    """제외할 ID 목록을 파싱한다.

    콤마로 구분된 문자열(?exclude_ids=2,7,8)과, 같은 이름을 반복한 쿼리
    파라미터(?exclude_ids=2&exclude_ids=7&exclude_ids=8, 예: Retrofit이
    보내는 형태) 둘 다 지원한다. 앱이 반복 파라미터로 보내는데 이걸
    str 하나로만 받으면 FastAPI가 마지막 값만 남기고 나머지를 버려서,
    같은 옷 2개가 계속 재추천되는 버그가 있었다.
    """
    if not exclude_ids:
        return set()

    raw_values = exclude_ids if isinstance(exclude_ids, list) else [exclude_ids]

    results: set[int] = set()
    for raw_value in raw_values:
        for part in str(raw_value).split(","):
            try:
                results.add(int(part.strip()))
            except Exception:
                continue
    return results


def strip_json_wrappers(raw_text: str) -> str:
    """Gemini 응답에 섞여 나오는 ```json ... ``` 코드블록 표기를 제거한다."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def normalize_three_ids(candidate_ids: list[int]) -> list[int]:
    """중복을 제거하고, 부족하면 앞에서부터 다시 채워 정확히 3개로 맞춘다."""
    unique_ids: list[int] = []
    for image_id in candidate_ids:
        if image_id not in unique_ids:
            unique_ids.append(image_id)

    if not unique_ids:
        return []

    index = 0
    while len(unique_ids) < 3:
        unique_ids.append(unique_ids[index % len(unique_ids)])
        index += 1

    return unique_ids[:3]


def choose_fallback_ids(inventory_ids: list[int], context: dict[str, Any] | None = None) -> list[int]:
    """Gemini 없이 결정적으로 3개를 고르는 대체 로직.

    컨텍스트(날씨/위치/일정)를 시드로 시작 위치를 정하고, 그 지점부터
    일정 간격으로 건너뛰며 골라 최대한 다양한 조합이 나오게 한다.
    """
    if not inventory_ids:
        return []

    if len(inventory_ids) <= 3:
        return inventory_ids.copy()

    start = 0
    if context is not None:
        seed_text = (
            f"{context.get('weather', '')}|{context.get('aqi', '')}|"
            f"{context.get('latitude', '')}|{context.get('longitude', '')}|"
            f"{json.dumps(context.get('schedule', []), ensure_ascii=False)}"
        )
        start = abs(hash(seed_text)) % len(inventory_ids)

    step = max(1, len(inventory_ids) // 3)
    selected: list[int] = []
    idx = start

    while len(selected) < 3:
        candidate = inventory_ids[idx]
        if candidate not in selected:
            selected.append(candidate)
        idx = (idx + step) % len(inventory_ids)

    return selected


def get_recommendation_ids(
    inventory: list[dict[str, Any]],
    weather_info: dict[str, Any],
    context: dict[str, Any] | None = None,
    exclude_ids: set[int] | None = None,
) -> list[int]:
    """오늘 추천할 옷 3벌의 ID를 고른다. exclude_ids는 후보에서 완전히 제외한다."""
    if exclude_ids:
        inventory = [item for item in inventory if item["id"] not in exclude_ids]
    inventory_ids = [item["id"] for item in inventory]

    if not inventory_ids:
        return []

    if genai is None:
        return choose_fallback_ids(inventory_ids, context)

    context_description = ""
    if context is not None:
        context_description = (
            f"Current app context:\n"
            f"AQI: {context.get('aqi')}\n"
            f"Location: {context.get('latitude')}, {context.get('longitude')}\n"
            f"Schedule: {json.dumps(context.get('schedule', []), ensure_ascii=False)}\n"
        )

    prompt = (
        "You are a smart closet stylist. Each inventory item has a `description` written by "
        "an image model -- use those descriptions (garment type, color, material, formality) as "
        "your primary basis for judging fit. Select exactly 3 item IDs, weighing two factors in "
        "this priority order: (1) the user's calendar/schedule below, if any, is the primary "
        "signal -- prefer items whose formality/style matches the day's events (e.g. formal wear "
        "for a meeting, athletic wear for exercise); (2) once schedule fit is satisfied, use the "
        "current weather as a secondary filter (e.g. avoid short sleeves in cold weather). "
        f"Current outdoor weather: {weather_info['temperature_c']}°C, {weather_info['conditions']}.\n"
        f"{context_description}"
        "Return ONLY a raw JSON array of integers containing the selected IDs. Do not include markdown wraps or additional conversational text.\n\n"
        f"Inventory: {json.dumps(inventory, ensure_ascii=False)}"
    )

    try:
        client = get_gemini_client()
        if client is None:
            raise RuntimeError("Gemini client unavailable")

        for model_name in GEMINI_MODEL_CANDIDATES:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                raw_text = getattr(response, "text", "") or ""
                cleaned = strip_json_wrappers(raw_text)
                parsed = json.loads(cleaned)
                if not isinstance(parsed, list):
                    raise ValueError("Gemini response is not a list")

                selected_ids: list[int] = []
                for value in parsed:
                    try:
                        parsed_value = int(value)
                        if parsed_value not in selected_ids:
                            selected_ids.append(parsed_value)
                    except Exception:
                        continue

                valid_ids = {item["id"] for item in inventory}
                selected_ids = [value for value in selected_ids if value in valid_ids]

                if len(selected_ids) >= 3:
                    return normalize_three_ids(selected_ids)
            except Exception as exc:
                logger.warning("Gemini recommendation failed on %s: %s", model_name, exc)
                continue
    except Exception:
        pass

    return choose_fallback_ids(inventory_ids, context)
