from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://www.aiwd.co.kr", "https://aiwd.co.kr"])

DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_KEY = os.getenv("ADMIN_KEY")


def db():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    with db() as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inquiries (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                company TEXT DEFAULT '',
                email TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """)


try:
    init_db()
except Exception:
    pass  # DATABASE_URL 미설정 상태로 배포돼도 서버는 뜨게 함


def is_admin():
    return ADMIN_KEY and request.headers.get("X-Admin-Key") == ADMIN_KEY


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

    try:
        with db() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO inquiries (name, company, email, message) VALUES (%s, %s, %s, %s)",
                (name, company, email, message),
            )
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/inquiries", methods=["GET"])
def list_inquiries():
    if not is_admin():
        return jsonify({"status": "error", "message": "인증 실패"}), 401
    try:
        with db() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, company, email, message,
                       to_char(created_at AT TIME ZONE 'Asia/Seoul', 'YYYY-MM-DD HH24:MI:SS')
                FROM inquiries ORDER BY id DESC
            """)
            rows = cur.fetchall()
        return jsonify([
            {"id": r[0], "name": r[1], "company": r[2], "email": r[3],
             "message": r[4], "created_at": r[5]}
            for r in rows
        ])
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/inquiry/<int:inquiry_id>", methods=["DELETE"])
def delete_inquiry(inquiry_id):
    if not is_admin():
        return jsonify({"status": "error", "message": "인증 실패"}), 401
    try:
        with db() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM inquiries WHERE id = %s", (inquiry_id,))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
