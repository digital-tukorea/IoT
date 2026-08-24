"""
send_test_command.py
실제 앱/서버 없이, MQTT로 이동/모드 명령을 수동으로 보내서
main_controller.py가 제대로 라우팅하는지 확인하는 테스트 도구.

사용법:
  python tools/send_test_command.py move forward 60
  python tools/send_test_command.py move stop
  python tools/send_test_command.py mode stop
  python tools/send_test_command.py mode start
"""

import sys
import json

import paho.mqtt.client as mqtt

sys.path.insert(0, ".")
from config import CONFIG, resolve_topics


def main():
    if len(sys.argv) < 2:
        print("사용법: python send_test_command.py <move|mode> [args...]")
        print("  예) python send_test_command.py move forward 60")
        print("  예) python send_test_command.py mode stop")
        return

    cfg = resolve_topics(CONFIG)
    command_type = sys.argv[1]

    if command_type == "move":
        action = sys.argv[2] if len(sys.argv) > 2 else "forward"
        speed = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        topic = cfg["move_command_topic"]
        payload = {"action": action, "speed": speed}

    elif command_type == "mode":
        action = sys.argv[2] if len(sys.argv) > 2 else "start"
        topic = cfg["mode_command_topic"]
        payload = {"action": action}

    else:
        print(f"알 수 없는 명령 종류: {command_type} (move 또는 mode만 지원)")
        return

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="test-command-sender")
    if cfg["mqtt_use_auth"]:
        client.username_pw_set(cfg["mqtt_username"], cfg["mqtt_password"])
    client.connect(cfg["mqtt_broker"], cfg["mqtt_port"], keepalive=10)

    message = json.dumps(payload, ensure_ascii=False)
    client.publish(topic, message, qos=1)
    print(f"[전송 완료] topic={topic}")
    print(f"[전송 완료] payload={message}")

    client.disconnect()


if __name__ == "__main__":
    main()
