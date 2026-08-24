"""DB 모듈

SQLite(local_gallery.db)에 대한 모든 읽기/쓰기를 이 모듈에 모아둔다.
테이블은 3개다.
- images: 옷장 슬롯(1~10번)별로 저장된 사진 경로와 Gemini 설명
- app_context: 앱이 보내주는 날씨/일정(캘린더) 컨텍스트 기록
- sent_recommendations: /api/recommend가 이미 내보낸 옷 ID 기록
  (같은 옷이 연속으로 추천되는 것을 막기 위한 이력)
"""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from config import DATABASE_PATH, parse_int


def get_connection() -> sqlite3.Connection:
    """새 SQLite 연결을 연다. 스레드마다 별도 연결을 쓰므로 매번 새로 연다."""
    connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    """앱 시작 시 한 번 호출되어 필요한 테이블을 생성한다(이미 있으면 무시)."""
    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY,
                    filepath TEXT,
                    description TEXT,
                    created_at REAL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS app_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL,
                    weather TEXT,
                    aqi INTEGER,
                    latitude REAL,
                    longitude REAL,
                    schedule TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sent_recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_id INTEGER NOT NULL,
                    sent_at REAL NOT NULL
                )
                """
            )
            connection.commit()
    except Exception:
        pass


# ---- images 테이블 (옷장 인벤토리) ----

def fetch_closet_inventory() -> list[dict[str, Any]]:
    """옷장에 저장된 전체 항목(id, 파일 경로, 설명, 생성 시각)을 가져온다."""
    try:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT id, filepath, description, created_at FROM images ORDER BY id ASC"
            ).fetchall()
        return [dict(row) for row in rows]
    except Exception:
        return []


def upsert_image_record(image_id: int, file_path: str, description: str) -> None:
    """옷장 슬롯 image_id의 사진/설명을 저장(이미 있으면 덮어쓰기)한다."""
    timestamp = time.time()
    try:
        with get_connection() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO images (id, filepath, description, created_at) VALUES (?, ?, ?, ?)",
                (image_id, file_path, description, timestamp),
            )
            connection.commit()
    except Exception:
        pass


# ---- app_context 테이블 (날씨/캘린더 컨텍스트) ----

def save_context_record(context_data: dict[str, Any]) -> None:
    """앱이 보내온 날씨/위치/일정 정보를 새 기록으로 저장한다."""
    timestamp = time.time()
    try:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO app_context (created_at, weather, aqi, latitude, longitude, schedule) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    timestamp,
                    str(context_data.get("weather", "")),
                    parse_int(str(context_data.get("aqi", "0")), 0),
                    float(context_data.get("latitude", 0.0)),
                    float(context_data.get("longitude", 0.0)),
                    json.dumps(context_data.get("schedule", []), ensure_ascii=False),
                ),
            )
            connection.commit()
    except Exception:
        pass


def fetch_latest_context() -> dict[str, Any] | None:
    """가장 최근에 저장된 날씨/일정 컨텍스트 한 건을 가져온다."""
    try:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT weather, aqi, latitude, longitude, schedule, created_at FROM app_context ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None

        schedule_value = row["schedule"]
        try:
            schedule = json.loads(schedule_value) if schedule_value else []
        except Exception:
            schedule = schedule_value

        return {
            "weather": row["weather"],
            "aqi": row["aqi"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "schedule": schedule,
            "created_at": row["created_at"],
        }
    except Exception:
        return None


# ---- sent_recommendations 테이블 (추천 발송 이력) ----

def fetch_sent_recommendation_ids() -> set[int]:
    """지금까지 한 번이라도 추천으로 내보낸 옷 ID 목록을 가져온다."""
    try:
        with get_connection() as connection:
            rows = connection.execute("SELECT DISTINCT image_id FROM sent_recommendations").fetchall()
        return {row["image_id"] for row in rows}
    except Exception:
        return set()


def clear_sent_recommendations() -> None:
    """추천 발송 이력을 전부 지운다(옷장 전체를 한 바퀴 다 보낸 뒤 순환 초기화용)."""
    try:
        with get_connection() as connection:
            connection.execute("DELETE FROM sent_recommendations")
            connection.commit()
    except Exception:
        pass


def record_sent_recommendations(image_ids: list[int]) -> None:
    """방금 추천으로 내보낸 옷 ID들을 이력에 남긴다."""
    if not image_ids:
        return
    timestamp = time.time()
    try:
        with get_connection() as connection:
            connection.executemany(
                "INSERT INTO sent_recommendations (image_id, sent_at) VALUES (?, ?)",
                [(image_id, timestamp) for image_id in image_ids],
            )
            connection.commit()
    except Exception:
        pass
