from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://www.aiwd.co.kr", "https://aiwd.co.kr"])

# ponytail: Render 무료 플랜이 SMTP 포트를 차단하므로 Brevo HTTP API로 발송
RECIPIENT = "ksnam@aiwd.co.kr"


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

    api_key = os.getenv("BREVO_API_KEY")
    sender = os.getenv("BREVO_SENDER")
    if not api_key or not sender:
        return jsonify({"status": "error", "message": "메일 설정이 완료되지 않았습니다."}), 500

    try:
        resp = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": api_key, "Content-Type": "application/json"},
            json={
                "sender": {"name": "AIWORLD 문의폼", "email": sender},
                "to": [{"email": RECIPIENT}],
                "replyTo": {"email": email, "name": name},
                "subject": f"[AIWORLD 문의] {name} ({company})",
                "textContent": f"이름: {name}\n기업명: {company}\n이메일: {email}\n\n문의사항:\n{message}",
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": f"메일 발송 실패 ({resp.status_code}): {resp.text[:200]}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
