from datetime import datetime, timedelta, timezone
import os

from jose import jwt, JWTError, ExpiredSignatureError
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from authlib.integrations.starlette_client import OAuth

from app.database import get_db
from app import models


# =========================================================
# PASSWORD HASHING
# =========================================================

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    password: str,
    hashed_password: str
) -> bool:
    return password_hash.verify(
        password,
        hashed_password
    )


# =========================================================
# JWT CONFIGURATION
# =========================================================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "your-super-secret-key-change-this"
)

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60


# =========================================================
# CREATE APPLICATION JWT
# =========================================================

def create_access_token(user_id: int) -> str:
    """
    Create the JWT used by the Notes application.

    The JWT contains:
        sub = local database user ID
        exp = expiration time
    """

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": str(user_id),
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    print(
        f"JWT created for user_id={user_id}"
    )

    return token


# =========================================================
# OAUTH2 BEARER TOKEN
# =========================================================

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/login"
)


# =========================================================
# GET CURRENT USER
# =========================================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Validate the application's JWT and return
    the corresponding database user.
    """

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer"
        },
    )

    # -----------------------------------------------------
    # DEBUG: CONFIRM TOKEN WAS RECEIVED
    # -----------------------------------------------------

    if not token:
        print("AUTH ERROR: No bearer token received")
        raise credentials_exception

    print(
        "AUTH: Bearer token received "
        f"(length={len(token)})"
    )

    # -----------------------------------------------------
    # DECODE JWT
    # -----------------------------------------------------

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        print(
            "AUTH: JWT decoded successfully"
        )

        # -------------------------------------------------
        # GET USER ID FROM SUB CLAIM
        # -------------------------------------------------

        user_id = payload.get("sub")

        print(
            f"AUTH: JWT sub={user_id}"
        )

        if user_id is None:
            print(
                "AUTH ERROR: JWT is missing 'sub' claim"
            )

            raise credentials_exception

        # -------------------------------------------------
        # CONVERT USER ID TO INTEGER
        # -------------------------------------------------

        try:

            user_id = int(user_id)

        except (ValueError, TypeError):

            print(
                "AUTH ERROR: Invalid user ID in JWT:",
                user_id
            )

            raise credentials_exception

    # -----------------------------------------------------
    # TOKEN EXPIRED
    # -----------------------------------------------------

    except ExpiredSignatureError:

        print(
            "AUTH ERROR: JWT token has expired"
        )

        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # -----------------------------------------------------
    # INVALID JWT
    # -----------------------------------------------------

    except JWTError as e:

        print(
            "AUTH ERROR: JWT validation failed:",
            repr(e)
        )

        raise credentials_exception

    # -----------------------------------------------------
    # FIND USER IN DATABASE
    # -----------------------------------------------------

    user = (
        db.query(models.User)
        .filter(
            models.User.id == user_id
        )
        .first()
    )

    # -----------------------------------------------------
    # USER DOES NOT EXIST
    # -----------------------------------------------------

    if user is None:

        print(
            "AUTH ERROR: User does not exist:",
            user_id
        )

        raise credentials_exception

    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    print(
        "AUTH SUCCESS: "
        f"user_id={user.id}, "
        f"email={user.email}"
    )

    return user


# =========================================================
# GOOGLE OAUTH CONFIGURATION
# =========================================================

GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID"
)

GOOGLE_CLIENT_SECRET = os.getenv(
    "GOOGLE_CLIENT_SECRET"
)

GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8000/auth/google/callback"
)


# =========================================================
# AUTHLIB OAUTH CLIENT
# =========================================================

oauth = OAuth()


oauth.register(
    name="google",

    client_id=GOOGLE_CLIENT_ID,

    client_secret=GOOGLE_CLIENT_SECRET,

    server_metadata_url=(
        "https://accounts.google.com/"
        ".well-known/openid-configuration"
    ),

    client_kwargs={
        "scope": "openid email profile"
    },
)