import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Content
from rate_limiter import allow_send

def send_bulk_email(subject, body, recipients):
    """
    Sends bulk email using the SendGrid API.
    Returns: (success_bool, message_str, failed_emails_list)
    """
    sent_count = 0
    failed_emails = []
    
    # 1. Get the API key from the environment
    api_key = os.environ.get('SENDGRID_API_KEY')
    if not api_key:
        error_msg = "SendGrid API key is not configured."
        logging.error(f"❌ {error_msg}")
        return False, error_msg, []
    
    # 2. Create the SendGrid client
    sg_client = SendGridAPIClient(api_key)
    from_email = os.environ.get("EMAIL", "prudata.tech@gmail.com")  # Your sender email
    
    # 3. Loop through recipients and send
    for to_email in recipients:
        try:
            allow_send(2)  # Respect rate limits (2 sec delay between sends)
            
            # Create the email message
            message = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                html_content=body  # SendGrid handles both HTML and plain text well
            )
            
            # Send the email
            response = sg_client.send(message)
            
            # Check for success (HTTP 202 Accepted)
            if response.status_code == 202:
                sent_count += 1
                logging.info(f"✅ Email sent to: {to_email}")
            else:
                # Log the error from SendGrid
                error_body = response.body.decode('utf-8') if response.body else "No error details"
                failed_emails.append((to_email, f"SendGrid Error {response.status_code}: {error_body}"))
                logging.error(f"❌ Failed to send to {to_email}: Status {response.status_code}")
                
        except Exception as e:
            failed_emails.append((to_email, str(e)))
            logging.error(f"❌ Exception sending to {to_email}: {str(e)}")
            continue  # Continue with the next email
    
    # 4. Return results to app.py
    success = (len(failed_emails) == 0 and sent_count > 0)
    if success:
        message = f"All {sent_count} emails sent successfully!"
    else:
        message = f"Sent {sent_count} of {len(recipients)} emails. {len(failed_emails)} failed."
    
    return success, message, failed_emails