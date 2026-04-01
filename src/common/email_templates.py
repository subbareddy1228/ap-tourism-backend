"""
common/email_templates.py
HTML email templates used across the project.
All templates return ready-to-send HTML strings.
"""


def otp_email_template(otp: str, purpose: str = "verify_email") -> str:
    """
    Standard OTP email HTML template.
    Used by auth_service for email verification.

    Args:
        otp:     6-digit OTP code
        purpose: verify_email | forgot_password | register

    Returns:
        HTML string ready to send via SendGrid
    """
    purpose_labels = {
        "verify_email":    "verify your email address",
        "forgot_password": "reset your password",
        "register":        "complete your registration",
    }
    action = purpose_labels.get(purpose, "complete your action")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 0;">
      <table width="520" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:8px;overflow:hidden;
                    box-shadow:0 2px 8px rgba(0,0,0,0.08);">
        <tr>
          <td style="background:#1a56db;padding:28px 40px;">
            <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:600;">
              AP Travel &amp; Temple Tourism
            </h1>
          </td>
        </tr>
        <tr>
          <td style="padding:36px 40px;">
            <p style="margin:0 0 8px;color:#374151;font-size:15px;line-height:1.6;">
              Use the OTP below to <strong>{action}</strong>.
            </p>
            <p style="margin:0 0 24px;color:#6b7280;font-size:13px;">
              Expires in <strong>5 minutes</strong>. Do not share with anyone.
            </p>
            <div style="margin:28px 0;text-align:center;">
              <span style="display:inline-block;background:#f0f4ff;
                           border:2px dashed #1a56db;border-radius:8px;
                           padding:18px 40px;font-size:36px;font-weight:700;
                           letter-spacing:12px;color:#1a56db;">{otp}</span>
            </div>
            <p style="margin:0;color:#6b7280;font-size:13px;line-height:1.6;">
              If you did not request this, please ignore this email.
              Your account is safe.
            </p>
          </td>
        </tr>
        <tr>
          <td style="background:#f9fafb;padding:20px 40px;
                     border-top:1px solid #e5e7eb;">
            <p style="margin:0;color:#9ca3af;font-size:12px;">
              AP Travel &amp; Temple Tourism Platform &nbsp;|&nbsp;
              Automated message — please do not reply.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def welcome_email_template(name: str) -> str:
    """Welcome email for new users."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;padding:20px;">
  <div style="background:#1a56db;padding:28px 40px;border-radius:8px 8px 0 0;">
    <h1 style="margin:0;color:#fff;font-size:22px;">Welcome to AP Tourism!</h1>
  </div>
  <div style="background:#fff;padding:36px 40px;border:1px solid #e5e7eb;">
    <p style="color:#374151;font-size:15px;">Hi <strong>{name}</strong>,</p>
    <p style="color:#374151;font-size:15px;line-height:1.6;">
      Welcome to AP Travel &amp; Temple Tourism — your guide to
      Andhra Pradesh's temples and destinations.
    </p>
    <p style="color:#374151;font-size:15px;">
      Start exploring at <a href="https://aptourism.ap.gov.in" style="color:#1a56db;">
      aptourism.ap.gov.in</a>
    </p>
  </div>
  <div style="background:#f9fafb;padding:20px 40px;border:1px solid #e5e7eb;
              border-top:none;border-radius:0 0 8px 8px;">
    <p style="margin:0;color:#9ca3af;font-size:12px;">
      AP Travel &amp; Temple Tourism Platform &nbsp;|&nbsp; Automated message.
    </p>
  </div>
</body>
</html>"""


def booking_confirmation_template(booking_number: str, amount: float) -> str:
    """Booking confirmation email."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;padding:20px;">
  <div style="background:#16a34a;padding:28px 40px;border-radius:8px 8px 0 0;">
    <h1 style="margin:0;color:#fff;font-size:22px;">Booking Confirmed ✓</h1>
  </div>
  <div style="background:#fff;padding:36px 40px;border:1px solid #e5e7eb;">
    <p style="color:#374151;font-size:15px;line-height:1.6;">
      Your booking <strong>{booking_number}</strong> has been confirmed.
    </p>
    <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
                padding:20px;margin:20px 0;text-align:center;">
      <p style="margin:0;color:#15803d;font-size:14px;">Total Amount</p>
      <p style="margin:8px 0 0;color:#15803d;font-size:28px;font-weight:700;">
        &#8377;{amount:.2f}
      </p>
    </div>
    <p style="color:#374151;font-size:15px;">
      Thank you for choosing AP Tourism!
    </p>
  </div>
  <div style="background:#f9fafb;padding:20px 40px;border:1px solid #e5e7eb;
              border-top:none;border-radius:0 0 8px 8px;">
    <p style="margin:0;color:#9ca3af;font-size:12px;">AP Tourism Platform</p>
  </div>
</body>
</html>"""