"""옷장 인벤토리 라우터

DB에 저장된 옷 목록 조회, 사진 파일 다운로드, 수동 업로드(카메라 자동
인식이 아니라 앱에서 직접 사진을 올리는 경우)를 담당한다.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response

from config import IMAGE_DIR, VALID_QR_IDS
from database import fetch_closet_inventory, upsert_image_record
from gemini_service import analyze_image_with_gemini

router = APIRouter()


@router.get("/api/closet")
def list_closet_items() -> JSONResponse:
    try:
        inventory = fetch_closet_inventory()
        return JSONResponse(content=inventory)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/closet/{image_id}")
def get_closet_item(image_id: int) -> JSONResponse:
    try:
        inventory = fetch_closet_inventory()
        for item in inventory:
            if int(item.get("id", -1)) == image_id:
                return JSONResponse(content=item)
        raise HTTPException(status_code=404, detail="Item not found")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/images/download/{filename}")
def download_image(filename: str) -> Response:
    try:
        safe_name = Path(filename).name
        file_path = IMAGE_DIR / safe_name

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Image not found")

        media_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        return Response(content=file_path.read_bytes(), media_type=media_type)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Image not found")


@router.post("/api/upload/{image_id}")
def upload_image(image_id: int, file: UploadFile = File(...)) -> JSONResponse:
    if image_id not in VALID_QR_IDS:
        raise HTTPException(status_code=400, detail="Image ID must be between 1 and 10")

    if file.content_type not in {"image/jpeg", "image/jpg", "image/png"}:
        raise HTTPException(status_code=400, detail="File must be a JPG or PNG image")

    try:
        file_bytes = file.file.read()
        extension = ".jpg" if file.content_type != "image/png" else ".png"
        image_path = IMAGE_DIR / f"qr_{image_id}{extension}"
        with open(image_path, "wb") as out_file:
            out_file.write(file_bytes)

        description = analyze_image_with_gemini(image_path) or ""
        upsert_image_record(image_id, str(image_path), description)
        return JSONResponse(content={"id": image_id, "filepath": str(image_path), "description": description})
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to save uploaded image")
