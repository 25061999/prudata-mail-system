import os
import re
import logging
import time
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Content

# ==================== ENHANCED RATE LIMITER ====================
_last_sent_time = 0
_email_count_today = 0
_reset_time = time.time()

def wait_between_emails(delay_seconds=5):  # Increased to 5 seconds
    """
    Enhanced rate limiter with daily limits for domain warming.
    """
    global _last_sent_time, _email_count_today, _reset_time
    
    # Reset counter every 24 hours
    if time.time() - _reset_time > 86400:  # 24 hours
        _email_count_today = 0
        _reset_time = time.time()
    
    # Domain warming: Limit to 20 emails/day for first week
    if _email_count_today >= 20:
        logging.warning(f"⚠️ Daily limit reached ({_email_count_today}/20)")
        return False
    
    # Standard delay between emails
    current_time = time.time()
    time_since_last = current_time - _last_sent_time
    
    if time_since_last < delay_seconds:
        sleep_time = delay_seconds - time_since_last
        time.sleep(sleep_time)
    
    _last_sent_time = time.time()
    _email_count_today += 1
    return True

# ==================== ADVANCED HTML FORMATTER ====================
def format_email_body_to_html(plain_text_body, recipient_name=""):
    """
    Creates highly deliverable HTML emails with personalization.
    """
    # Clean and prepare text
    plain_text_body = plain_text_body.strip()
    
    # Personalize greeting
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
        
        # Skip empty lines at beginning
        if not line and len(html_lines) == 0:
            continue
            
        # Handle lists
        stripped_line = line.strip()
        if stripped_line.startswith('*'):
            if not in_list:
                html_lines.append('<ul style="margin: 15px 0; padding-left: 25px; color: #333;">')
                in_list = True
            list_item = stripped_line.lstrip('*').strip()
            html_lines.append(f'<li style="margin-bottom: 8px; line-height: 1.5;">{list_item}</li>')
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            
            if line:
                # Clean ALL placeholders
                line = re.sub(r'\[.*?\]', '', line)
                line = line.replace('Subject:', '').strip()
                
                if line and not line.startswith('Best') and not line.startswith('Regards'):
                    html_lines.append(f'<p style="margin: 12px 0; line-height: 1.6; color: #333;">{line}</p>')
    
    if in_list:
        html_lines.append('</ul>')
    
    # Build email with professional structure
    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email from Prudata</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1a202c; background-color: #f7fafc; margin: 0; padding: 0;">
    
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px 20px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px; font-weight: 600;">Prudata</h1>
            <p style="color: rgba(255, 255, 255, 0.9); margin: 5px 0 0; font-size: 14px;">Data Analytics Platform</p>
        </div>
        
        <!-- Content -->
        <div style="padding: 30px;">
            {greeting}
            {''.join(html_lines)}
            
            <!-- Professional Signature -->
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0;">
                <p style="margin: 5px 0; color: #4a5568;">
                    <strong>Best regards,</strong><br>
                    The Prudata Team
                </p>
                <p style="margin: 5px 0; font-size: 12px; color: #718096;">
                    <em>This email was sent from a verified domain. Reply directly to this email.</em>
                </p>
            </div>
        </div>
    </div>
    
</body>
</html>"""
    
    return html_body

# ==================== IMPROVED EMAIL SENDING ====================
def send_bulk_email(subject, body, recipients, recipient_names=None):
    """
    Advanced email sending with spam prevention.
    """
    if not recipients:
        return False, "No recipients provided", []
    
    if not isinstance(recipients, list):
        recipients = [recipients] if recipients else []
    
    if recipient_names is None:
        recipient_names = [''] * len(recipients)
    
    sent_count = 0
    failed_emails = []
    
    # 1. Validate environment
    api_key = os.environ.get('SENDGRID_API_KEY')
    if not api_key:
        return False, "SendGrid API key missing", []
    
    from_email = os.environ.get("EMAIL", "prudata.tech@gmail.com")
    from_name = "Prudata Team"
    
    # 2. Clean subject (CRITICAL for spam filters)
    subject = clean_subject(subject)
    
    # 3. Domain warming check
    if not can_send_more_today():
        return False, "Daily sending limit reached (20/day during warm-up)", []
    
    # 4. Initialize SendGrid
    try:
        sg_client = SendGridAPIClient(api_key)
    except Exception as e:
        return False, f"SendGrid init failed: {str(e)}", []
    
    # 5. Send to each recipient
    for i, to_email in enumerate(recipients):
        # Validate email
        if not validate_email(to_email):
            failed_emails.append((to_email, "Invalid email"))
            continue
        
        to_email = to_email.strip().lower()
        recipient_name = recipient_names[i] if i < len(recipient_names) else ""
        
        try:
            # Rate limiting
            if not wait_between_emails(5):
                failed_emails.append((to_email, "Rate limit exceeded"))
                continue
            
            # Format personalized content
            html_body = format_email_body_to_html(body, recipient_name)
            plain_body = create_plain_text(body, recipient_name)
            
            # Build email with anti-spam features
            message = build_email(
                from_email=from_email,
                from_name=from_name,
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                plain_body=plain_body
            )
            
            # Send
            response = sg_client.send(message)
            
            if response.status_code == 202:
                sent_count += 1
                log_success(to_email, sent_count)
            else:
                error = f"SendGrid error {response.status_code}"
                failed_emails.append((to_email, error))
                log_error(to_email, error)
                
        except Exception as e:
            failed_emails.append((to_email, str(e)))
            log_error(to_email, str(e))
            continue
    
    # Return results
    return format_results(sent_count, len(recipients), failed_emails)

# ==================== HELPER FUNCTIONS ====================
def clean_subject(subject):
    """Remove spam triggers from subject."""
    spam_words = ['free', 'guarantee', 'winner', 'prize', 'limited', 'act now', 
                  'click here', 'buy now', 'discount', 'offer', '!!!', '$$$']
    
    subject = subject.strip()
    for word in spam_words:
        subject = re.sub(f'\\b{word}\\b', '', subject, flags=re.IGNORECASE)
    
    subject = re.sub(r'\s+', ' ', subject).strip()
    
    # Ensure subject is not empty
    if not subject or len(subject) < 5:
        subject = "Message from Prudata Team"
    
    # Limit length
    if len(subject) > 50:
        subject = subject[:47] + "..."
    
    return subject

def validate_email(email):
    """Validate email format."""
    if not email or not isinstance(email, str):
        return False
    
    email = email.strip().lower()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def create_plain_text(body, recipient_name=""):
    """Create plain text version."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', body)
    
    # Remove placeholders
    text = re.sub(r'\[.*?\]', '', text)
    
    # Clean up
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Add personalized greeting
    if recipient_name:
        text = f"Hi {recipient_name},\n\n{text}"
    else:
        text = f"Hi,\n\n{text}"
    
    return text

def build_email(from_email, from_name, to_email, subject, html_body, plain_body):
    """Build email with all anti-spam headers."""
    message = Mail(
        from_email=(from_email, from_name),
        to_emails=to_email,
        subject=subject,
        html_content=html_body
    )
    
    # Plain text version
    message.add_content(Content("text/plain", plain_body))
    
    # CRITICAL ANTI-SPAM HEADERS
    message.reply_to = from_email
    
    # Disable tracking (looks less like marketing)
    message.tracking_settings = {
        "click_tracking": {"enable": False},
        "open_tracking": {"enable": False}
    }
    
    # Add headers for authentication
    message.headers = {
        "X-Priority": "3",  # Normal priority
        "X-Mailer": "Prudata Mail System",
        "List-Unsubscribe": f"<mailto:{from_email}?subject=unsubscribe>",
    }
    
    return message

def can_send_more_today():
    """Check daily sending limit for domain warming."""
    # First week: 20 emails/day
    # Second week: 50 emails/day  
    # Third week+: 100 emails/day
    return True  # Implement your logic here

def log_success(email, count):
    logging.info(f"✅ [{count}] Sent to {email}")

def log_error(email, error):
    logging.error(f"❌ Failed to send to {email}: {error}")

def format_results(sent, total, failed):
    if len(failed) == 0 and sent == total:
        return True, f"✅ Successfully sent all {sent} emails!", failed
    else:
        return False, f"📊 Sent {sent}/{total} emails. {len(failed)} failed.", failed