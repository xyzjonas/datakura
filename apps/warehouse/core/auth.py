from datetime import timedelta, datetime, timezone

import jwt
from django.conf import settings
from django.contrib.auth.models import User
from ninja.security import HttpBearer
from loguru import logger


# JWT Configuration
JWT_SECRET = getattr(settings, 'JWT_SECRET_KEY')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


class TokenAuth(HttpBearer):
    def authenticate(self, request, token) -> User | None:
        try:
            # Decode the JWT token
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

            # Check if it's an access token
            if payload.get('token_type') != 'access':
                return None

            # Get the user
            user = User.objects.get(id=payload['user_id'])
            return user

        except jwt.ExpiredSignatureError:
            # Token has expired
            return None
        except jwt.InvalidTokenError:
            # Invalid token or user doesn't exist
            return None
        except User.DoesNotExist:
            return None
        except Exception as exc:
            logger.exception("Failed to authenticate.", exc)
            # Any other error
            return None


def generate_access_token(user):
    """Generate JWT access token"""
    delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        'user_id': user.id,
        'username': user.username,
        'token_type': 'access',
        'exp': (datetime.now(tz=timezone.utc) + delta).timestamp(),
        'iat': datetime.now(tz=timezone.utc).timestamp()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def generate_refresh_token(user) -> str:
    """Generate JWT refresh token"""
    delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        'user_id': user.id,
        'token_type': 'refresh',
        'exp': (datetime.now(tz=timezone.utc) + delta).timestamp(),
        'iat': datetime.now(tz=timezone.utc).timestamp()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')
