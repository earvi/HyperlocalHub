def send_email(to, subject, body):
    # In a real app, integrate with SMTP or SendGrid/AWS SES
    print(f"--- [MOCK EMAIL] ---")
    print(f"To: {to}")
    print(f"Subject: {subject}")
    print(f"Body: {body[:100]}...")
    print(f"--------------------")
    return True

def generate_digest_content(alerts):
    if not alerts:
        return "No significant alerts today."
    
    html = "<h1>Daily Local Digest</h1><ul>"
    for a in alerts:
        html += f"<li><strong>{a.title}</strong> - <a href='{a.url}'>Read</a><br>{a.summary[:100] if a.summary else ''}...</li>"
    html += "</ul>"
    return html
