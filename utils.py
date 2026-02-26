import smtplib
from email.mime.text import MIMEText


def send_email(to_email, subject, body,
               smtp_server="smtp.gmail.com", smtp_port=587,
               username=None, password=None):
    if not (username and password):
        print("Email not configured.")
        return

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = username
    msg["To"] = to_email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
        print("Email sent to", to_email)


def send_sms(phone_number, message):
    # integrate actual SMS provider (e.g. Twilio) here later
    print(f"SMS to {phone_number}: {message}")
