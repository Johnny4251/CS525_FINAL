#!/usr/bin/env python3
"""
vehicle_server.py
-----------------
Very small Flask site that lets a driver pick their vehicle colour and
shows live speed / status, refreshing once per second.

Run with:  python3 vehicle_server.py
"""
from flask import Flask, request, redirect, session, jsonify, render_template_string
import sqlite3, os

app = Flask(__name__)
app.secret_key = "top-secret-key"

DB_PATH = os.path.join(os.path.dirname(__file__), "vehicle_status.db")
COLOURS = ["Red","Orange","Yellow","Green","Blue","Purple","White","Gray","Black","Unknown"]

LOGIN_HTML = """
<!doctype html>
<title>Select vehicle</title>
<h2>Select your vehicle colour</h2>
<form method=post>
  <select name=color>
    {% for c in colours %}
      <option value="{{c}}">{{c}}</option>
    {% endfor %}
  </select>
  <button type=submit>Enter</button>
</form>
"""

DASH_HTML = """
<!doctype html>
<title>Vehicle dashboard</title>
<h2 style="margin-bottom:0">Vehicle ({{colour}})</h2>
<div style="font-size:3rem">
  <span id=stat>…</span>
</div>
<p>Last speed: <span id=speed>…</span> mph</p>
<script>
async function poll(){
    const r = await fetch("/status");
    const j = await r.json();
    if (j.error){ document.getElementById("stat").textContent = j.error; return; }
    document.getElementById("stat").textContent   = j.status;
    document.getElementById("speed").textContent  = (j.speed ?? "–").toFixed(1);
}
poll();                       // initial
setInterval(poll, 1000);      // every 1 s
</script>
"""

def get_db():
    return sqlite3.connect(DB_PATH)

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        session["color"] = request.form["color"]
        return redirect("/dashboard")
    return render_template_string(LOGIN_HTML, colours=COLOURS)

@app.route("/dashboard")
def dash():
    if "color" not in session:
        return redirect("/")
    return render_template_string(DASH_HTML, colour=session["color"])

@app.route("/status")
def status():
    colour = session.get("color")
    if not colour:
        return jsonify({"error": "not logged in"})
    cur = get_db().execute("SELECT speed_mph, status FROM vehicle_status WHERE color=?",
                            (colour,))
    row = cur.fetchone()
    if not row:
        return jsonify({"status": "waiting…", "speed": None})
    return jsonify({"status": row[1], "speed": row[0]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True, threaded=False)
