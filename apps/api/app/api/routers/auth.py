from fastapi import APIRouter

from app.api.deps import AuthServiceDep, CurrentUserDep
from app.api.schemas.auth import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, auth: AuthServiceDep) -> LoginResponse:
    result = auth.login(body.email, body.password)
    return LoginResponse(token=result.token, user=UserOut(**result.user.__dict__))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUserDep) -> UserOut:
    return UserOut(**user.__dict__)
