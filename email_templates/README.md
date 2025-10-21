# Jiran Email Templates for ZeptoMail

This folder contains HTML email templates for Jiran's transactional emails, designed with Marrakesh souk-inspired branding.

## Templates

### 1. OTP Verification Email (`otp_verification.html`)

**Purpose**: Send one-time passwords for email verification during registration.

**Variables to Replace**:
- `{{OTP_CODE}}` - The 6-digit OTP code (e.g., "123456")
- `{{USER_EMAIL}}` - Recipient's email address
- `{{VERIFICATION_LINK}}` - Deep link to verify in app (e.g., "jiran://verify?code=123456&email=user@example.com")

**Design Features**:
- Souk Fire gradient header (Souk Red → Burnt Orange)
- Large, easy-to-read OTP code in monospace font
- 10-minute expiry timer notice
- Security warning box with golden border
- One-click verification button
- Mobile-responsive design

**Use Case**:
```
Trigger: User signs up for Jiran account
When: Immediately after registration form submission
Expected Action: User enters OTP in app or clicks verification link
```

---

### 2. Welcome Email (`welcome.html`)

**Purpose**: Onboard new users and introduce Jiran's key features after successful registration.

**Variables to Replace**:
- `{{USER_NAME}}` - User's first name or full name
- `{{APP_LINK}}` - Deep link to open the app (e.g., "jiran://home")
- `{{BROWSE_LINK}}` - Web link to browse products (e.g., "https://jiran.ae/browse")
- `{{IOS_APP_LINK}}` - App Store download link
- `{{ANDROID_APP_LINK}}` - Google Play download link
- `{{UNSUBSCRIBE_LINK}}` - Unsubscribe link (e.g., "https://jiran.ae/unsubscribe?token=...")
- `{{PRIVACY_LINK}}` - Privacy policy link (e.g., "https://jiran.ae/privacy")
- `{{TERMS_LINK}}` - Terms of service link (e.g., "https://jiran.ae/terms")

**Design Features**:
- Sunset gradient hero section (Souk Red → Burnt Orange → Souk Gold)
- 4 feature cards highlighting key app benefits
- Community stats banner (50K+ users, 200K+ products)
- Paradise Green CTA section with dual action buttons
- 5-point quick start tips with numbered badges
- App download buttons (iOS/Android)
- Comprehensive footer with links

**Use Case**:
```
Trigger: User successfully verifies email and completes registration
When: Immediately after OTP verification succeeds
Expected Action: User explores app features and creates first listing
```

---

## Brand Colors Used

### Primary Colors
- **Souk Red**: `#C1440E` - Headers, CTAs, live badges
- **Burnt Orange**: `#E87A3E` - Gradient accents
- **Souk Gold**: `#D4A745` - Premium badges, tips

### Secondary Colors
- **Paradise Green**: `#2D6A4F` - Trust, verification, success
- **Majorelle Blue**: `#2C5F8D` - Info, links, stats

### Neutrals
- **Sand**: `#FFF8F0` - Background
- **Clay**: `#8B7355` - Secondary text
- **Dark Wood**: `#2C1810` - Primary text

### Gradients
- **Souk Fire**: `linear-gradient(135deg, #C1440E 0%, #E87A3E 100%)`
- **Sunset**: `linear-gradient(135deg, #C1440E 0%, #E87A3E 40%, #D4A745 100%)`
- **Paradise Garden**: `linear-gradient(135deg, #2D6A4F 0%, #52B788 100%)`
- **Desert Sky**: `linear-gradient(135deg, #2C5F8D 0%, #4A6FA5 100%)`

---

## ZeptoMail Integration

### Sample Python Code (FastAPI)

```python
from zeptomail import ZeptoMail
import os

# Initialize ZeptoMail client
zepto = ZeptoMail(api_key=os.getenv("ZEPTOMAIL_API_KEY"))

# Send OTP Email
def send_otp_email(user_email: str, otp_code: str):
    with open("email_templates/otp_verification.html", "r") as f:
        html_template = f.read()

    # Replace variables
    html_body = html_template.replace("{{OTP_CODE}}", otp_code)
    html_body = html_body.replace("{{USER_EMAIL}}", user_email)
    html_body = html_body.replace(
        "{{VERIFICATION_LINK}}",
        f"https://jiran.ae/verify?code={otp_code}&email={user_email}"
    )

    # Send email
    zepto.send_email(
        from_email="noreply@jiran.ae",
        from_name="Jiran",
        to=[{"email": user_email}],
        subject="Verify Your Jiran Account - OTP Inside",
        html_body=html_body
    )

# Send Welcome Email
def send_welcome_email(user_email: str, user_name: str):
    with open("email_templates/welcome.html", "r") as f:
        html_template = f.read()

    # Replace variables
    html_body = html_template.replace("{{USER_NAME}}", user_name)
    html_body = html_body.replace("{{USER_EMAIL}}", user_email)
    html_body = html_body.replace("{{APP_LINK}}", "jiran://home")
    html_body = html_body.replace("{{BROWSE_LINK}}", "https://jiran.ae/browse")
    html_body = html_body.replace("{{IOS_APP_LINK}}", "https://apps.apple.com/app/jiran")
    html_body = html_body.replace("{{ANDROID_APP_LINK}}", "https://play.google.com/store/apps/details?id=ae.jiran")
    html_body = html_body.replace("{{UNSUBSCRIBE_LINK}}", f"https://jiran.ae/unsubscribe?email={user_email}")
    html_body = html_body.replace("{{PRIVACY_LINK}}", "https://jiran.ae/privacy")
    html_body = html_body.replace("{{TERMS_LINK}}", "https://jiran.ae/terms")

    # Send email
    zepto.send_email(
        from_email="hello@jiran.ae",
        from_name="Jiran Team",
        to=[{"email": user_email}],
        subject="Welcome to Jiran - Your Neighborhood Marketplace Awaits! 🎉",
        html_body=html_body
    )
```

---

## Testing

### Preview in Browser
1. Open `otp_verification.html` or `welcome.html` in a browser
2. Manually replace `{{VARIABLES}}` with sample data:
   - `{{OTP_CODE}}` → `123456`
   - `{{USER_NAME}}` → `Ahmed`
   - `{{USER_EMAIL}}` → `ahmed@example.com`

### Email Client Testing
Test rendering in:
- ✅ Gmail (web, iOS, Android)
- ✅ Apple Mail (macOS, iOS)
- ✅ Outlook (web, Windows, macOS)
- ✅ Yahoo Mail
- ✅ ProtonMail

### Mobile Responsiveness
- Templates use `max-width: 600px` for optimal mobile display
- Media queries adjust font sizes and layouts below 600px width
- Buttons stack vertically on mobile devices

---

## Compliance

### CAN-SPAM Act (US)
- ✅ Clear "From" name (Jiran / Jiran Team)
- ✅ Accurate subject lines
- ✅ Physical mailing address in footer
- ✅ Unsubscribe link in welcome email
- ✅ Transactional emails (OTP) exempt from unsubscribe

### GDPR (EU/UAE)
- ✅ Clear purpose statement ("You're receiving this email because...")
- ✅ Privacy policy link
- ✅ Data controller identified (Jiran, Dubai, UAE)
- ✅ Right to unsubscribe (marketing emails)

### UAE Telecommunications Regulations
- ✅ Sender identification
- ✅ Opt-out mechanism
- ✅ Legitimate business relationship

---

## File Structure

```
backend/
└── email_templates/
    ├── README.md                  # This file
    ├── otp_verification.html      # OTP email template
    └── welcome.html               # Welcome email template
```

---

## Variable Reference Table

| Variable | OTP Email | Welcome Email | Example Value |
|----------|-----------|---------------|---------------|
| `{{OTP_CODE}}` | ✅ | ❌ | `123456` |
| `{{USER_NAME}}` | ❌ | ✅ | `Ahmed Khan` |
| `{{USER_EMAIL}}` | ✅ | ✅ | `ahmed@example.com` |
| `{{VERIFICATION_LINK}}` | ✅ | ❌ | `jiran://verify?code=123456` |
| `{{APP_LINK}}` | ❌ | ✅ | `jiran://home` |
| `{{BROWSE_LINK}}` | ❌ | ✅ | `https://jiran.ae/browse` |
| `{{IOS_APP_LINK}}` | ❌ | ✅ | `https://apps.apple.com/app/jiran` |
| `{{ANDROID_APP_LINK}}` | ❌ | ✅ | `https://play.google.com/store/apps/details?id=ae.jiran` |
| `{{UNSUBSCRIBE_LINK}}` | ❌ | ✅ | `https://jiran.ae/unsubscribe?token=xyz` |
| `{{PRIVACY_LINK}}` | ❌ | ✅ | `https://jiran.ae/privacy` |
| `{{TERMS_LINK}}` | ❌ | ✅ | `https://jiran.ae/terms` |

---

## Support

For questions about email templates:
- **Design issues**: Contact design team
- **Technical integration**: Contact backend team
- **ZeptoMail API**: Check [ZeptoMail Documentation](https://www.zoho.com/zeptomail/help/)

---

**Last Updated**: January 2025
**Version**: 1.0
**Maintained by**: Jiran Development Team
