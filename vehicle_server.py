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
<html>
<head>
  <title>Select Vehicle</title>
  <style>
    body { font-family: sans-serif; text-align: center; padding: 2em; background: #f9f9f9; }
    h2 { color: #333; }
    form { background: white; display: inline-block; padding: 2em; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    select, button { padding: 0.5em 1em; font-size: 1rem; border-radius: 6px; border: 1px solid #ccc; margin-top: 1em; }
    button { background: #007BFF; color: white; border: none; cursor: pointer; }
    button:hover { background: #0056b3; }
  </style>
</head>
<body>
  <h2>Select Your Vehicle Colour</h2>
  <form method="post">
    <select name="color">
      {% for c in colours %}
        <option value="{{c}}">{{c}}</option>
      {% endfor %}
    </select>
    <br>
    <button type="submit">Enter</button>
  </form>
</body>
</html>
"""

DASH_HTML = """
<!doctype html>
<html>
<head>
  <title>Vehicle Dashboard</title>
  <style>
    body { font-family: sans-serif; background: #f0f4f8; padding: 2em; text-align: center; }
    h2 { color: #444; }
    .dashboard {
      background: white;
      display: inline-block;
      padding: 2em 3em;
      border-radius: 14px;
      box-shadow: 0 6px 20px rgba(0,0,0,0.1);
      margin-top: 2em;
    }
    .stat { font-size: 2.5rem; color: #222; margin: 1rem 0; }
    .speed { font-size: 1.25rem; color: #666; }
  </style>
</head>
<body>
  <h2>Vehicle ({{colour}})</h2>
  <div class="dashboard">
    <div class="stat" id="stat">…</div>
    <div class="speed">Last speed: <span id="speed">…</span> mph</div>
  </div>
  <script>
    async function updateStatus() {
      try {
        const res = await fetch("/status");
        const data = await res.json();
        if (data.error) {
          document.getElementById("stat").textContent = data.error;
          document.getElementById("speed").textContent = "–";
        } else {
          document.getElementById("stat").textContent = data.status;
          document.getElementById("speed").textContent = (data.speed ?? "–").toFixed(1);
        }
      } catch (err) {
        document.getElementById("stat").textContent = "Error fetching status.";
        document.getElementById("speed").textContent = "–";
      }
    }
    updateStatus();
    setInterval(updateStatus, 1000);
  </script>
</body>
</html>
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
