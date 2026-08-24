"""Gemini 연동 모듈

Google Gemini API 클라이언트 생성과, 옷 사진 한 장을 보고 자연어 설명을
만들어내는 기능을 담당한다. DB의 description 컬럼은 이 모듈이 생성한
문장으로만 채워지며(다른 모듈에서 임의의 대체 문구를 넣지 않는다),
Gemini 호출이 실패하면 항상 None을 반환해 호출한 쪽이 "설명 없음"을
명확히 구분할 수 있게 한다.
"""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Any

from config import logger

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None

# 두 함수(이미지 설명 생성, 추천 후보 선택)가 공유하는 모델 후보 목록.
# 첫 번째가 실패하면(사용 중단 등) 다음 후보로 자동 재시도한다.
GEMINI_MODEL_CANDIDATES = ("gemini-3.6-flash", "gemini-flash-latest")


def get_gemini_client() -> Any | None:
    """API 키 또는 GOOGLE_APPLICATION_CREDENTIALS로 Gemini 클라이언트를 만든다."""
    if genai is None:
        return None

    api_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
    google_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

    try:
        if api_key:
            logger.info("Initializing Gemini client with API key")
            return genai.Client(api_key=api_key)

        if google_creds:
            logger.info("Initializing Gemini client with GOOGLE_APPLICATION_CREDENTIALS=%s", google_creds)
            return genai.Client()

        logger.warning("No Gemini API key or Google credentials available")
        return None
    except Exception as exc:
        logger.warning("Failed to initialize Gemini client: %s", exc)
        return None


def analyze_image_with_gemini(image_path: Path) -> str | None:
    """옷 사진 한 장을 Gemini로 분석해 한국어 한 문장 설명을 만든다.

    Gemini를 쓸 수 없거나 모든 모델 시도가 실패하면 None을 반환한다(가짜
    설명이나 플레이스홀더 문구를 대신 채워넣지 않는다).
    """
    prompt = (
        "당신은 이미지 기반 패션 어시스턴트입니다. 이 옷 사진을 보고 한 문장으로 간결하게 설명하세요. "
        "옷 종류, 대표 색상, 예상 소재감, 추천 착용 상황을 포함하고, 캐주얼/스포티/포멀 느낌이 명확하면 언급하세요. "
        "응답은 반드시 한국어로 자연스럽게 작성하고, 여분의 해설이나 코드 블록 없이 한 문장으로만 작성하세요."
    )

    if genai is None or types is None:
        return None

    try:
        client = get_gemini_client()
        if client is None:
            raise RuntimeError("Gemini client unavailable")

        image_bytes = image_path.read_bytes()
        image_mime_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=image_mime_type)

        for model_name in GEMINI_MODEL_CANDIDATES:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt, image_part],
                )
                text = getattr(response, "text", None)
                if text:
                    cleaned_text = text.strip()
                    if cleaned_text.startswith("```") and cleaned_text.endswith("```"):
                        cleaned_text = cleaned_text.strip("`")
                    if len(cleaned_text) > 5:
                        return cleaned_text
            except Exception as exc:
                logger.warning("Gemini image analysis failed for %s on %s: %s", image_path, model_name, exc)
                continue
    except Exception as exc:
        logger.warning("Gemini image analysis failed for %s: %s", image_path, exc)

    return None
