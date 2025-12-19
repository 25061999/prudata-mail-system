from flask import Flask, render_template, request, redirect, session
from dotenv import load_dotenv
from email_generator import generate_email
from email_sender import send_bulk_email
from auth import authenticate
import pandas as pd
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "prudata_secret"


# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if authenticate(request.form["username"], request.form["password"]):
            session["user"] = "admin"
            return redirect("/dashboard")
    return render_template("login.html")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template("dashboard.html")


# ---------------- COMPOSE EMAIL ----------------
@app.route("/compose", methods=["POST"])
def compose():
    if "user" not in session:
        return redirect("/")

    subject = request.form["subject"]
    purpose = request.form["purpose"]
    template = request.form["template"]

    file = request.files["csv"]
    df = pd.read_csv(file)
    emails = df.iloc[:, 0].dropna().tolist()

    body = generate_email(purpose, template)
    print("EMAIL BODY GENERATED:\n", body)


    return render_template(
        "preview.html",
        subject=subject,
        body=body,
        emails=emails,
        count=len(emails)
    )


# ---------------- SEND EMAIL ----------------
@app.route("/send", methods=["POST"])
def send():
    if "user" not in session:
        return redirect("/")

    subject = request.form["subject"]
    body = request.form["body"]
    emails = request.form.getlist("emails")

    send_bulk_email(subject, body, emails)

    return render_template("success.html", count=len(emails))


# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)
