from flask import Flask, request, Response
import sqlite3
from datetime import datetime

app = Flask(__name__)

@app.route("/answer", methods=["POST", "GET"])
def answer():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak voice="WOMAN" language="hi-IN">
        Namaste! Main Smollan ki taraf se bol rahi hoon.
        Kya aap aaj field duty par aa rahe hain?
        Haan ke liye 1 dabayein.
        Leave ke liye 2 dabayein.
    </Speak>
    <Gather numDigits="1" timeout="10"
            action="/response" method="POST">
    </Gather>
    <Speak voice="WOMAN" language="hi-IN">
        Koi response nahi mila. Dhanyawad.
    </Speak>
    <Hangup/>
</Response>"""
    return Response(xml, mimetype="text/xml")

@app.route("/response", methods=["POST", "GET"])
def handle_response():
    digit     = request.form.get("Digits", "")
    call_uuid = request.form.get("CallUUID", "")
    
    print(f"Response: {digit} — Call: {call_uuid}")
    
    if digit == "1":
        status = "PRESENT"
        msg    = "Shukriya! Aapki attendance mark ho gayi. Acha din ho!"
    elif digit == "2":
        status = "LEAVE"
        msg    = "Theek hai. Leave record kar li gayi. Jaldi theek ho jaayein!"
    else:
        status = "UNCLEAR"
        msg    = "Invalid input. Dhanyawad."
    
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
    print(f"Call ended: {request.form}")
    return "OK"

def log_result(call_uuid, status):
    try:
        conn = sqlite3.connect("attendance.db")
        c    = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS logs
                     (call_uuid TEXT, status TEXT, timestamp TEXT)''')
        c.execute("INSERT INTO logs VALUES (?, ?, ?)",
                  (call_uuid, status,
                   datetime.now().strftime("%d-%m-%Y %H:%M:%S")))
        conn.commit()
        conn.close()
        print(f"Logged: {status}")
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    app.run(debug=True)