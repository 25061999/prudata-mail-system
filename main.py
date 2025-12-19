from email_generator import generate_email
from email_sender import send_bulk_email
from dotenv import load_dotenv

load_dotenv()

emails = input("Enter emails (comma separated): ").split(",")
purpose = input("What is the purpose of the email? ")
subject = input("Email subject: ")

email_body = generate_email(purpose)
send_bulk_email(subject, email_body, emails)

print("✅ Emails sent successfully!")
