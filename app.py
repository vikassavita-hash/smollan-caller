import os
from flask import Flask, request, Response
import sqlite3
from datetime import datetime

app = Flask(__name__)

BASE_URL = os.environ.get("BASE_URL", "https://smollan-caller.onrender.com")

@app.route("/", methods=["GET"])
def home():
    return "Smollan AI Calling Server — Running!", 200

@app.route("/answer", methods=["POST", "GET"])
def answer():
    print("=== ANSWER CALLED ===")
    print(f"Form data: {dict(request.form)}")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak voice="WOMAN" language="hi-IN">
        Namaste! Main Smollan ki taraf se bol rahi hoon.
        Kya aap aaj field duty par aa rahe hain?
        Haan ke liye 1 dabayein.
        Leave ke liye 2 dabayein.
    </Speak>
    <Gather numDigits="1" timeout="10"
            action="{BASE_URL}/response" method="POST">
        <Speak voice="WOMAN" language="hi-IN">
            Kripya 1 ya 2 dabayein.
        </Speak>
    </Gather>
    <Speak voice="WOMAN" language="hi-IN">
        Koi response nahi mila. Dhanyawad. Goodbye!
    </Speak>
    <Hangup/>
</Response>"""

    print(f"Returning XML with BASE_URL: {BASE_URL}")
    return Response(xml, mimetype="text/xml")

@app.route("/response", methods=["POST", "GET"])
def handle_response():
    print("=== RESPONSE RECEIVED ===")
    print(f"All form data: {dict(request.form)}")

    digit     = request.form.get("Digits", "")
    call_uuid = request.form.get("CallUUID", "")

    print(f"Digit pressed: '{digit}'")
    print(f"Call UUID: '{call_uuid}'")

    if digit == "1":
        status = "PRESENT"
        msg    = "Shukriya! Aapki attendance mark ho gayi. Acha din ho!"
    elif digit == "2":
        status = "LEAVE"
        msg    = "Theek hai. Leave record kar li gayi. Jaldi theek ho jaayein!"
    else:
        status = "UNCLEAR"
        msg    = "Koi valid input nahi mila. Dhanyawad."

    print(f"Status classified: {status}")
    log_result(call_uuid, status)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak voice="WOMAN" language="hi-IN">
        {msg}
    </Speak>
    <Hangup/>
</Response>"""

    return Response(xml, mimetype="text/xml")

@app.route("/hangup", methods=["POST", "GET"])
def hangup():
    print("=== CALL ENDED ===")
    print(f"Hangup data: {dict(request.form)}")
    return "OK", 200

def log_result(call_uuid, status):
    try:
        conn = sqlite3.connect("attendance.db")
        c    = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                call_uuid TEXT,
                status    TEXT,
                timestamp TEXT
            )
        ''')
        c.execute(
            "INSERT INTO logs (call_uuid, status, timestamp) VALUES (?, ?, ?)",
            (call_uuid, status, datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
        )
        conn.commit()
        conn.close()
        print(f"DB logged: {status} — {call_uuid}")
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    app.run(debug=True)
