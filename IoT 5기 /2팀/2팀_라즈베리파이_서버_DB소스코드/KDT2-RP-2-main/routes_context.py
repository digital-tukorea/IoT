"""날씨/캘린더 컨텍스트 라우터

앱이 현재 날씨와 사용자 일정(캘린더)을 보내면 저장해 두고, 추천 로직이
이 값을 읽어서 옷을 고를 때 참고한다.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database import fetch_latest_context, save_context_record

router = APIRouter()


class ContextPayload(BaseModel):
    weather: str
    aqi: int
    latitude: float
    longitude: float
    schedule: Any


@router.post("/api/context")
def receive_context(context: ContextPayload) -> JSONResponse:
    try:
        save_context_record(context.dict())
        return JSONResponse(content={"ok": True, "message": "Context saved"})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/context")
def get_context() -> JSONResponse:
    try:
        latest = fetch_latest_context()
        if latest is None:
            raise HTTPException(status_code=404, detail="No context saved yet")
        return JSONResponse(content=latest)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
