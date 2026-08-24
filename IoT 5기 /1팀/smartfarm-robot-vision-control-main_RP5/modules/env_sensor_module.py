"""
env_sensor_module.py
라즈베리파이에 직접 연결된 온습도 센서(DHT11/DHT22)를 읽는다.

설치:
  pip install adafruit-circuitpython-dht gpiod --break-system-packages

배선 (DHT11/DHT22 공통, 3핀 모듈 기준):
  VCC -> 3.3V 또는 5V (모듈 사양에 맞게)
  GND -> GND
  DATA -> config.py의 env_sensor_gpio_pin에 지정한 GPIO 핀
  (권장: DATA-VCC 사이에 4.7~10kΩ 풀업 저항 - 브레이크아웃 모듈은 보통 내장되어 있음)
"""

import time


class EnvSensorModule:
    def __init__(self, config):
        self.config = config
        self.sensor = None
        self._last_read_time = 0
        self._min_read_interval_sec = 2  # DHT 센서 자체의 하드웨어 한계 (2초 미만 재측정 불가)

        self._init_sensor()

    def _init_sensor(self):
        try:
            import board
            import adafruit_dht

            pin_name = self.config.get("env_sensor_gpio_pin", "D4")
            sensor_type = self.config.get("env_sensor_type", "DHT22")

            pin = getattr(board, pin_name)
            if sensor_type == "DHT11":
                self.sensor = adafruit_dht.DHT11(pin)
            else:
                self.sensor = adafruit_dht.DHT22(pin)

            print(f"✅ [EnvSensor] {sensor_type} 센서 초기화 완료 (핀: {pin_name})")

        except ImportError:
            print("  [경고] adafruit-circuitpython-dht 미설치: "
                  "pip install adafruit-circuitpython-dht libgpiod --break-system-packages")
            self.sensor = None
        except (NotImplementedError, AttributeError, RuntimeError) as e:
            print(f"  [경고] 온습도 센서 초기화 실패: {e}")
            self.sensor = None

    def read(self):
        """
        (temperature_c, humidity_percent) 튜플을 반환한다.
        읽기 실패(DHT 센서 특성상 흔함, 정상적인 현상) 시 (None, None) 반환.
        너무 잦은 호출은 자동으로 건너뛴다 (하드웨어 한계).
        """
        if self.sensor is None:
            return None, None

        now = time.time()
        if now - self._last_read_time < self._min_read_interval_sec:
            return None, None
        self._last_read_time = now

        try:
            temperature_c = self.sensor.temperature
            humidity_percent = self.sensor.humidity
            if temperature_c is None or humidity_percent is None:
                return None, None
            return temperature_c, humidity_percent
        except RuntimeError as e:
            # DHT 계열 센서는 타이밍 특성상 읽기 실패가 자주 발생한다 - 정상.
            # main_controller가 몇 초 뒤 다시 시도하므로 별도 조치 불필요.
            print(f"  [EnvSensor] 읽기 실패(정상적인 현상, 재시도 예정): {e}")
            return None, None
        except Exception as e:
            print(f"  [EnvSensor 경고] 예상치 못한 오류: {e}")
            return None, None

    def close(self):
        if self.sensor is not None:
            try:
                self.sensor.exit()
            except Exception:
                pass
