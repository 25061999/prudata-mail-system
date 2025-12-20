import os
import re
import logging
import time
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Content

# ==================== SIMPLE RATE LIMITER ====================
_last_sent_time = 0

def wait_between_emails(delay_seconds=5):  # Increased to 5 seconds for better warm-up
    """
    Ensures minimum delay between email sends to build domain reputation.
    """
    global _last_sent_time
    
    current_time = time.time()
    time_since_last = current_time - _last_sent_time
    
    if time_since_last < delay_seconds:
        sleep_time = delay_seconds - time_since_last
        time.sleep(sleep_time)
    
    _last_sent_time = time.time()

# ==================== EMAIL VALIDATION ====================
def validate_email(email):
    """
    Validates email format.
    """
    if not email or not isinstance(email, str):
        return False
    
    email = email.strip().lower()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# ==================== HTML FORMATTER ====================
def format_email_body_to_html(plain_text_body, recipient_name=""):
    """
    Creates professional HTML email optimized for deliverability.
    """
    # Clean and personalize
    plain_text_body = plain_text_body.strip()
    
    # Remove subject line if present
    if plain_text_body.startswith("Subject:"):
        lines = plain_text_body.split('\n', 1)
        plain_text_body = lines[1] if len(lines) > 1 else ""
    
    # Create greeting
    if recipient_name:
        greeting = f"Hi {recipient_name},<br><br>"
    else:
        greeting = "Hi there,<br><br>"
    
    # Process content
    lines = plain_text_body.split('\n')
    html_lines = []
    in_list = False
    
    for line in lines:
        line = line.rstrip()
        
        # Skip empty lines at start
        if not line and not html_lines:
            continue
            
        # Handle bullet points
        stripped = line.strip()
        if stripped.startswith('*'):
            if not in_list:
                html_lines.append('<ul style="margin: 12px 0; padding-left: 20px; color: #333;">')
                in_list = True
            
            item = stripped.lstrip('*').strip()
            # Clean common placeholders
            item = re.sub(r'\[Your.*?\]', '', item)
            item = re.sub(r'\[Contact.*?\]', '', item)
            if item:
                html_lines.append(f'<li style="margin-bottom: 6px;">{item}</li>')
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            
            if line:
                # Clean placeholders and format
                line = re.sub(r'\[.*?\]', '', line)
                line = line.strip()
                if line and not line.startswith('Best') and not line.startswith('Regards'):
                    html_lines.append(f'<p style="margin: 10px 0; line-height: 1.5;">{line}</p>')
    
    if in_list:
        html_lines.append('</ul>')
    
    # Build email
    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.5; color: #24292e; margin: 0; padding: 20px; background-color: #f6f8fa;">
    
    <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 6px; padding: 30px; border: 1px solid #e1e4e8;">
        {greeting}
        {''.join(html_lines)}
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eaecef; font-size: 14px; color: #6a737d;">
            <p style="margin: 0;">
                Best regards,<br>
                <strong>The Prudata Team</strong>
            </p>
            <p style="margin: 10px 0 0; font-size: 12px;">
                Reply directly to this email for questions.
            </p>
        </div>
    </div>
    
</body>
</html>"""
    
    return html_body

# ==================== MAIN FUNCTION ====================
def send_bulk_email(subject, body, recipients, recipient_names=None):
    """
    Sends bulk email with anti-spam optimizations.
    Returns: (success_bool, message_str, failed_emails_list)
    """
    # Validate inputs
    if not recipients:
        return False, "No recipients provided", []
    
    if not isinstance(recipients, list):
        recipients = [recipients] if recipients else []
    
    # Setup recipient names
    if recipient_names is None:
        recipient_names = [''] * len(recipients)
    elif not isinstance(recipient_names, list):
        recipient_names = [recipient_names]
    
    sent_count = 0
    failed_emails = []
    
    # 1. Get API key
    api_key = os.environ.get('SENDGRID_API_KEY')
    if not api_key:
        return False, "SendGrid API key is not configured.", []
    
    # 2. Get sender info - use a personal name
    from_email = os.environ.get("EMAIL", "prudata.tech@gmail.com")
    from_name = "Alex from Prudata"  # Personal name improves trust
    
    # 3. Clean subject - CRITICAL for spam filters
    def clean_subject(text):
        text = re.sub(r'\b(free|guarantee|winner|prize|discount|offer|buy now|click here|limited time|!!!)\b', 
                     '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Ensure not empty
        if not text or len(text) < 3:
            text = "Update from Prudata"
        
        # Limit length
        if len(text) > 60:
            text = text[:57] + "..."
        
        return text
    
    clean_subject_line = clean_subject(subject)
    
    # 4. Create SendGrid client
    try:
        sg_client = SendGridAPIClient(api_key)
    except Exception as e:
        return False, f"Failed to initialize SendGrid: {str(e)}", []
    
    # 5. Send emails
    for i, to_email in enumerate(recipients):
        if not validate_email(to_email):
            failed_emails.append((to_email, "Invalid email format"))
            continue
        
        to_email = to_email.strip().lower()
        current_name = recipient_names[i] if i < len(recipient_names) else ""
        
        try:
            # Rate limiting - 5 seconds between emails for warm-up
            wait_between_emails(5)
            
            # Prepare content
            html_body = format_email_body_to_html(body, current_name)
            
            # Create plain text version
            plain_text = re.sub(r'<[^>]+>', '', body)
            plain_text = re.sub(r'\[.*?\]', '', plain_text)
            plain_text = re.sub(r'\s+', ' ', plain_text).strip()
            
            # Build email with anti-spam configuration
            message = Mail(
                from_email=(from_email, from_name),  # Name + email improves trust
                to_emails=to_email,
                subject=clean_subject_line,
                html_content=html_body
            )
            
            # Add plain text version
            message.add_content(Content("text/plain", plain_text))
            
            # ANTI-SPAM CONFIGURATION:
            # 1. Reply-to header (reduces spam score)
            message.reply_to = from_email
            
            # 2. Disable tracking initially (marketing emails get penalized)
            message.tracking_settings = {
                "click_tracking": {"enable": False},
                "open_tracking": {"enable": False}
            }
            
            # 3. Add category for filtering
            message.category = "business_update"
            
            # Send email
            response = sg_client.send(message)
            
            if response.status_code == 202:
                sent_count += 1
                logging.info(f"✅ Email {i+1}/{len(recipients)} sent to: {to_email}")
            else:
                error_msg = f"SendGrid error: {response.status_code}"
                if response.body:
                    error_msg += f" - {response.body.decode('utf-8')[:100]}"
                failed_emails.append((to_email, error_msg))
                logging.error(f"❌ Failed to send to {to_email}: {error_msg}")
                
        except Exception as e:
            error_msg = str(e)
            failed_emails.append((to_email, error_msg))
            logging.error(f"❌ Exception sending to {to_email}: {error_msg}")
            continue
    
    # 6. Return results
    total = len(recipients)
    
    if len(failed_emails) == 0 and sent_count == total:
        return True, f"✅ Successfully sent all {sent_count} emails!", failed_emails
    else:
        msg = f"Sent {sent_count}/{total} emails"
        if failed_emails:
            msg += f" - {len(failed_emails)} failed"
        return False, msg, failed_emails