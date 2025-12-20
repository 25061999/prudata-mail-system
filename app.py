from flask import Flask, render_template, request, redirect, session
from dotenv import load_dotenv
from email_generator import generate_email
from email_sender import send_bulk_email
from auth import authenticate
import pandas as pd
import logging
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")


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
    
    # Get emails and names if available
    emails = df['email'].dropna().tolist()
    
    # Handle names column (use empty string if not present)
    names = []
    if 'name' in df.columns:
        names = df['name'].fillna('').tolist()
    else:
        names = [''] * len(emails)

    body = generate_email(purpose, template)
    app.logger.info(f"Email body generated for: {purpose}")

    return render_template(
        "preview.html",
        subject=subject,
        body=body,
        emails=emails,
        names=names,  # Pass names to template
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
    names = request.form.getlist("names")

    # ✅ Now sends with names for personalization
    success, message, failed_emails = send_bulk_email(subject, body, emails, names)
    
    if success:
        return render_template("success.html", count=len(emails))
    else:
        # Show which emails failed
        return f"""
        <h2>Partial Success</h2>
        <p>{message}</p>
        <p>Failed emails ({len(failed_emails)}):</p>
        <ul>
            {"".join(f"<li>{email}: {error}</li>" for email, error in failed_emails)}
        </ul>
        <a href="/dashboard">Back to Dashboard</a>
        """


# ---------------- RUN APP ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)