from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://www.aiwd.co.kr", "https://aiwd.co.kr"])


@app.route("/send-email", methods=["POST"])
def send_email():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "잘못된 요청입니다."}), 400

    # ponytail: honeypot(봇이 채우는 숨김 필드) + 최소 작성 시간으로 스팸봇 차단
    if data.get("website"):
        return jsonify({"status": "error", "message": "잘못된 요청입니다."}), 400
    if data.get("elapsedMs", 0) < 2000:
        return jsonify({"status": "error", "message": "잘못된 요청입니다."}), 400

    name = data.get("name", "").strip()
    company = data.get("company", "").strip()
    email = data.get("email", "").strip()
    message = data.get("message", "").strip()

    if not all([name, email, message]):
        return jsonify({"status": "error", "message": "필수 항목이 누락되었습니다."}), 400

    naver_email = os.getenv("NAVER_EMAIL")
    naver_password = os.getenv("NAVER_PASSWORD")

    msg = MIMEMultipart()
    msg["From"] = naver_email
    msg["To"] = "ksnam@aiwd.co.kr"
    msg["Subject"] = f"[AIWORLD 문의] {name} ({company})"
    msg.attach(MIMEText(
        f"이름: {name}\n기업명: {company}\n이메일: {email}\n\n문의사항:\n{message}",
        "plain",
        "utf-8",
    ))

    try:
        with smtplib.SMTP_SSL("smtp.naver.com", 465) as server:
            server.login(naver_email, naver_password)
            server.send_message(msg)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
