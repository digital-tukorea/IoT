import os
import asyncio
import logging
import aiomysql
import requests
from datetime import datetime
import pytz
import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense
import matplotlib.pyplot as plt
import io
import time
from typing import Optional, List
import aiohttp  # 추가된 부분

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 민감한 정보 직접 할당 (플레이스홀더 사용)
TOKEN = '7481408909:AAEHsa9t5WPYLJYC_z68QBnm1S5NpQEoV7I'  # 실제 토큰으로 변경하세요
CHAT_ID = '7264419497'           # 실제 채팅 ID로 변경하세요

# 기타 설정
DATA_URL = 'http://34.64.139.72:5000/data'
MYSQL_HOST = '34.64.249.216'        # 실제 MySQL 호스트로 변경하세요
MYSQL_USER = 'root'        # 실제 MySQL 사용자명으로 변경하세요
MYSQL_PASSWORD = 'iotiot123'  # 실제 MySQL 비밀번호로 변경하세요
MYSQL_DB = 'final_data'

# 상수 정의
DATA_THRESHOLD = 6   # 피로도 예측을 위한 최소 데이터 수 (1분 동안 수집된 데이터 수)
MAX_DATA_LENGTH = 100
TEMP_ALERT_INTERVAL = 3600  # 1시간
SHOCK_THRESHOLD = 3  # 이 값은 더 이상 사용되지 않을 수 있습니다.
TEMP_THRESHOLD = 30
HUMIDITY_THRESHOLD = 70
GAS_THRESHOLD = 100
ALERT_COOLDOWN = 600  # 10분

MODEL_PATH = "fatigue_model.h5"
SCALER_PATH = "scaler.save"

class FatigueMonitor:
    def __init__(self):
        self.data_history: List[np.ndarray] = []
        self.last_temp_alert_time = 0
        self.last_alert_times = {}  # 알림 종류별 마지막 전송 시간
        self.model = None
        self.scaler = StandardScaler()
        self.db_pool = None
        self.last_fatigue_predict_time = time.time() - 60  # 처음 실행 시 바로 예측하도록 설정

        # 이전 x, y, z 값을 저장하기 위한 변수 초기화
        self.prev_x = None
        self.prev_y = None
        self.prev_z = None

        # 모델 및 스케일러 로드 또는 초기화
        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            try:
                self.model = load_model(MODEL_PATH)
                self.scaler = joblib.load(SCALER_PATH)
                logger.info("모델과 스케일러를 로드하였습니다.")
            except Exception as e:
                logger.error(f"모델 로드 실패: {e}")
                self.initialize_model()
        else:
            logger.info("모델이 존재하지 않습니다. 새로 초기화합니다.")
            self.initialize_model()

    def initialize_model(self):
        # 간단한 모델 초기화 (데이터가 부족하거나 동일한 경우에도 예측 가능하도록)
        self.model = Sequential()
        self.model.add(Dense(1, input_shape=(9,)))  # 입력 차원을 새로운 데이터에 맞게 조정
        self.model.compile(loss='mean_squared_error', optimizer='adam')
        self.scaler = StandardScaler()

    async def init_db(self):
        try:
            self.db_pool = await aiomysql.create_pool(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                db=MYSQL_DB
            )
            logger.info("데이터베이스 연결 성공")
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")

    async def fetch_data(self) -> Optional[dict]:
        try:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, self.fetch_data_sync)
            return data
        except Exception as e:
            logger.error(f"데이터 수신 오류: {e}")
            return None

    def fetch_data_sync(self) -> Optional[dict]:
        try:
            response = requests.get(DATA_URL)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"데이터 수신: {data}")
                return data
            else:
                logger.error(f"데이터 수신 실패, 상태 코드: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"데이터 수신 오류: {e}")
            return None

    async def send_message(self, message: str):
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            payload = {
                'chat_id': CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, requests.post, url, payload)
            if response.status_code == 200:
                logger.info("메시지 전송 성공")
            else:
                logger.error(f"메시지 전송 실패: {response.status_code}, {response.text}")
        except Exception as e:
            logger.error(f"메시지 전송 중 예외 발생: {e}")

    async def send_plot(self, data: List[float]):
        try:
            logger.info("그래프 생성 시작")
            plt.figure(figsize=(6, 4))
            plt.plot(data, marker='o', linestyle='-', color='blue')
            plt.title("예상 피로도 추이")
            plt.xlabel("시간")
            plt.ylabel("피로도")
            plt.grid(True)
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=80)
            buf.seek(0)
            plt.close()
            logger.info("그래프 생성 완료")

            url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            buf.name = 'plot.png'  # 파일 이름 설정

            form = aiohttp.FormData()
            form.add_field('chat_id', CHAT_ID)
            form.add_field('photo', buf, filename='plot.png', content_type='image/png')

            # aiohttp를 사용하여 비동기적으로 요청을 보냅니다.
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=form) as response:
                    logger.info(f"텔레그램 응답 코드: {response.status}")
                    if response.status == 200:
                        logger.info("그래프 전송 성공")
                    else:
                        text = await response.text()
                        logger.error(f"그래프 전송 실패: {response.status}, {text}")
        except Exception as e:
            logger.error(f"그래프 전송 중 예외 발생: {e}")

    def categorize_fatigue(self, fatigue_score: float) -> (int, str):
        normalized_fatigue = int(min(max(fatigue_score, 1), 100))
        if normalized_fatigue <= 20:
            return normalized_fatigue, "피로도 매우 낮음"
        elif normalized_fatigue <= 40:
            return normalized_fatigue, "피로도 낮음"
        elif normalized_fatigue <= 60:
            return normalized_fatigue, "피로도 보통"
        elif normalized_fatigue <= 80:
            return normalized_fatigue, "피로도 높음"
        else:
            return normalized_fatigue, "피로도 매우 높음"

    async def save_fatigue_to_db(self, fatigue_score: int):
        if self.db_pool is None:
            logger.error("데이터베이스 연결이 설정되지 않았습니다.")
            return
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = "INSERT INTO fatigability (fatigability, timestamp) VALUES (%s, %s)"
                    await cur.execute(sql, (fatigue_score, datetime.now()))
                    await conn.commit()
                    logger.info(f"피로도 {fatigue_score}를 데이터베이스에 저장하였습니다.")
        except Exception as e:
            logger.error(f"데이터베이스 저장 실패: {e}")

    async def save_fatigue_to_expect_data(self, fatigue_score: int):
        if self.db_pool is None:
            logger.error("데이터베이스 연결이 설정되지 않았습니다.")
            return
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = "INSERT INTO expect_data (fatigability, timestamp) VALUES (%s, %s)"
                    await cur.execute(sql, (fatigue_score, datetime.now()))
                    await conn.commit()
                    logger.info(f"피로도 {fatigue_score}를 expect_data 테이블에 저장하였습니다.")
        except Exception as e:
            logger.error(f"expect_data 테이블에 피로도 저장 실패: {e}")

    async def save_alert_to_db(self, alert_message: str):
        if self.db_pool is None:
            logger.error("데이터베이스 연결이 설정되지 않았습니다.")
            return
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = "INSERT INTO alerts (alert_message, timestamp) VALUES (%s, %s)"
                    await cur.execute(sql, (alert_message, datetime.now()))
                    await conn.commit()
                    logger.info(f"알림을 데이터베이스에 저장하였습니다: {alert_message}")
        except Exception as e:
            logger.error(f"데이터베이스 알림 저장 실패: {e}")

    def detect_anomaly(self, data_point: np.ndarray) -> bool:
        # 동일한 값이 계속 들어와도 이상치로 간주하지 않도록 수정
        return False  # 이상치 탐지를 비활성화합니다.

    def preprocess_data(self) -> np.ndarray:
        data_array = np.array(self.data_history)
        logger.info(f"데이터 스케일링 전 데이터 형태: {data_array.shape}")
        scaled_data = self.scaler.fit_transform(data_array)
        logger.info(f"데이터 스케일링 후 데이터 형태: {scaled_data.shape}")
        return scaled_data

    async def predict_fatigue(self):
        logger.info("predict_fatigue 메서드가 호출되었습니다.")
        if len(self.data_history) >= DATA_THRESHOLD:
            logger.info("데이터가 충분하여 피로도 예측을 시작합니다.")
            try:
                data_array = self.preprocess_data()
                X = np.array(data_array)
                # 간단한 평균을 사용하여 피로도 예측 (데이터가 동일해도 예측 가능)
                predicted_fatigue = np.mean(X)
                fatigue_score, fatigue_level = self.categorize_fatigue(predicted_fatigue)
                logger.info(f"예측된 피로도 점수: {fatigue_score}")

                # 알림 전송
                message = f"예상 피로도: {fatigue_score} (상태: {fatigue_level})입니다."
                await self.send_message(message)
                await self.save_fatigue_to_db(fatigue_score)
                await self.save_fatigue_to_expect_data(fatigue_score)  # 추가된 부분

                # 최근 피로도 추이 그래프 전송
                recent_fatigues = [fatigue_score] * len(X)
                await self.send_plot(recent_fatigues)

                # 데이터 관리
                if len(self.data_history) > MAX_DATA_LENGTH:
                    self.data_history = self.data_history[-MAX_DATA_LENGTH:]
            except Exception as e:
                logger.error(f"피로도 예측 중 예외 발생: {e}")
        else:
            logger.warning("데이터가 충분하지 않아 피로도 예측을 진행할 수 없습니다.")

    def get_seoul_time(self) -> str:
        seoul_tz = pytz.timezone('Asia/Seoul')
        seoul_time = datetime.now(seoul_tz).strftime("%Y-%m-%d %H:%M:%S KST")
        return seoul_time

    async def check_alerts(self, data: dict):
        temperature = data.get('temperature', 0)
        humidity = data.get('humidity', 0)
        gas = data.get('gas', 0)
        dust = data.get('dust', 0)
        uv = data.get('uv', 0)
        # x, y, z 값 가져오기
        x = data.get('x', 0)
        y = data.get('y', 0)
        z = data.get('z', 0)

        current_time = time.time()

        # 온도 알림
        if temperature >= TEMP_THRESHOLD:
            last_alert = self.last_alert_times.get('temperature', 0)
            if current_time - last_alert >= ALERT_COOLDOWN:
                alert_message = f"온도가 {temperature}도입니다. 10분 휴식을 권고합니다."
                await self.send_message(alert_message)
                await self.save_alert_to_db(alert_message)
                self.last_alert_times['temperature'] = current_time

        # 습도 알림
        if humidity >= HUMIDITY_THRESHOLD:
            last_alert = self.last_alert_times.get('humidity', 0)
            if current_time - last_alert >= ALERT_COOLDOWN:
                alert_message = f"습도가 {humidity}%입니다. 너무 습합니다! 환기하세요."
                await self.send_message(alert_message)
                await self.save_alert_to_db(alert_message)
                self.last_alert_times['humidity'] = current_time

        # 가스 농도 알림
        if gas >= GAS_THRESHOLD:
            last_alert = self.last_alert_times.get('gas', 0)
            if current_time - last_alert >= ALERT_COOLDOWN:
                alert_message = f"가스 농도가 {gas}ppm입니다. 위험하니 즉시 지역을 떠나세요!"
                await self.send_message(alert_message)
                await self.save_alert_to_db(alert_message)
                self.last_alert_times['gas'] = current_time

        # 충격 감지 알림 (x, y, z 값 사용)
        if self.prev_x is not None:
            delta_x = abs(x - self.prev_x)
            delta_y = abs(y - self.prev_y)
            delta_z = abs(z - self.prev_z)
            if delta_x != 0 or delta_y != 0 or delta_z != 0:
                # x, y, z 값에 아주 작은 변화라도 있으면 충격으로 간주
                last_alert = self.last_alert_times.get('shock', 0)
                if current_time - last_alert >= ALERT_COOLDOWN:
                    alert_message = "충격이 감지되었습니다. 119에 연락하세요!"
                    await self.send_message(alert_message)
                    await self.save_alert_to_db(alert_message)
                    self.last_alert_times['shock'] = current_time

        # 이전 x, y, z 값 업데이트
        self.prev_x = x
        self.prev_y = y
        self.prev_z = z

        # 먼지 농도 알림 (예시로 추가)
        if dust >= 150:
            last_alert = self.last_alert_times.get('dust', 0)
            if current_time - last_alert >= ALERT_COOLDOWN:
                alert_message = f"먼지 농도가 {dust}입니다. 마스크를 착용하세요!"
                await self.send_message(alert_message)
                await self.save_alert_to_db(alert_message)
                self.last_alert_times['dust'] = current_time

        # 자외선 알림 (예시로 추가)
        if uv >= 8:
            last_alert = self.last_alert_times.get('uv', 0)
            if current_time - last_alert >= ALERT_COOLDOWN:
                alert_message = f"자외선 지수가 {uv}입니다. 선크림을 바르세요!"
                await self.send_message(alert_message)
                await self.save_alert_to_db(alert_message)
                self.last_alert_times['uv'] = current_time

    async def monitor(self):
        try:
            await self.init_db()
            while True:
                data = await self.fetch_data()
                if data:
                    # 데이터 추가
                    data_point = np.array([
                        data.get('temperature', 0),
                        data.get('humidity', 0),
                        data.get('gas', 0),
                        data.get('shock', 0),  # 필요 없으면 삭제 가능
                        data.get('dust', 0),
                        data.get('uv', 0),
                        data.get('x', 0),
                        data.get('y', 0),
                        data.get('z', 0)
                    ])

                    # 데이터 유효성 검사
                    if not np.any(np.isnan(data_point)):
                        # 이상치 탐지 비활성화 (데이터가 동일해도 이상치로 판단하지 않음)
                        self.data_history.append(data_point.tolist())
                        await self.check_alerts(data)

                        # 현재 데이터 전송 (10초마다)
                        message = (
                            f"<b>현재 센서 데이터:</b>\n"
                            f"온도: {data.get('temperature', 0)}도\n"
                            f"습도: {data.get('humidity', 0)}%\n"
                            f"가스 농도: {data.get('gas', 0)}ppm\n"
                            f"x: {data.get('x', 0)}\n"
                            f"y: {data.get('y', 0)}\n"
                            f"z: {data.get('z', 0)}\n"
                            f"먼지 농도: {data.get('dust', 0)}\n"
                            f"자외선 지수: {data.get('uv', 0)}\n"
                            f"시간: {self.get_seoul_time()}"
                        )
                        await self.send_message(message)

                        # 피로도 예측 (1분마다)
                        current_time = time.time()
                        if current_time - self.last_fatigue_predict_time >= 60:
                            logger.info("피로도 예측을 시작합니다.")
                            await self.predict_fatigue()
                            self.last_fatigue_predict_time = current_time
                    else:
                        logger.warning("수신된 데이터에 유효하지 않은 값이 포함되어 있습니다.")

                await asyncio.sleep(10)  # 10초마다 데이터 수집 및 전송
        except Exception as e:
            logger.critical(f"모니터링 중 예외 발생: {e}")
        finally:
            if self.db_pool:
                self.db_pool.close()
                await self.db_pool.wait_closed()
                logger.info("데이터베이스 연결을 종료하였습니다.")

if __name__ == '__main__':
    monitor = FatigueMonitor()
    try:
        asyncio.run(monitor.monitor())
    except KeyboardInterrupt:
        logger.info("프로그램이 사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.critical(f"프로그램 실행 중 예외 발생: {e}")
