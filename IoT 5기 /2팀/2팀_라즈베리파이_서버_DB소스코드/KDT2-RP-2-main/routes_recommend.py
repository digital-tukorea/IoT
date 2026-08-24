"""추천 라우터

오늘 입을 옷 3벌을 골라주는 엔드포인트들과, 특정 슬롯을 레일로
보내달라는 /api/send_id를 담당한다. 실제 선택 로직은 recommendation
모듈에, 전송은 mqtt_client 모듈에 있고 여기서는 그것들을 엮어서
HTTP 응답으로 만든다.

/api/recommend는 고른 3벌을 곧바로 MQTT로 레일에 전송하고
sent_recommendations 테이블에 기록한다. 그래서 다음 호출에서는 이미
보낸 옷을 자동으로 제외하며, 옷장 전체를 한 바퀴 다 보내면 기록을
비우고 처음부터 다시 순환한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import MQTT_BROKER_HOST, MQTT_TOPIC, VALID_QR_IDS
from database import (
    clear_sent_recommendations,
    fetch_closet_inventory,
    fetch_latest_context,
    fetch_sent_recommendation_ids,
    get_connection,
    record_sent_recommendations,
)
from image_analysis import build_inventory_analysis
from mqtt_client import publish_slot_id
from recommendation import choose_fallback_ids, get_recommendation_ids, get_weather_info, parse_exclude_ids

router = APIRouter()


def get_image_download_url(request: Request, image_id: int) -> str:
    """옷 ID에 해당하는 실제 저장 파일명으로 다운로드 URL을 만든다."""
    try:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT filepath FROM images WHERE id = ?",
                (image_id,),
            ).fetchone()
        if not row or not row["filepath"]:
            return f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/images/download/qr_{image_id}.jpg"
        filename = Path(str(row["filepath"])).name
        return f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/images/download/{filename}"
    except Exception:
        return f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/images/download/qr_{image_id}.jpg"


@router.api_route("/api/send_id/{image_id}", methods=["GET", "POST"])
def send_image_id(image_id: int) -> JSONResponse:
    if image_id not in VALID_QR_IDS:
        raise HTTPException(status_code=400, detail="Image ID must be between 1 and 10")

    published = publish_slot_id(image_id)
    if not published:
        raise HTTPException(status_code=502, detail="Failed to publish to MQTT broker")

    return JSONResponse(
        content={
            "ok": True,
            "id": image_id,
            "topic": MQTT_TOPIC,
            "broker": MQTT_BROKER_HOST,
        }
    )


@router.get("/api/recommend/context")
def recommend_from_context(request: Request, exclude_ids: list[str] = Query(default=[])) -> JSONResponse:
    latest_context = fetch_latest_context()
    if latest_context is None:
        raise HTTPException(status_code=404, detail="No context saved yet")

    inventory = fetch_closet_inventory()
    if not inventory:
        return JSONResponse(content={"recommendations": []})

    weather_info = {
        "temperature_c": 0,
        "conditions": latest_context.get("weather", "Unknown"),
    }
    excluded = parse_exclude_ids(exclude_ids)
    selected_ids = get_recommendation_ids(inventory, weather_info, latest_context, excluded)

    recommendations = []
    for image_id in selected_ids:
        recommendations.append(
            {
                "id": image_id,
                "download_url": get_image_download_url(request, image_id),
            }
        )

    return JSONResponse(
        content={
            "context": latest_context,
            "recommendations": recommendations,
        }
    )


class ExcludeRecommendationPayload(BaseModel):
    exclude_ids: list[int]


@router.get("/api/recommend/different")
def recommend_different(request: Request, exclude_ids: list[str] = Query(default=[])) -> JSONResponse:
    latest_context = fetch_latest_context()
    inventory = fetch_closet_inventory()
    if not inventory:
        return JSONResponse(content={"recommendations": []})

    weather_info = {
        "temperature_c": 0,
        "conditions": latest_context.get("weather", "Unknown") if latest_context else "Unknown",
    }
    excluded = parse_exclude_ids(exclude_ids)
    selected_ids = get_recommendation_ids(inventory, weather_info, latest_context, excluded)

    recommendations = []
    for image_id in selected_ids:
        recommendations.append(
            {
                "id": image_id,
                "download_url": get_image_download_url(request, image_id),
            }
        )

    return JSONResponse(content={"recommendations": recommendations})


@router.post("/api/recommend/different")
def recommend_different_post(request: Request, payload: ExcludeRecommendationPayload) -> JSONResponse:
    latest_context = fetch_latest_context()
    inventory = fetch_closet_inventory()
    if not inventory:
        return JSONResponse(content={"recommendations": []})

    weather_info = {
        "temperature_c": 0,
        "conditions": latest_context.get("weather", "Unknown") if latest_context else "Unknown",
    }
    excluded = set(payload.exclude_ids or [])
    selected_ids = get_recommendation_ids(inventory, weather_info, latest_context, excluded)

    recommendations = []
    for image_id in selected_ids:
        recommendations.append(
            {
                "id": image_id,
                "download_url": get_image_download_url(request, image_id),
            }
        )

    return JSONResponse(content={"recommendations": recommendations})


@router.get("/api/recommend/analyze")
def recommend_with_analysis(request: Request, exclude_ids: list[str] = Query(default=[])) -> JSONResponse:
    inventory = fetch_closet_inventory()
    if not inventory:
        return JSONResponse(content={"recommendations": []})

    excluded = parse_exclude_ids(exclude_ids)
    filtered_inventory = [item for item in inventory if item.get("id") not in excluded]
    if not filtered_inventory:
        return JSONResponse(content={"recommendations": []})

    analyses = build_inventory_analysis(filtered_inventory)

    if not analyses:
        selected_ids = []
    else:
        def score_analysis_item(item: dict[str, Any]) -> int:
            score = len(item.get("yolo_labels", [])) * 2
            summary = str(item.get("summary", ""))
            score += min(5, max(0, len(summary.split())))
            if "clothing" in summary.lower() or "톤" in summary.lower():
                score += 1
            return score

        scores = [score_analysis_item(item) for item in analyses]
        analyses.sort(key=score_analysis_item, reverse=True)

        if len(analyses) > 3 and min(scores) == max(scores):
            selected_ids = choose_fallback_ids([item["id"] for item in analyses], fetch_latest_context())
        else:
            selected_ids = [item["id"] for item in analyses[:3]]

        if len(selected_ids) < 3:
            fallback_ids = get_recommendation_ids(filtered_inventory, get_weather_info(), fetch_latest_context())
            for image_id in fallback_ids:
                if image_id not in selected_ids and len(selected_ids) < 3:
                    selected_ids.append(image_id)

    recommendations = []
    for image_id in selected_ids:
        analysis_item = next((item for item in analyses if item["id"] == image_id), None)
        recommendations.append(
            {
                "id": image_id,
                "download_url": get_image_download_url(request, image_id),
                "yolo_labels": analysis_item["yolo_labels"] if analysis_item else [],
                "summary": analysis_item["summary"] if analysis_item else "No analysis available",
            }
        )

    return JSONResponse(
        content={
            "recommendations": recommendations,
            "analysis_count": len(analyses),
        }
    )


@router.get("/api/recommend")
def recommend(request: Request) -> JSONResponse:
    weather_info = get_weather_info()
    latest_context = fetch_latest_context()
    inventory = fetch_closet_inventory()

    inventory_ids = {item["id"] for item in inventory}
    already_sent = fetch_sent_recommendation_ids()
    reset_cycle = bool(inventory_ids) and inventory_ids.issubset(already_sent)
    if reset_cycle:
        clear_sent_recommendations()
        already_sent = set()

    selected_ids = get_recommendation_ids(inventory, weather_info, latest_context, already_sent)

    response_payload = []
    for image_id in selected_ids:
        published = publish_slot_id(image_id)
        response_payload.append(
            {
                "id": image_id,
                "download_url": get_image_download_url(request, image_id),
                "published": published,
            }
        )
    record_sent_recommendations(selected_ids)

    return JSONResponse(
        content=response_payload,
        headers={"X-Cycle-Reset": "true" if reset_cycle else "false"},
    )
