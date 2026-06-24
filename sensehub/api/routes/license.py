from fastapi import APIRouter, Depends

from sensehub.api.deps import get_current_user
from sensehub.licensing.tier import get_license_info

router = APIRouter(tags=["license"])


@router.get("/license")
async def license_info(username: str = Depends(get_current_user)):
    return get_license_info(username)
