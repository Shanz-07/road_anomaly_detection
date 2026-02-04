from flask import Flask, render_template, jsonify, send_from_directory, request, redirect, session
import csv
import os

app = Flask(__name__)
app.secret_key = "change-this-secret"

LOG_FILE = "logs/anomaly_log.csv"
CLIPS_DIR = "clips"

USERNAME = "admin"
PASSWORD = "1234"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == USERNAME and request.form["password"] == PASSWORD:
            session["user"] = USERNAME
            return redirect("/")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
def index():
    if "user" not in session:
        return redirect("/login")
    return render_template("index.html")

@app.route("/api/logs")
def get_logs():
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, newline="") as f:
            reader = csv.DictReader(f)
            logs = list(reader)
    return jsonify(logs)

@app.route("/api/stats")
def get_stats():
    stats = {}
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cls = row["class"]
                stats[cls] = stats.get(cls, 0) + 1
    return jsonify(stats)

@app.route("/api/clips")
def get_clips():
    files = []
    if os.path.exists(CLIPS_DIR):
        files = sorted(os.listdir(CLIPS_DIR), reverse=True)
    return jsonify(files)

@app.route("/api/delete_clip", methods=["POST"])
def delete_clip():
    name = request.json["name"]
    path = os.path.join(CLIPS_DIR, name)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"ok": True})
    return jsonify({"ok": False})

@app.route("/clips/<filename>")
def serve_clip(filename):
    return send_from_directory(CLIPS_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True)
