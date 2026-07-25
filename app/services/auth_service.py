from fastapi import HTTPException, status
from app.models.user import User, Profile
from app.schemas.user import UserCreate, UserLogin
from app.auth.security import get_password_hash, verify_password, create_access_token
from google.oauth2 import id_token
from google.auth.transport import requests
from app.config.config import settings
import secrets
import logging

logger = logging.getLogger(__name__)

class AuthService:
    
    @staticmethod
    async def register_user(user_in: UserCreate) -> User:
        # Check if user already exists
        existing_user = await User.find_one(User.email == user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The user with this email already exists in the system."
            )
            
        # Create new user
        hashed_password = get_password_hash(user_in.password)
        new_user = User(
            name=user_in.name,
            email=user_in.email,
            hashed_password=hashed_password
        )
        await new_user.insert()
        
        # Create an empty profile for the user
        new_profile = Profile(user_id=str(new_user.id))
        await new_profile.insert()
        
        return new_user

    @staticmethod
    async def authenticate(user_in: UserLogin):
        user = await User.find_one(User.email == user_in.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        if not verify_password(user_in.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
            
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
            
        # Create access token
        access_token = create_access_token(subject=str(user.id))
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }

    @staticmethod
    async def authenticate_google(token: str) -> dict:
        try:
            # The frontend is sending an OAuth Access Token, not an ID Token.
            # We verify it by fetching the user's profile info from Google.
            import urllib.request
            import json
            
            url = "https://www.googleapis.com/oauth2/v3/userinfo"
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            try:
                with urllib.request.urlopen(req) as response:
                    idinfo = json.loads(response.read().decode())
            except Exception as exc:
                raise ValueError(f"Failed to fetch user info from Google: {exc}")
            
            email = idinfo.get('email')
            name = idinfo.get('name')
            
            if not email:
                raise ValueError("Email not found in Google token")
                
            # Check if user exists
            user = await User.find_one(User.email == email)
            
            if not user:
                # Create a new user automatically
                # Generate a random password since they login via Google
                random_password = secrets.token_urlsafe(16)
                hashed_password = get_password_hash(random_password)
                
                user = User(
                    name=name or email.split('@')[0],
                    email=email,
                    hashed_password=hashed_password,
                    is_active=True
                )
                await user.insert()
                
                # Create profile
                new_profile = Profile(user_id=str(user.id))
                await new_profile.insert()
                
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inactive user"
                )
                
            # Create access token
            access_token = create_access_token(subject=str(user.id))
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": user
            }
        except ValueError as e:
            logger.error(f"Google token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Google token: {str(e)}"
            )

    @staticmethod
    async def forgot_password(email: str) -> None:
        user = await User.find_one(User.email == email)
        if not user:
            # Prevent user enumeration attacks by returning quietly, but log it
            logger.warning(f"Forgot password requested for non-existent email: {email}")
            return
            
        # Generate token
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        from datetime import datetime, timedelta
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        await user.save()
        
        # Send email
        await AuthService.send_reset_email(user.email, token)
        
    @staticmethod
    async def send_reset_email(email: str, token: str) -> None:
        # Construct reset link
        reset_link = f"http://localhost:5173/reset-password?token={token}"
        
        # Log to console so it is always accessible in dev
        logger.info(f"==================================================")
        logger.info(f"PASSWORD RESET LINK FOR {email}:")
        logger.info(f"{reset_link}")
        logger.info(f"==================================================")
        print(f"\n[Reset Link] {email}: {reset_link}\n")
        
        html_content = f"""
        <html>
          <body>
            <h2>Reset Your Password</h2>
            <p>You requested a password reset for your PrepAI account.</p>
            <p>Click the link below to set a new password. This link will expire in 1 hour.</p>
            <p><a href="{reset_link}" style="padding: 10px 20px; background-color: #5A36D6; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Password</a></p>
            <p>If you did not request this reset, you can safely ignore this email.</p>
          </body>
        </html>
        """

        # 1. Try sending via Resend API if configured
        if settings.RESEND_API_KEY:
            try:
                import urllib.request
                import json
                
                logger.info("Attempting to send email via Resend API...")
                headers = {
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                # Note: Resend Free tier (onboarding@resend.dev) can only send emails to your own email address
                data = {
                    "from": f"{settings.EMAILS_FROM_NAME} <onboarding@resend.dev>",
                    "to": [email],
                    "subject": "PrepAI - Reset Your Password",
                    "html": html_content
                }
                
                req = urllib.request.Request(
                    "https://api.resend.com/emails",
                    data=json.dumps(data).encode("utf-8"),
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(req) as response:
                    result = json.loads(response.read().decode())
                    logger.info(f"Successfully sent email via Resend API: {result}")
                return
            except Exception as e:
                logger.error(f"Failed to send email via Resend API: {e}")
                # Fall through to SMTP if Resend fails
        
        # 2. Try sending email via SMTP if configured
        if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            try:
                logger.info("Attempting to send email via SMTP...")
                message = MIMEMultipart("alternative")
                message["Subject"] = "PrepAI - Reset Your Password"
                message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL or settings.SMTP_USER}>"
                message["To"] = email
                message.attach(MIMEText(html_content, "html"))
                
                # Connect to SMTP server
                if settings.SMTP_SSL:
                    server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
                else:
                    server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
                    if settings.SMTP_TLS:
                        server.starttls()
                
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_USER, email, message.as_string())
                server.quit()
                logger.info(f"Successfully sent password reset email via SMTP to {email}")
                return
            except Exception as e:
                logger.error(f"Failed to send email via SMTP: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to send password reset email via SMTP. Please check your configuration."
                )

        # 3. Fallback warning if neither is set up
        logger.warning("Neither Resend API nor SMTP settings are configured in .env. Password reset link printed to console for local testing.")
        return

    @staticmethod
    async def reset_password_direct(email: str, new_password: str) -> None:
        user = await User.find_one(User.email == email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with this email not found"
            )
            
        hashed_password = get_password_hash(new_password)
        user.hashed_password = hashed_password
        # Clear reset token just in case
        user.reset_token = None
        user.reset_token_expires = None
        await user.save()
        logger.info(f"Password reset directly and successfully for user: {email}")
