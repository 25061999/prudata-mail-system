import smtplib
from email.mime.text import MIMEText
import os
import time
import logging
from rate_limiter import allow_send
from flask import current_app

def send_bulk_email(subject, body, recipients):
    sent_count = 0
    failed_emails = []
    
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)
        server.starttls()
        server.login(os.getenv("EMAIL"), os.getenv("EMAIL_PASSWORD"))
        
        for email in recipients:
            try:
                allow_send(3)  # 3 seconds gap
                
                msg = MIMEText(body, "html" if "<html>" in body else "plain")
                msg["Subject"] = subject
                msg["From"] = os.getenv("EMAIL")
                msg["To"] = email
                
                server.sendmail(msg["From"], email, msg.as_string())
                sent_count += 1
                logging.info(f"✅ Email sent to: {email}")
                
            except Exception as e:
                failed_emails.append((email, str(e)))
                logging.error(f"❌ Failed to send to {email}: {str(e)}")
                continue  # Continue with next email
        
        server.quit()
        
    except Exception as e:
        logging.error(f"❌ SMTP connection failed: {str(e)}")
        return False, f"SMTP Error: {str(e)}", []
    
    # Return results
    success = len(failed_emails) == 0
    message = f"Sent {sent_count}/{len(recipients)} emails" if not success else "All emails sent successfully"
    return success, message, failed_emails