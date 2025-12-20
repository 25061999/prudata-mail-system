import os
import re
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Content
from rate_limiter import allow_send

def format_email_body_to_html(plain_text_body):
    """
    Converts plain text email body (from Groq AI) to clean HTML.
    Handles paragraphs and bullet points (*).
    """
    # Clean up the text first
    plain_text_body = plain_text_body.strip()
    
    # Split text by lines
    lines = plain_text_body.split('\n')
    html_lines = []
    in_list = False
    
    for line in lines:
        line = line.rstrip()  # Remove trailing whitespace
        
        # Check if line starts with a bullet point
        stripped_line = line.strip()
        if stripped_line.startswith('*'):
            # Start unordered list if we're not already in one
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            
            # Remove the '*' and any extra spaces, wrap in <li>
            list_item = stripped_line.lstrip('*').strip()
            html_lines.append(f'<li>{list_item}</li>')
        else:
            # If we were in a list and this line isn't a bullet, close the list
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            
            # Handle regular text (non-empty lines)
            if line:
                html_lines.append(f'<p>{line}</p>')
    
    # Close list if still open
    if in_list:
        html_lines.append('</ul>')
    
    # Create final HTML structure
    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        ul {{ margin: 10px 0; padding-left: 20px; }}
        li {{ margin-bottom: 5px; }}
        p {{ margin: 10px 0; }}
    </style>
</head>
<body>
{''.join(html_lines)}
<hr>
<p><small>Sent via Prudata Mail System</small></p>
</body>
</html>"""
    
    return html_body

def validate_email_format(email):
    """Basic email format validation"""
    if not email or not isinstance(email, str):
        return False
    
    email = email.strip().lower()
    
    # Simple but effective regex for email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def send_bulk_email(subject, body, recipients):
    """
    Sends bulk email using the SendGrid API.
    Returns: (success_bool, message_str, failed_emails_list)
    """
    # Validate inputs
    if not recipients:
        return False, "No recipients provided", []
    
    if not isinstance(recipients, list):
        recipients = [recipients] if recipients else []
    
    sent_count = 0
    failed_emails = []
    
    # 1. Get the API key from the environment
    api_key = os.environ.get('SENDGRID_API_KEY')
    if not api_key:
        error_msg = "SendGrid API key is not configured."
        logging.error(f"❌ {error_msg}")
        return False, error_msg, []
    
    # 2. Get sender email
    from_email = os.environ.get("EMAIL", "prudata.tech@gmail.com")
    if not validate_email_format(from_email):
        return False, f"Invalid sender email format: {from_email}", []
    
    # 3. Format the body to HTML and create plain text version
    try:
        html_body = format_email_body_to_html(body)
        # Create plain text version by removing HTML tags and extra spaces
        plain_body = re.sub(r'<[^>]+>', '', body)
        plain_body = re.sub(r'\s+', ' ', plain_body).strip()
    except Exception as e:
        logging.error(f"❌ Failed to format email body: {str(e)}")
        # Fallback to simple formatting
        html_body = f"<p>{body}</p>"
        plain_body = body
    
    # 4. Create SendGrid client
    try:
        sg_client = SendGridAPIClient(api_key)
    except Exception as e:
        error_msg = f"Failed to initialize SendGrid client: {str(e)}"
        logging.error(f"❌ {error_msg}")
        return False, error_msg, []
    
    # 5. Loop through recipients and send
    for to_email in recipients:
        # Validate email format
        if not validate_email_format(to_email):
            failed_emails.append((to_email, "Invalid email format"))
            logging.warning(f"⚠️ Skipped invalid email: {to_email}")
            continue
        
        to_email = to_email.strip().lower()
        
        try:
            allow_send(2)  # Respect rate limits (2 sec delay)
            
            # ✅ SIMPLE, RELIABLE APPROACH: Create Mail object with basic parameters
            message = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_body
            )
            
            # ✅ Add plain text content (important for deliverability)
            plain_content = Content("text/plain", plain_body)
            message.add_content(plain_content)
            
            # ✅ REMOVED: All complex Personalization and custom_arg code
            # ✅ REMOVED: Substitutions, custom headers, etc.
            
            # Send the email
            response = sg_client.send(message)
            
            # Check for success (HTTP 202 Accepted)
            if response.status_code == 202:
                sent_count += 1
                logging.info(f"✅ Email sent to: {to_email}")
            else:
                error_body = response.body.decode('utf-8') if response.body else "No details"
                error_msg = f"SendGrid Error {response.status_code}: {error_body}"
                failed_emails.append((to_email, error_msg))
                logging.error(f"❌ Failed to send to {to_email}: {error_msg}")
                
        except Exception as e:
            error_msg = str(e)
            failed_emails.append((to_email, error_msg))
            logging.error(f"❌ Exception sending to {to_email}: {error_msg}")
            continue
    
    # 6. Return results
    total_attempted = len(recipients)
    
    if len(failed_emails) == 0 and sent_count == total_attempted:
        success = True
        message = f"✅ Successfully sent all {sent_count} emails!"
    else:
        success = False
        failed_count = len(failed_emails)
        invalid_count = len([e for e in recipients if not validate_email_format(e)])
        message = f"📊 Sent {sent_count} of {total_attempted} emails. {failed_count} failed, {invalid_count} invalid."
    
    return success, message, failed_emails