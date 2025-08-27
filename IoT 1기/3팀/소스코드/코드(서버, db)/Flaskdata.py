from flask import Flask, jsonify, request, Response
import json
from decimal import Decimal
import mysql.connector
from flask_cors import CORS
from datetime import datetime

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')  # datetime을 문자열로 변환
        return super(DecimalEncoder, self).default(obj)

app = Flask(__name__)
CORS(app)

# MySQL 데이터베이스 정보
DB_HOST = "34.64.249.216"
DB_USER = "root"
DB_PASSWORD = "iotiot123"
DB_NAME = "final_data"

# 데이터베이스 연결 설정
def connect_to_database():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

@app.route('/')
def home():
    return "Welcome to the Flask server!"

@app.route('/data', methods=['GET'])
def get_data():
    try:
        cnx = connect_to_database()
        cursor = cnx.cursor(dictionary=True)
        query = """
        SELECT latitude, longitude, ppm, temperature, humidity, cx, cy, cz, deltaCx, deltaCy, deltaCz, orientation
        FROM test_data
        ORDER BY timestamp DESC
        LIMIT 1
        """
        cursor.execute(query)  # 쿼리 실행
        row = cursor.fetchone()  # 가장 최근 데이터 1개 조회
        cursor.close()
        cnx.close()

        if row:
            # JSON으로 변환
            json_data = json.dumps(row, cls=DecimalEncoder)
            return Response(json_data, mimetype='application/json')
        else:
            return jsonify({"error": "No data found"}), 404  # 데이터가 없을 경우 404 응답
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500  # MySQL 오류에 대한 응답
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # 일반 오류에 대한 응답

@app.route('/update', methods=['POST'])
def update_data():
    try:
        data = request.json
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        ppm = data.get("ppm")
        temperature = data.get("temperature")
        humidity = data.get("humidity")
        cx = data.get("cx")
        cy = data.get("cy")
        cz = data.get("cz")
        deltaCx = data.get("deltaCx")
        deltaCy = data.get("deltaCy")
        deltaCz = data.get("deltaCz")
        orientation = data.get("orientation")

        cnx = connect_to_database()
        cursor = cnx.cursor()
        add_sensor = """
        INSERT INTO test_data (
            latitude, longitude, ppm, temperature, humidity, cx, cy, cz, deltaCx, deltaCy, deltaCz, orientation, timestamp
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP + INTERVAL 9 HOUR)
        """

        cursor.execute(add_sensor, (latitude, longitude, ppm, temperature, humidity, cx, cy, cz, deltaCx, deltaCy, deltaCz, orientation))
        cnx.commit()
        cursor.close()
        cnx.close()
        return jsonify({"status": "success"}), 200
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500  # MySQL 오류에 대한 응답
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # 일반 오류에 대한 응답

@app.route('/data_1', methods=['GET'])
def get_data_1():
    try:
        cnx = connect_to_database()
        cursor = cnx.cursor(dictionary=True)
        query = """
        SELECT fatigability
        FROM expect_data
        ORDER BY timestamp DESC
        LIMIT 1
        """
        cursor.execute(query)  # 쿼리 실행
        row = cursor.fetchone()  # 가장 최근 데이터 1개 조회
        cursor.close()
        cnx.close()
        if row:
            # JSON으로 변환
            json_data = json.dumps(row, cls=DecimalEncoder)
            return Response(json_data, mimetype='application/json')
        else:
            return jsonify({"error": "No data found"}), 404  # 데이터가 없을 경우 404 응답
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500  # MySQL 오류에 대한 응답
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # 일반 오류에 대한 응답

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
