import os
import re
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Content
from rate_limiter import allow_send

def format_email_body_to_html(plain_text_body):
    """
    Converts plain text email body (from Groq AI) to professional HTML.
    Handles paragraphs, bullet points (*), and preserves important formatting.
    """
    # Clean up the text first
    plain_text_body = plain_text_body.strip()
    
    # Split text by lines
    lines = plain_text_body.split('\n')
    html_lines = []
    in_list = False
    in_paragraph = False
    
    for line in lines:
        line = line.rstrip()  # Remove trailing whitespace
        
        # Skip completely empty lines between paragraphs
        if not line and not in_paragraph:
            continue
            
        # Check if line starts with a bullet point
        if line.strip().startswith('*'):
            # Start unordered list if we're not already in one
            if not in_list:
                html_lines.append('<ul style="margin: 15px 0; padding-left: 25px;">')
                in_list = True
            
            # Remove the '*' and any extra spaces, wrap in <li>
            list_item = line.strip().lstrip('*').strip()
            html_lines.append(f'  <li style="margin-bottom: 8px;">{list_item}</li>')
            in_paragraph = True
        else:
            # If we were in a list and this line isn't a bullet, close the list
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            
            # Handle regular text
            if line:
                # Convert [Placeholders] to highlighted text
                line = re.sub(r'\[(.*?)\]', r'<strong style="color: #2c5282;">[\1]</strong>', line)
                
                # Add paragraph tags for non-empty lines
                html_lines.append(f'<p style="margin: 12px 0; line-height: 1.6;">{line}</p>')
                in_paragraph = True
            elif in_paragraph:
                # Empty line after content = paragraph break
                html_lines.append('</p><p style="margin: 12px 0;">')
    
    # Close list if still open
    if in_list:
        html_lines.append('</ul>')
    
    # Create final HTML structure
    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #2d3748; background-color: #f7fafc; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; padding: 30px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
        {"".join(html_lines)}
        <div style="margin-top: 25px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 14px; color: #718096;">
            <p>This email was sent by Prudata Mail System.</p>
        </div>
    </div>
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
    
    # 3. Format the body to HTML
    try:
        html_body = format_email_body_to_html(body)
        plain_body = re.sub(r'<[^>]+>', '', body)  # Create plain text version
        plain_body = re.sub(r'\s+', ' ', plain_body).strip()
    except Exception as e:
        logging.error(f"❌ Failed to format email body: {str(e)}")
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
            
            # Create the email message with both HTML and plain text
            message = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject
            )
            
            # Add both HTML and plain text content
            message.content = [
                Content("text/html", html_body),
                Content("text/plain", plain_body)
            ]
            
            # Optional: Add custom headers for tracking
            message.custom_arg = {
                "campaign": "prudata_mail",
                "sent_via": "flask_app"
            }
            
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
    
    # 6. Return results with detailed statistics
    total_attempted = len(recipients)
    invalid_emails = len([e for e in recipients if not validate_email_format(e)])
    
    if len(failed_emails) == 0 and sent_count == total_attempted:
        success = True
        if invalid_emails > 0:
            message = f"✅ Sent {sent_count} emails. Skipped {invalid_emails} invalid addresses."
        else:
            message = f"✅ Successfully sent all {sent_count} emails!"
    else:
        success = False
        failed_count = len(failed_emails)
        message = f"📊 Sent {sent_count} of {total_attempted} emails. {failed_count} failed, {invalid_emails} invalid."
    
    # Add more details to the return message
    details = {
        "sent": sent_count,
        "failed": len(failed_emails),
        "invalid": invalid_emails,
        "total": total_attempted
    }
    
    logging.info(f"📧 Email batch completed: {message}")
    return success, f"{message} | Details: {details}", failed_emails