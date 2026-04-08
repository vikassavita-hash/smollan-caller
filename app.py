import os
import sqlite3
from datetime import datetime
from flask import Flask, request, Response

app = Flask(__name__)

BASE_URL = os.environ.get("BASE_URL", "https://smollan-caller.onrender.com")

# ── HOME ─────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return "Smollan AI Calling Server — Running!", 200

# ── STEP 1: Call aane par AI bolti hai ───────────────────────────
@app.route("/answer", methods=["POST", "GET"])
def answer():
    print("=== CALL ANSWERED ===")
    print(f"Form data: {dict(request.form)}")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak voice="WOMAN" language="en-IN">
        Good morning! This is a call from Smollan Head Office.
        Please confirm your attendance for today.
        Press 1 if you are present.
        Press 2 if you are on leave.
    </Speak>
    <Gather numDigits="1" timeout="10"
            action="{BASE_URL}/attendance-response"
            method="POST">
    </Gather>
    <Speak voice="WOMAN" language="en-IN">
        We did not receive your response.
        Thank you. Goodbye.
    </Speak>
    <Hangup/>
</Response>"""

    return Response(xml, mimetype="text/xml")

# ── STEP 2: Response process ─────────────────────────────────────
@app.route("/attendance-response", methods=["POST", "GET"])
def attendance_response():
    print("=== ATTENDANCE RESPONSE ===")
    print(f"Form data: {dict(request.form)}")

    digit     = request.form.get("Digits", "")
    call_uuid = request.form.get("CallUUID", "")
    phone     = request.form.get("To", "")

    print(f"Digit: {digit} | UUID: {call_uuid} | Phone: {phone}")

    if digit == "1":
        status = "PRESENT"
        xml    = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak voice="WOMAN" language="en-IN">
        Thank you for confirming.
        Your attendance has been marked for today.
        Have a productive day. Goodbye.
    </Speak>
    <Hangup/>
</Response>"""
        log_result(call_uuid, phone, status, "")

    elif digit == "2":
        status = "LEAVE"
        xml    = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak voice="WOMAN" language="en-IN">
        Thank you for informing us.
        Could you please tell us the reason for your leave?
        Press 1 for sick leave.
        Press 2 for personal reason.
        Press 3 for emergency.
    </Speak>
    <Gather numDigits="1" timeout="10"
            action="{BASE_URL}/leave-reason?uuid={call_uuid}&amp;phone={phone}"
            method="POST">
    </Gather>
    <Speak voice="WOMAN" language="en-IN">
        Leave has been noted. Thank you. Goodbye.
    </Speak>
    <Hangup/>
</Response>"""
        log_result(call_uuid, phone, status, "reason pending")

    else:
        status = "NO_RESPONSE"
        xml    = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak voice="WOMAN" language="en-IN">
        We did not receive a valid response.
        Please contact your Team Leader directly.
        Thank you. Goodbye.
    </Speak>
    <Hangup/>
</Response>"""
        log_result(call_uuid, phone, status, "")

    return Response(xml, mimetype="text/xml")

# ── STEP 3: Leave reason ─────────────────────────────────────────
@app.route("/leave-reason", methods=["POST", "GET"])
def leave_reason():
    print("=== LEAVE REASON ===")
    print(f"Form data: {dict(request.form)}")

    digit     = request.form.get("Digits", "")
    call_uuid = request.args.get("uuid", "")
    phone     = request.args.get("phone", "")

    reasons = {
        "1": "Sick Leave",
        "2": "Personal Reason",
        "3": "Emergency"
    }

    reason = reasons.get(digit, "Not specified")
    print(f"Leave reason: {reason}")

    update_reason(call_uuid, reason)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak voice="WOMAN" language="en-IN">
        Thank you. Your leave reason has been recorded as {reason}.
        Please take care. Goodbye.
    </Speak>
    <Hangup/>
</Response>"""

    return Response(xml, mimetype="text/xml")

# ── STEP 4: Hangup ───────────────────────────────────────────────
@app.route("/hangup", methods=["POST", "GET"])
def hangup():
    print(f"=== CALL ENDED === {dict(request.form)}")
    return "OK", 200

# ── DB: Log result ───────────────────────────────────────────────
def log_result(call_uuid, phone, status, reason):
    try:
        conn = sqlite3.connect("attendance.db")
        c    = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS logs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            call_uuid TEXT,
            phone     TEXT,
            status    TEXT,
            reason    TEXT,
            timestamp TEXT
        )''')
        c.execute(
            "INSERT INTO logs VALUES (NULL,?,?,?,?,?)",
            (call_uuid, phone, status, reason,
             datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
        )
        conn.commit()
        conn.close()
        print(f"DB logged: {status} | {reason}")
    except Exception as e:
        print(f"DB error: {e}")

# ── DB: Update reason ────────────────────────────────────────────
def update_reason(call_uuid, reason):
    try:
        conn = sqlite3.connect("attendance.db")
        c    = conn.cursor()
        c.execute(
            "UPDATE logs SET reason=? WHERE call_uuid=?",
            (reason, call_uuid)
        )
        conn.commit()
        conn.close()
        print(f"Reason updated: {reason}")
    except Exception as e:
        print(f"Update error: {e}")

if __name__ == "__main__":
    app.run(debug=True)
