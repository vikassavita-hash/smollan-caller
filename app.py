import os
import requests
import sqlite3
from datetime import datetime
from flask import Flask, request, Response
import anthropic

app = Flask(__name__)

BASE_URL         = os.environ.get("BASE_URL", "https://smollan-caller.onrender.com")
VOBIZ_AUTH_ID    = os.environ.get("VOBIZ_AUTH_ID", "MA_8P89YGSA")
VOBIZ_AUTH_TOKEN = os.environ.get("VOBIZ_AUTH_TOKEN", "9YqJVtYBmtuPnn8ZpRGMgnE5KEougPcIOafk7ygX6GSu7EYIWRb0xiZCzNy5LQdx")
ANTHROPIC_KEY    = os.environ.get("ANTHROPIC_API_KEY", "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")

# ── HOME ──────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return "Smollan AI Calling Server — Running!", 200

# ── STEP 1: Call aane par AI bolti hai ───────────────────────────
@app.route("/answer", methods=["POST", "GET"])
def answer():
    print("=== CALL ANSWERED ===")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak voice="WOMAN" language="en-IN">
        Good morning! This is a call from Smollan Head Office.
        Please confirm your attendance for today.
        Say present if you are on duty,
        or say leave if you are not coming today.
    </Speak>
    <Record maxLength="5"
            action="{BASE_URL}/attendance-response"
            method="POST"
            playBeep="false"
            finishOnKey="">
    </Record>
    <Speak voice="WOMAN" language="en-IN">
        We did not receive your response.
        Thank you. Goodbye.
    </Speak>
    <Hangup/>
</Response>"""

    return Response(xml, mimetype="text/xml")

# ── STEP 2: Recording mili — transcribe + classify ───────────────
@app.route("/attendance-response", methods=["POST", "GET"])
def attendance_response():
    print("=== ATTENDANCE RESPONSE ===")
    print(f"Form data: {dict(request.form)}")

    recording_url = request.form.get("RecordingUrl", "")
    call_uuid     = request.form.get("CallUUID", "")
    to_number     = request.form.get("To", "")

    print(f"Recording URL: {recording_url}")

    if not recording_url:
        print("No recording received")
        return _no_response_xml()

    # Recording download karo
    audio = _download_recording(recording_url)
    if not audio:
        return _no_response_xml()

    # Whisper se transcribe karo
    transcript = _transcribe(audio)
    print(f"Transcript: {transcript}")

    # Claude se classify karo
    status, reason = _classify(transcript)
    print(f"Status: {status} | Reason: {reason}")

    # DB mein log karo
    log_result(call_uuid, to_number, status, reason, transcript)

    if status == "PRESENT":
        msg = """Thank you for confirming.
                 Your attendance has been marked for today.
                 Have a productive day. Goodbye."""

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak voice="WOMAN" language="en-IN">{msg}</Speak>
    <Hangup/>
</Response>"""
        return Response(xml, mimetype="text/xml")

    elif status == "LEAVE":
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak voice="WOMAN" language="en-IN">
        Thank you for informing us.
        Could you please tell us the reason for your leave today?
        Please speak after this message.
    </Speak>
    <Record maxLength="8"
            action="{BASE_URL}/leave-reason?uuid={call_uuid}&amp;phone={to_number}"
            method="POST"
            playBeep="false"
            finishOnKey="">
    </Record>
    <Hangup/>
</Response>"""
        return Response(xml, mimetype="text/xml")

    else:
        msg = """We could not understand your response.
                 Please contact your Team Leader directly.
                 Thank you. Goodbye."""

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak voice="WOMAN" language="en-IN">{msg}</Speak>
    <Hangup/>
</Response>"""
        return Response(xml, mimetype="text/xml")

# ── STEP 3: Leave reason record ──────────────────────────────────
@app.route("/leave-reason", methods=["POST", "GET"])
def leave_reason():
    print("=== LEAVE REASON ===")

    recording_url = request.form.get("RecordingUrl", "")
    call_uuid     = request.args.get("uuid", "")
    phone         = request.args.get("phone", "")

    if recording_url:
        audio      = _download_recording(recording_url)
        transcript = _transcribe(audio) if audio else "Not captured"
        reason     = _extract_reason(transcript)
        print(f"Leave reason: {reason}")
        update_reason(call_uuid, reason)
        msg = """Thank you for letting us know.
                 Your leave has been recorded.
                 Please take care. Goodbye."""
    else:
        msg = "Thank you. Your leave has been noted. Goodbye."

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak voice="WOMAN" language="en-IN">{msg}</Speak>
    <Hangup/>
</Response>"""

    return Response(xml, mimetype="text/xml")

# ── STEP 4: Hangup log ───────────────────────────────────────────
@app.route("/hangup", methods=["POST", "GET"])
def hangup():
    print(f"=== CALL ENDED === {dict(request.form)}")
    return "OK", 200

# ── HELPER: Recording download ───────────────────────────────────
def _download_recording(url):
    try:
        r = requests.get(
            url,
            headers={
                "X-Auth-ID":    VOBIZ_AUTH_ID,
                "X-Auth-Token": VOBIZ_AUTH_TOKEN
            },
            timeout=10
        )
        if r.status_code == 200:
            path = "/tmp/recording.wav"
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"Recording saved: {len(r.content)} bytes")
            return path
        print(f"Recording download failed: {r.status_code}")
        return None
    except Exception as e:
        print(f"Download error: {e}")
        return None

# ── HELPER: Whisper transcribe ───────────────────────────────────
def _transcribe(audio_path):
    try:
        import whisper
        model  = whisper.load_model("tiny")
        result = model.transcribe(audio_path, language="en")
        return result["text"].strip()
    except Exception as e:
        print(f"Transcribe error: {e}")
        return ""

# ── HELPER: Claude classify ──────────────────────────────────────
def _classify(transcript):
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        msg    = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": f"""Classify this attendance response: "{transcript}"

Reply in this exact format only:
STATUS: PRESENT or LEAVE or UNCLEAR
REASON: brief reason or none

Examples:
STATUS: PRESENT
REASON: none

STATUS: LEAVE
REASON: sick"""
            }]
        )
        text   = msg.content[0].text
        status = "PRESENT" if "PRESENT" in text else \
                 "LEAVE"   if "LEAVE"   in text else "UNCLEAR"
        reason = ""
        for line in text.split("\n"):
            if "REASON:" in line:
                reason = line.split("REASON:")[-1].strip()
        return status, reason
    except Exception as e:
        print(f"Claude error: {e}")
        t = transcript.lower()
        if any(w in t for w in ["present", "yes", "coming", "aa raha", "haan"]):
            return "PRESENT", ""
        elif any(w in t for w in ["leave", "no", "sick", "nahi", "chutti"]):
            return "LEAVE", "mentioned in call"
        return "UNCLEAR", ""

# ── HELPER: Reason extract ───────────────────────────────────────
def _extract_reason(transcript):
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        msg    = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=30,
            messages=[{
                "role": "user",
                "content": f"""Extract leave reason from: "{transcript}"
Reply in 3-5 words only.
Example: sick fever, family emergency, personal work"""
            }]
        )
        return msg.content[0].text.strip()
    except:
        return transcript[:50] if transcript else "Not captured"

# ── HELPER: No response XML ──────────────────────────────────────
def _no_response_xml():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak voice="WOMAN" language="en-IN">
        We did not receive your response.
        Thank you. Goodbye.
    </Speak>
    <Hangup/>
</Response>"""
    return Response(xml, mimetype="text/xml")

# ── DB: Log result ───────────────────────────────────────────────
def log_result(call_uuid, phone, status, reason, transcript):
    try:
        conn = sqlite3.connect("attendance.db")
        c    = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            call_uuid  TEXT,
            phone      TEXT,
            status     TEXT,
            reason     TEXT,
            transcript TEXT,
            timestamp  TEXT
        )''')
        c.execute(
            "INSERT INTO logs VALUES (NULL,?,?,?,?,?,?)",
            (call_uuid, phone, status, reason, transcript,
             datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
        )
        conn.commit()
        conn.close()
        print(f"DB logged: {status} — {reason}")
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
