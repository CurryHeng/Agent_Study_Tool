"""AI 供应商设置路由。"""
from fastapi import APIRouter, Depends

from api.deps import get_current_user
from models import User
from schemas.settings import AiSettingsIn, AiSettingsOut
from services import ai_settings
from services.access import AccessError

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/ai", response_model=AiSettingsOut)
def get_ai_settings(_user: User = Depends(get_current_user)):
    return ai_settings.get_ai_settings()


@router.put("/ai", response_model=AiSettingsOut)
def update_ai_settings(
    payload: AiSettingsIn,
    _user: User = Depends(get_current_user),
):
    try:
        return ai_settings.save_ai_settings(payload.model_dump())
    except ValueError as exc:
        raise AccessError(400, str(exc)) from exc
