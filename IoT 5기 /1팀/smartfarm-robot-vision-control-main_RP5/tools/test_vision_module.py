"""
test_vision_module.py
카메라 없이, 저장된 이미지 파일 하나로 vision_module.py의 탐지/분석 로직만 테스트한다.

사용법:
  python tools/test_vision_module.py path/to/test_image.jpg [zone_id]
"""

import sys

import cv2

sys.path.insert(0, ".")
from config import CONFIG, CROP_COLOR_PROFILES
from modules.vision_module import VisionModule


def main():
    if len(sys.argv) < 2:
        print("사용법: python test_vision_module.py <이미지경로> [zone_id]")
        return

    image_path = sys.argv[1]
    zone_id = sys.argv[2] if len(sys.argv) > 2 else "test_zone"

    frame = cv2.imread(image_path)
    if frame is None:
        print(f"❌ 이미지를 읽을 수 없습니다: {image_path}")
        return

    print("[초기화] 비전 모듈 로드 중... (YOLO 모델 로딩에 시간이 걸릴 수 있음)")
    vision = VisionModule(CONFIG, CROP_COLOR_PROFILES)

    print(f"[탐지 실행] zone_id={zone_id}")
    annotated_frame, detections = vision.detect(frame, zone_id=zone_id)

    if not detections:
        print("탐지된 객체가 없습니다. conf_threshold를 낮추거나 다른 이미지로 시도해보세요.")
    else:
        for i, d in enumerate(detections, start=1):
            print(f"  [{i}] crop_id={d.crop_id} track_id={d.track_id} 신뢰도={d.confidence:.2f} "
                  f"익음도={d.ripeness_percent} (평균={d.ripeness_percent_smoothed}) 익음여부={d.is_ripe} "
                  f"병해충(YOLO)={'유' if d.disease_detected else '무'} "
                  f"색상급변경보={'유' if d.color_change_alert else '무'} "
                  f"(disease_type={d.disease_type}, trigger={d.diagnosis_trigger})")

    output_path = "vision_test_result.jpg"
    cv2.imwrite(output_path, annotated_frame)
    print(f"\n결과 이미지 저장됨: {output_path} (박스/라벨이 그려진 이미지 확인 가능)")


if __name__ == "__main__":
    main()
