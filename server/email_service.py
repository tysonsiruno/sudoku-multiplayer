"""
Email Service for Minesweeper Multiplayer
Using SendGrid for email delivery
"""

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import os

# SendGrid Configuration
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@minesweeper.com')
APP_NAME = 'Minesweeper Multiplayer'
DOMAIN = os.environ.get('DOMAIN', 'http://localhost:5000')


def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """
    Send an email using SendGrid

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content of the email

    Returns:
        True if email sent successfully, False otherwise
    """
    if not SENDGRID_API_KEY:
        print('WARNING: SENDGRID_API_KEY not set. Email not sent.')
        print(f'Would have sent to {to_email}: {subject}')
        return False

    try:
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        return response.status_code in [200, 201, 202]

    except Exception as e:
        print(f'Error sending email: {e}')
        return False


def send_verification_email(to_email: str, username: str, token: str) -> bool:
    """
    Send email verification email

    Args:
        to_email: User's email address
        username: User's username
        token: Verification token

    Returns:
        True if email sent successfully
    """
    verify_link = f"{DOMAIN}/verify-email?token={token}"

    subject = f'Verify your email - {APP_NAME}'

    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }}
            .content {{
                background: #f5f5f5;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }}
            .button {{
                display: inline-block;
                padding: 15px 30px;
                background: #667eea;
                color: white !important;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                font-size: 0.9em;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎮 {APP_NAME} 🎮</h1>
        </div>
        <div class="content">
            <h2>Welcome, {username}!</h2>
            <p>Thank you for signing up! Please verify your email address to start playing.</p>
            <p>Click the button below to verify your email:</p>
            <a href="{verify_link}" class="button">Verify Email Address</a>
            <p>Or copy and paste this link into your browser:</p>
            <p style="background: white; padding: 10px; border-radius: 5px; word-break: break-all;">
                {verify_link}
            </p>
            <p><strong>This link will expire in 24 hours.</strong></p>
            <p>If you didn't create an account, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>© 2025 {APP_NAME}. All rights reserved.</p>
        </div>
    </body>
    </html>
    '''

    return send_email(to_email, subject, html_content)


def send_password_reset_email(to_email: str, username: str, token: str) -> bool:
    """
    Send password reset email

    Args:
        to_email: User's email address
        username: User's username
        token: Password reset token

    Returns:
        True if email sent successfully
    """
    reset_link = f"{DOMAIN}/reset-password?token={token}"

    subject = f'Reset your password - {APP_NAME}'

    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }}
            .content {{
                background: #f5f5f5;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }}
            .button {{
                display: inline-block;
                padding: 15px 30px;
                background: #667eea;
                color: white !important;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                margin: 20px 0;
            }}
            .warning {{
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                font-size: 0.9em;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔐 Password Reset 🔐</h1>
        </div>
        <div class="content">
            <h2>Hi {username},</h2>
            <p>We received a request to reset your password for your {APP_NAME} account.</p>
            <p>Click the button below to set a new password:</p>
            <a href="{reset_link}" class="button">Reset Password</a>
            <p>Or copy and paste this link into your browser:</p>
            <p style="background: white; padding: 10px; border-radius: 5px; word-break: break-all;">
                {reset_link}
            </p>
            <p><strong>This link will expire in 1 hour.</strong></p>
            <div class="warning">
                <strong>⚠️ Important:</strong>
                <p>If you didn't request this password reset, please ignore this email and your password will remain unchanged.</p>
                <p>If you're concerned about your account security, please contact support.</p>
            </div>
        </div>
        <div class="footer">
            <p>© 2025 {APP_NAME}. All rights reserved.</p>
        </div>
    </body>
    </html>
    '''

    return send_email(to_email, subject, html_content)


def send_account_locked_email(to_email: str, username: str, locked_minutes: int) -> bool:
    """
    Send account locked notification email

    Args:
        to_email: User's email address
        username: User's username
        locked_minutes: Number of minutes account is locked for

    Returns:
        True if email sent successfully
    """
    subject = f'Account locked - {APP_NAME}'

    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: #e74c3c;
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }}
            .content {{
                background: #f5f5f5;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }}
            .warning {{
                background: #ffebee;
                border-left: 4px solid #e74c3c;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                font-size: 0.9em;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔒 Account Locked 🔒</h1>
        </div>
        <div class="content">
            <h2>Hi {username},</h2>
            <div class="warning">
                <p><strong>Your account has been temporarily locked due to multiple failed login attempts.</strong></p>
                <p>For your security, you won't be able to log in for the next <strong>{locked_minutes} minutes</strong>.</p>
            </div>
            <p>If you forgot your password, you can reset it after the lockout period expires.</p>
            <p>If you didn't attempt to log in, please contact support immediately as your account may be compromised.</p>
        </div>
        <div class="footer">
            <p>© 2025 {APP_NAME}. All rights reserved.</p>
        </div>
    </body>
    </html>
    '''

    return send_email(to_email, subject, html_content)


def send_welcome_email(to_email: str, username: str) -> bool:
    """
    Send welcome email after successful verification

    Args:
        to_email: User's email address
        username: User's username

    Returns:
        True if email sent successfully
    """
    subject = f'Welcome to {APP_NAME}!'

    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }}
            .content {{
                background: #f5f5f5;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }}
            .feature {{
                background: white;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
                border-left: 4px solid #667eea;
            }}
            .button {{
                display: inline-block;
                padding: 15px 30px;
                background: #667eea;
                color: white !important;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                font-size: 0.9em;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎉 Welcome to {APP_NAME}! 🎉</h1>
        </div>
        <div class="content">
            <h2>Hi {username}!</h2>
            <p>Your email has been verified successfully! You're all set to start playing.</p>

            <h3>🎮 Game Modes Available:</h3>
            <div class="feature">
                <strong>Standard</strong> - Classic minesweeper race
            </div>
            <div class="feature">
                <strong>Russian Roulette</strong> - Turn-based, no numbers shown!
            </div>
            <div class="feature">
                <strong>Time Bomb ⏰</strong> - Race against the clock
            </div>
            <div class="feature">
                <strong>Survival 🏃</strong> - Endless challenge, how far can you go?
            </div>

            <a href="{DOMAIN}" class="button">Start Playing Now!</a>

            <p>Good luck and have fun! 💣</p>
        </div>
        <div class="footer">
            <p>© 2025 {APP_NAME}. All rights reserved.</p>
        </div>
    </body>
    </html>
    '''

    return send_email(to_email, subject, html_content)
