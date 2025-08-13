from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..services.auth_service import AuthService, create_access_token
from ..db import models
from jose import JWTError, jwt
from ..services.auth_service import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    auth = AuthService(db)
    # Auto-register convenience for dev if user absent
    auth.register_if_absent(form_data.username, form_data.password)
    user = auth.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> models.User:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == sub).first()
    if not user:
        raise credentials_exception
    return user


def get_current_user_optional(db: Session = Depends(get_db), authorization: str | None = Header(None)) -> models.User | None:
    """Best-effort user retrieval; returns None if no valid bearer token.
    Used during transitional period while legacy demo-user fallback exists."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(None, 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if not sub:
            return None
        user = db.query(models.User).filter(models.User.id == sub).first()
        return user
    except JWTError:
        return None
