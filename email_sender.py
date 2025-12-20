import os
import re
import logging
import time
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Content

# ==================== RATE LIMITER ====================
_last_sent_time = 0

def wait_between_emails(delay_seconds=5):
    """Simple rate limiter."""
    global _last_sent_time
    current_time = time.time()
    time_since_last = current_time - _last_sent_time
    
    if time_since_last < delay_seconds:
        sleep_time = delay_seconds - time_since_last
        time.sleep(sleep_time)
    
    _last_sent_time = time.time()

# ==================== HTML FORMATTER ====================
def format_email_body_to_html(plain_text_body):
    """Converts plain text to clean HTML."""
    plain_text_body = plain_text_body.strip()
    lines = plain_text_body.split('\n')
    html_lines = []
    in_list = False
    
    for line in lines:
        line = line.rstrip()
        
        stripped_line = line.strip()
        if stripped_line.startswith('*'):
            if not in_list:
                html_lines.append('<ul style="margin:10px 0;padding-left:20px;">')
                in_list = True
            list_item = stripped_line.lstrip('*').strip()
            html_lines.append(f'<li style="margin-bottom:5px;">{list_item}</li>')
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            
            if line:
                line = re.sub(r'\[.*?\]', '', line)  # Remove placeholders
                html_lines.append(f'<p style="margin:8px 0;line-height:1.5;">{line}</p>')
    
    if in_list:
        html_lines.append('</ul>')
    
    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;">
{''.join(html_lines)}
</body>
</html>"""
    
    return html_body

# ==================== MAIN FUNCTION ====================
def send_bulk_email(subject, body, recipients):
    """
    Sends bulk email using SendGrid API.
    Returns: (success_bool, message_str, failed_emails_list)
    """
    if not recipients:
        return False, "No recipients provided", []
    
    if not isinstance(recipients, list):
        recipients = [recipients] if recipients else []
    
    sent_count = 0
    failed_emails = []
    
    # 1. Get API key
    api_key = os.environ.get('SENDGRID_API_KEY')
    if not api_key:
        return False, "SendGrid API key not configured.", []
    
    # 2. Get sender info
    from_email = os.environ.get("EMAIL", "prudata.tech@gmail.com")
    
    # 3. Clean subject
    subject = re.sub(r'\b(free|guarantee|click here|buy now|limited time)\b', '', subject, flags=re.IGNORECASE)
    subject = subject.strip()
    if not subject:
        subject = "Message from Prudata"
    
    # 4. Format content
    try:
        html_body = format_email_body_to_html(body)
        plain_body = re.sub(r'<[^>]+>', '', body)
        plain_body = re.sub(r'\[.*?\]', '', plain_body)
        plain_body = re.sub(r'\s+', ' ', plain_body).strip()
    except Exception as e:
        logging.error(f"Formatting error: {str(e)}")
        html_body = f"<p>{body}</p>"
        plain_body = body
    
    # 5. Create SendGrid client
    try:
        sg_client = SendGridAPIClient(api_key)
    except Exception as e:
        return False, f"SendGrid client error: {str(e)}", []
    
    # 6. Send emails
    for to_email in recipients:
        # Basic email validation
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', str(to_email)):
            failed_emails.append((to_email, "Invalid format"))
            continue
        
        to_email = str(to_email).strip().lower()
        
        try:
            # Rate limiting
            wait_between_emails(5)
            
            # Create email (SIMPLIFIED - no headers property)
            message = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_body
            )
            
            # Add plain text version
            message.add_content(Content("text/plain", plain_body))
            
            # ✅ FIXED: Set reply-to correctly (NOT in headers)
            message.reply_to = from_email
            
            # ✅ FIXED: Tracking settings (NOT in headers)
            message.tracking_settings = {
                "click_tracking": {"enable": False},
                "open_tracking": {"enable": False}
            }
            
            # ❌ REMOVED: message.headers = {...}  # This was causing the error
            
            # Send email
            response = sg_client.send(message)
            
            if response.status_code == 202:
                sent_count += 1
                logging.info(f"✅ Sent to: {to_email}")
            else:
                error_body = response.body.decode('utf-8') if response.body else "No details"
                failed_emails.append((to_email, f"Error {response.status_code}: {error_body}"))
                
        except Exception as e:
            failed_emails.append((to_email, str(e)))
            logging.error(f"Failed to send to {to_email}: {str(e)}")
            continue
    
    # 7. Return results
    success = len(failed_emails) == 0 and sent_count == len(recipients)
    message = f"Sent {sent_count}/{len(recipients)}. {len(failed_emails)} failed."
    
    return success, message, failed_emails