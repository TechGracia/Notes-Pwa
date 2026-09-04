from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from urllib.parse import urlencode

from app.database import get_db
from app import models, schemas

from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    oauth,
    SECRET_KEY,
    GOOGLE_REDIRECT_URI,
)


# =========================================================
# CONFIGURATION
# =========================================================

FRONTEND_URL = "http://localhost:5173"
FRONTEND_LOGIN_URL = f"{FRONTEND_URL}/login"

# Backend URL used by the frontend
BACKEND_URL = "http://127.0.0.1:8000"


# =========================================================
# APP
# =========================================================

app = FastAPI()


# =========================================================
# SESSION MIDDLEWARE
# REQUIRED FOR GOOGLE OAUTH / AUTHLIB STATE
# =========================================================

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=3600,
    same_site="lax",
    https_only=False,
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# TEST ENDPOINT
# =========================================================

@app.get("/")
def root():
    return {
        "message": "Notes API is running"
    }


# =========================================================
# DATABASE TEST
# =========================================================

@app.get("/database-test")
def database_test(
    db: Session = Depends(get_db)
):
    from sqlalchemy import text

    result = db.execute(
        text("SELECT 1")
    )

    value = result.scalar()

    return {
        "database": "connected",
        "result": value,
    }


# =========================================================
# USER REGISTRATION
# =========================================================

@app.post(
    "/users",
    response_model=schemas.UserResponse
)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    email = user.email.strip().lower()

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email is required"
        )

    if len(user.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters"
        )

    existing_user = (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    new_user = models.User(
        email=email,
        hashed_password=hash_password(user.password),
        auth_provider="local",
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# =========================================================
# EMAIL / PASSWORD LOGIN
# =========================================================

@app.post(
    "/login",
    response_model=schemas.TokenResponse
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    email = form_data.username.strip().lower()

    existing_user = (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

    if not existing_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Google-only users do not have a local password.
    if existing_user.hashed_password is None:
        raise HTTPException(
            status_code=401,
            detail=(
                "This account uses Google login. "
                "Please continue with Google."
            )
        )

    if not verify_password(
        form_data.password,
        existing_user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        existing_user.id
    )

    print(
        f"Local login successful: "
        f"user_id={existing_user.id}, "
        f"email={existing_user.email}"
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# =========================================================
# GET CURRENT USER
# =========================================================

@app.get(
    "/me",
    response_model=schemas.UserResponse
)
def get_me(
    current_user: models.User = Depends(get_current_user)
):
    print(
        f"/me authenticated successfully: "
        f"user_id={current_user.id}, "
        f"email={current_user.email}"
    )

    return current_user


# =========================================================
# GOOGLE OAUTH LOGIN
# =========================================================

@app.get("/auth/google")
async def google_login(
    request: Request
):
    """
    Start Google OAuth.

    Authlib stores the OAuth state in the Starlette
    session. SessionMiddleware is therefore required.
    """

    return await oauth.google.authorize_redirect(
        request,
        GOOGLE_REDIRECT_URI,
    )


# =========================================================
# GOOGLE OAUTH CALLBACK
# =========================================================

@app.get("/auth/google/callback")
async def google_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Google OAuth callback.

    Flow:

    1. Exchange Google's authorization code.
    2. Get verified Google user information.
    3. Find/create the local Notes user.
    4. Create our own Notes JWT.
    5. Redirect to Svelte with the Notes JWT.
    """

    try:

        # -----------------------------------------------------
        # 1. EXCHANGE GOOGLE AUTHORIZATION CODE
        # -----------------------------------------------------

        token = await oauth.google.authorize_access_token(
            request
        )

        print("Google OAuth token received.")


        # -----------------------------------------------------
        # 2. GET GOOGLE USER INFORMATION
        # -----------------------------------------------------

        user_info = token.get("userinfo")

        # Fallback if Authlib does not automatically
        # provide userinfo.
        if not user_info:
            try:
                user_info = await oauth.google.userinfo(
                    token=token
                )

            except Exception as userinfo_error:
                print(
                    "Google userinfo request failed:",
                    repr(userinfo_error)
                )

                user_info = None

        if not user_info:
            raise HTTPException(
                status_code=400,
                detail="Could not retrieve Google user information"
            )


        # -----------------------------------------------------
        # 3. EXTRACT GOOGLE IDENTITY
        # -----------------------------------------------------

        google_id = user_info.get("sub")
        email = user_info.get("email")

        email_verified = user_info.get(
            "email_verified",
            False
        )

        print(
            "Google user info: "
            f"google_id={google_id}, "
            f"email={email}, "
            f"verified={email_verified}"
        )


        # -----------------------------------------------------
        # 4. VALIDATE GOOGLE INFORMATION
        # -----------------------------------------------------

        if not google_id:
            raise HTTPException(
                status_code=400,
                detail="Google did not provide a user ID"
            )

        if not email:
            raise HTTPException(
                status_code=400,
                detail="Google did not provide an email"
            )

        if not email_verified:
            raise HTTPException(
                status_code=400,
                detail="Google email is not verified"
            )

        email = email.strip().lower()
        google_id = str(google_id)


        # -----------------------------------------------------
        # 5. FIND USER BY GOOGLE ID
        # -----------------------------------------------------

        user = (
            db.query(models.User)
            .filter(
                models.User.google_id == google_id
            )
            .first()
        )


        # -----------------------------------------------------
        # 6. IF NOT FOUND, FIND USER BY EMAIL
        # -----------------------------------------------------

        if not user:
            user = (
                db.query(models.User)
                .filter(
                    models.User.email == email
                )
                .first()
            )


        # -----------------------------------------------------
        # 7. EXISTING USER
        # -----------------------------------------------------

        if user:

            # Link Google account if it is not already linked.
            if user.google_id is None:
                user.google_id = google_id

            # If the account does not have a local password,
            # mark it as Google authentication.
            if user.hashed_password is None:
                user.auth_provider = "google"

            db.commit()
            db.refresh(user)

            print(
                "Existing user found: "
                f"user_id={user.id}, "
                f"email={user.email}"
            )


        # -----------------------------------------------------
        # 8. CREATE NEW GOOGLE USER
        # -----------------------------------------------------

        else:

            user = models.User(
                email=email,
                hashed_password=None,
                google_id=google_id,
                auth_provider="google",
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            print(
                "New Google user created: "
                f"user_id={user.id}, "
                f"email={user.email}"
            )


        # -----------------------------------------------------
        # 9. CREATE OUR APPLICATION JWT
        # -----------------------------------------------------

        access_token = create_access_token(
            user.id
        )

        print(
            "Notes JWT created successfully: "
            f"user_id={user.id}"
        )

        # IMPORTANT DEBUG INFORMATION
        print(
            "JWT will be sent to frontend."
        )


        # -----------------------------------------------------
        # 10. REDIRECT TO FRONTEND
        # -----------------------------------------------------

        query_string = urlencode({
            "token": access_token
        })

        frontend_url = (
            f"{FRONTEND_LOGIN_URL}"
            f"?{query_string}"
        )

        print(
            "Redirecting Google user to:",
            frontend_url.split("?")[0]
        )

        return RedirectResponse(
            url=frontend_url,
            status_code=302,
        )


    # =========================================================
    # EXPECTED AUTHENTICATION ERRORS
    # =========================================================

    except HTTPException:
        raise


    # =========================================================
    # UNEXPECTED GOOGLE OAUTH ERROR
    # =========================================================

    except Exception as e:

        print(
            "Google OAuth error:",
            repr(e)
        )

        return RedirectResponse(
            url=(
                f"{FRONTEND_LOGIN_URL}"
                "?error=google_login_failed"
            ),
            status_code=302,
        )


# =========================================================
# CHANGE PASSWORD
# =========================================================

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@app.put("/change-password")
def change_password(
    password_data: ChangePasswordRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # Google-only accounts don't have local passwords.
    if current_user.hashed_password is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "This account uses Google login and "
                "does not have a local password."
            )
        )

    # Verify current password.
    if not verify_password(
        password_data.current_password,
        current_user.hashed_password
    ):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )

    # Minimum password length.
    if len(password_data.new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="New password must be at least 6 characters"
        )

    # New password must be different.
    if verify_password(
        password_data.new_password,
        current_user.hashed_password
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "New password must be different "
                "from the current password"
            )
        )

    current_user.hashed_password = hash_password(
        password_data.new_password
    )

    db.commit()
    db.refresh(current_user)

    return {
        "message": "Password changed successfully"
    }


# =========================================================
# FORGOT PASSWORD
# =========================================================

class ForgotPasswordRequest(BaseModel):
    email: str
    new_password: str


@app.put("/forgot-password")
def forgot_password(
    password_data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):

    email = password_data.email.strip().lower()

    # Validate email.
    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email is required"
        )

    # Validate password.
    if len(password_data.new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="New password must be at least 6 characters"
        )

    # Find user.
    user = (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="No account found with this email"
        )

    # Google users don't have local passwords.
    if user.hashed_password is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "This account uses Google login. "
                "Please sign in with Google."
            )
        )

    # New password must be different.
    if verify_password(
        password_data.new_password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "New password must be different "
                "from the current password"
            )
        )

    user.hashed_password = hash_password(
        password_data.new_password
    )

    db.commit()
    db.refresh(user)

    return {
        "message": "Password reset successfully"
    }


# =========================================================
# NOTE ENDPOINTS
# =========================================================


# =========================================================
# CREATE NOTE
# =========================================================

@app.post(
    "/notes",
    response_model=schemas.NoteResponse
)
def create_note(
    note: schemas.NoteCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    new_note = models.Note(
        title=note.title,
        content=note.content,
        user_id=current_user.id
    )

    db.add(new_note)
    db.commit()
    db.refresh(new_note)

    return new_note


# =========================================================
# GET ALL NOTES
# =========================================================

@app.get(
    "/notes",
    response_model=list[schemas.NoteResponse]
)
def get_notes(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    notes = (
        db.query(models.Note)
        .filter(
            models.Note.user_id == current_user.id
        )
        .all()
    )

    return notes


# =========================================================
# GET SINGLE NOTE
# =========================================================

@app.get(
    "/notes/{note_id}",
    response_model=schemas.NoteResponse
)
def get_note(
    note_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    note = (
        db.query(models.Note)
        .filter(
            models.Note.id == note_id,
            models.Note.user_id == current_user.id
        )
        .first()
    )

    if not note:
        raise HTTPException(
            status_code=404,
            detail="Note not found"
        )

    return note


# =========================================================
# UPDATE NOTE
# =========================================================

@app.put(
    "/notes/{note_id}",
    response_model=schemas.NoteResponse
)
def update_note(
    note_id: int,
    note_data: schemas.NoteCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    note = (
        db.query(models.Note)
        .filter(
            models.Note.id == note_id,
            models.Note.user_id == current_user.id
        )
        .first()
    )

    if not note:
        raise HTTPException(
            status_code=404,
            detail="Note not found"
        )

    note.title = note_data.title
    note.content = note_data.content

    db.commit()
    db.refresh(note)

    return note


# =========================================================
# DELETE NOTE
# =========================================================

@app.delete("/notes/{note_id}")
def delete_note(
    note_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    note = (
        db.query(models.Note)
        .filter(
            models.Note.id == note_id,
            models.Note.user_id == current_user.id
        )
        .first()
    )

    if not note:
        raise HTTPException(
            status_code=404,
            detail="Note not found"
        )

    db.delete(note)
    db.commit()

    return {
        "message": "Note deleted successfully"
    }