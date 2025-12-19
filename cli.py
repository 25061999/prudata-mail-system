
import sys
import argparse
from email_generator import generate_email
from email_sender import send_bulk_email
from dotenv import load_dotenv

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Send bulk emails")
    parser.add_argument("--emails", required=True, help="Comma-separated email list")
    parser.add_argument("--purpose", required=True, help="Email purpose")
    parser.add_argument("--subject", required=True, help="Email subject")
    
    args = parser.parse_args()
    
    emails = [e.strip() for e in args.emails.split(",")]
    email_body = generate_email(args.purpose)
    
    success, message, failed = send_bulk_email(args.subject, email_body, emails)
    
    if success:
        print(f"✅ All {len(emails)} emails sent!")
    else:
        print(f"⚠️  {message}")
        if failed:
            print("Failed emails:")
            for email, error in failed:
                print(f"  - {email}: {error}")

if __name__ == "__main__":
    main()