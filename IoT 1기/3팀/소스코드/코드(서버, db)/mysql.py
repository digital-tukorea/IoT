import mysql.connector
import paho.mqtt.client as mqtt
import json
import time
import threading

# MySQL 데이터베이스에 연결
conn = mysql.connector.connect(
    host='34.64.249.216',
    user='root',
    password='iotiot123',
    database='final_data'
)


# 커서 생성
cursor = conn.cursor()

sql_all = """
INSERT INTO test_data
(latitude, longitude, temperature, humidity, cx, cy, cz, deltaCx, deltaCy, deltaCz, orientation, ppm, timestamp)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s, CURRENT_TIMESTAMP + INTERVAL 9 HOUR)
"""

def on_connect(client, userdata, flags, rc):
    client.subscribe("home/sensors")

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode('utf-8'))

    values_all = (
        data.get("latitude"),
        data.get("longitude"),
        data.get("temperature"),
        data.get("humidity"),
        data.get("cx"),
        data.get("cy"),
        data.get("cz"),
        data.get("deltaCx", 0),
        data.get("deltaCy", 0),
        data.get("deltaCz", 0),
        data.get("orientation"),
        data.get("ppm", 0)
    )

    try:
        cursor.execute(sql_all, values_all)
        conn.commit()
        print("Data inserted into MySQL")
    except mysql.connector.Error as e:
        print(f"Error inserting data: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("34.64.139.72", 1883, 60)
client.loop_start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Interrupted by user")
finally:
    cursor.close()
    conn.close()
    client.loop_stop()
    client.disconnect()
