from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
import io
from typing import Optional, List
from typing import Dict, Any
from pydantic import BaseModel

from app.api.routers.auth import get_current_user
from app.models.user import User
from app.services.file_storage import file_storage

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload", response_model=Dict[str, Any])
async def upload_file(
    file: UploadFile = File(...),
    folder: str = "screenshots",
):
    """Upload a file to MinIO storage."""
    file_data = await file.read()
    if not file_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    result = await file_storage.upload_file(
        file_data=file_data,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        folder=folder,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "File upload failed."),
        )

    return result



@router.get("/stream")
async def stream_file(
    file_url: str,
    current_user: User = Depends(get_current_user),
):
    """Stream a file from MinIO so it can be displayed via an <img> tag.

    The `file_url` may be either the full URL produced by uploads or the
    object name inside the bucket.
    """
    result = file_storage.get_object_bytes(file_url)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "File not found."),
        )

    data = result.get("data")
    content_type = result.get("content_type") or "application/octet-stream"

    return StreamingResponse(io.BytesIO(data), media_type=content_type)



@router.get("/presigned")
async def presigned_url(
    file_url: str,
    expires: int = 3600,
    current_user: User = Depends(get_current_user),
):
    """Return a presigned GET URL for a stored object.

    Accepts either the full file URL produced by uploads or the object name.
    """
    # Convert full URL to object name if necessary
    object_name: Optional[str] = None
    try:
        object_name = file_storage._object_name_from_url(file_url)
    except Exception:
        object_name = None

    if not object_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file_url",
        )

    presigned = file_storage.get_presigned_url(object_name, expires=expires)
    if not presigned:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate presigned URL",
        )

    return {"presigned_url": presigned}


class PresignedBatchRequest(BaseModel):
    file_urls: List[str]
    expires: Optional[int] = 3600


class PresignedBatchResponse(BaseModel):
    presigned_urls: List[str]


@router.post("/presigned/batch", response_model=PresignedBatchResponse)
async def presigned_urls_batch(
    request: PresignedBatchRequest,
    current_user: User = Depends(get_current_user),
):
    if not request.file_urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file_urls must be a non-empty list",
        )

    presigned_urls: List[str] = []
    for file_url in request.file_urls:
        try:
            object_name = file_storage._object_name_from_url(file_url)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file_url: {file_url}",
            )

        if not object_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file_url: {file_url}",
            )

        presigned = file_storage.get_presigned_url(object_name, expires=request.expires)
        if not presigned:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not generate presigned URL for {file_url}",
            )

        presigned_urls.append(presigned)

    return {"presigned_urls": presigned_urls}
