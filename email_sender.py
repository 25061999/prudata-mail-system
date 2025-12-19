import smtplib
from email.mime.text import MIMEText
import os
from rate_limiter import allow_send

def send_bulk_email(subject, body, recipients):
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(os.getenv("EMAIL"), os.getenv("EMAIL_PASSWORD"))

    for email in recipients:
        allow_send(3)  # 3 seconds gap
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = os.getenv("EMAIL")
        msg["To"] = email
        server.sendmail(msg["From"], email, msg.as_string())

    server.quit()
