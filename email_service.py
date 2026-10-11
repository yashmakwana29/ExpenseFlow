"""
Email Service for ExpenseFlow.
Handles SMTP delivery of One-Time Passwords (OTP) and Administrative Password Resets.
Uses Gmail SMTP with TLS encryption and clean, professional HTML templates.
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple
from config import SMTP_CONFIG, APP_NAME

def _create_smtp_connection():
    """Initializes and returns an authenticated SMTP connection."""
    server = smtplib.SMTP(SMTP_CONFIG["host"], SMTP_CONFIG["port"], timeout=10)
    if SMTP_CONFIG.get("use_tls", True):
        context = ssl.create_default_context()
        server.starttls(context=context)
    server.login(SMTP_CONFIG["user"], SMTP_CONFIG["password"])
    return server

def send_otp_email(to_email: str, otp_code: str, username: str = "") -> Tuple[bool, str]:
    """
    Sends a 6-digit OTP verification code to the user's email address during registration.
    Returns (True, "Success message") or (False, "Error message").
    """
    clean_to = to_email.strip().lower()
    subject = f"{otp_code} is your {APP_NAME} Verification Code"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0F172A; color: #F8FAFC; margin: 0; padding: 20px; }}
        .card {{ max-width: 480px; margin: 0 auto; background-color: #1E293B; border: 1px solid #334155; border-radius: 16px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
        .brand {{ color: #6366F1; font-size: 22px; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 8px; }}
        .title {{ color: #F8FAFC; font-size: 20px; font-weight: 700; margin-top: 0; margin-bottom: 12px; }}
        .text {{ color: #94A3B8; font-size: 14px; line-height: 1.6; margin-bottom: 24px; }}
        .otp-box {{ background: linear-gradient(135deg, #1E1B4B 0%, #312E81 100%); border: 1px solid #4F46E5; border-radius: 12px; padding: 20px; text-align: center; margin: 24px 0; }}
        .otp-number {{ font-family: 'Courier New', Courier, monospace; font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #38BDF8; margin: 0; }}
        .footer {{ font-size: 12px; color: #64748B; margin-top: 24px; border-top: 1px solid #334155; padding-top: 16px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="brand">✦ {APP_NAME}</div>
        <h2 class="title">Verify Your Email Address</h2>
        <p class="text">
          Hi{f' <b>{username}</b>' if username else ''},<br><br>
          Thank you for creating an account with <b>{APP_NAME}</b>. Use the one-time verification code below to complete your registration:
        </p>
        <div class="otp-box">
          <div class="otp-number">{otp_code}</div>
        </div>
        <p class="text">
          This verification code will expire in <b>10 minutes</b>. If you did not request this account registration, you can safely ignore this email.
        </p>
        <div class="footer">
          © {APP_NAME} Automated Security Service. Do not reply to this email.
        </div>
      </div>
    </body>
    </html>
    """

    plain_content = f"""
    {APP_NAME} Email Verification
    -----------------------------------
    Your verification code is: {otp_code}

    This code will expire in 10 minutes.
    If you did not request this account, please ignore this email.
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_CONFIG.get('sender_name', APP_NAME)} <{SMTP_CONFIG['user']}>"
    msg["To"] = clean_to

    msg.attach(MIMEText(plain_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        server = _create_smtp_connection()
        server.sendmail(SMTP_CONFIG["user"], clean_to, msg.as_string())
        server.quit()
        return True, f"Verification OTP successfully sent to {clean_to}"
    except Exception as e:
        return False, f"Failed to send verification email: {str(e)}"

def send_password_reset_email(to_email: str, username: str, new_password: str) -> Tuple[bool, str]:
    """
    Sends an account password reset notice containing the new administrative temporary password.
    """
    clean_to = to_email.strip().lower()
    subject = f"Your {APP_NAME} Password Has Been Reset by Admin"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0F172A; color: #F8FAFC; margin: 0; padding: 20px; }}
        .card {{ max-width: 480px; margin: 0 auto; background-color: #1E293B; border: 1px solid #334155; border-radius: 16px; padding: 32px; }}
        .brand {{ color: #6366F1; font-size: 22px; font-weight: 800; margin-bottom: 8px; }}
        .title {{ color: #F8FAFC; font-size: 20px; font-weight: 700; margin-top: 0; }}
        .text {{ color: #94A3B8; font-size: 14px; line-height: 1.6; }}
        .pwd-box {{ background: #0F172A; border: 1px dashed #6366F1; border-radius: 10px; padding: 16px; text-align: center; margin: 20px 0; }}
        .pwd-text {{ font-family: monospace; font-size: 22px; font-weight: bold; color: #10B981; }}
        .footer {{ font-size: 12px; color: #64748B; margin-top: 24px; border-top: 1px solid #334155; padding-top: 16px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="brand">✦ {APP_NAME}</div>
        <h2 class="title">Administrative Password Reset</h2>
        <p class="text">
          Hello <b>{username}</b>,<br><br>
          Your account password has been updated by the System Administrator. You can now log in using the temporary credentials below:
        </p>
        <div class="pwd-box">
          <div class="pwd-text">{new_password}</div>
        </div>
        <p class="text">
          <b>Security Notice:</b> Please log in to your account and change this password immediately in Settings.
        </p>
        <div class="footer">
          © {APP_NAME} Admin Control Console.
        </div>
      </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_CONFIG.get('sender_name', APP_NAME)} <{SMTP_CONFIG['user']}>"
    msg["To"] = clean_to

    msg.attach(MIMEText(f"Your new password for {username} is: {new_password}", "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        server = _create_smtp_connection()
        server.sendmail(SMTP_CONFIG["user"], clean_to, msg.as_string())
        server.quit()
        return True, f"Password reset email sent to {clean_to}"
    except Exception as e:
        return False, f"Failed to send reset email: {str(e)}"
