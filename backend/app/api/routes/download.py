from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from datetime import datetime
from typing import Optional

from app.models.request_models import DownloadRequest
from app.services.excel_service import excel_service
from app.api.routes.auth import get_current_user, require_premium, TokenData

router = APIRouter()


@router.post("/excel")
async def download_excel(
    request: DownloadRequest,
    # Uncomment the line below to require premium subscription:
    # current_user: TokenData = Depends(require_premium)
    current_user: Optional[TokenData] = Depends(get_current_user)
):
    """
    Generate and download test cases as Excel file.

    This is a premium feature. When authentication is enforced,
    only premium users can download Excel files.
    """

    excel_file = excel_service.generate_excel(
        content=request.content,
        query=request.query
    )

    filename = f"airbot_test_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
