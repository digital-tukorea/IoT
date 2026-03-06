# 파일명: server_app.py
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    # templates 폴더 내부의 dashboard.html 파일을 find&show.
    return render_template('dashboard.html')

if __name__ == '__main__':
    print("---------------------------------------------------")
    print("🚀 관제 시스템 웹 서버가 시작되었습니다.")
    print("🖥️  접속 주소: http://192.168.0.5:5000")
    print("---------------------------------------------------")
    # 0.0.0.0은 외부(같은 와이파이)에서 접속을 허용함.
    app.run(host='0.0.0.0', port=5001, debug=True)
