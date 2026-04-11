from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.database import get_database
from app.services.github_kanban_sync import handle_github_webhook

router = APIRouter()


@router.post("/github")
async def github_webhook(request: Request):
    """GitHub App / webhook: secured with X-Hub-Signature-256 only (no JWT)."""
    body = await request.body()
    hdrs = {k.lower(): v for k, v in request.headers.items()}
    db = await get_database()
    result, err = await handle_github_webhook(db, body, hdrs)
    if err:
        return JSONResponse(content=result, status_code=err)
    return result
