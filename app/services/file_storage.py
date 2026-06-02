"""
File Storage Service
MinIO/S3-compatible storage for file uploads
"""
import io
import uuid
from typing import Optional, Dict, Any
from datetime import timedelta
from pathlib import Path

try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False

from app.core.config import settings


class FileStorageService:
    """MinIO/S3 file storage service."""
    
    # Public MinIO credentials (demo purposes)
    PUBLIC_ENDPOINT = "localhost:9000"
    PUBLIC_ACCESS_KEY = "admin"
    PUBLIC_SECRET_KEY = "password"
    
    def __init__(self):
        """Initialize MinIO client."""
        self.client = None
        self.bucket_name = settings.MINIO_BUCKET or "tradezella"
        self.endpoint_url = None
        
        # Use public credentials if no custom config
        if MINIO_AVAILABLE:
            if settings.MINIO_ENDPOINT and settings.MINIO_ACCESS_KEY:
                self.endpoint_url = f"{'https' if settings.MINIO_SECURE else 'http'}://{settings.MINIO_ENDPOINT}"
                self.client = Minio(
                    settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=settings.MINIO_SECURE,
                )
            else:
                self.endpoint_url = f"https://{self.PUBLIC_ENDPOINT}"
                self.client = Minio(
                    self.PUBLIC_ENDPOINT,
                    access_key=self.PUBLIC_ACCESS_KEY,
                    secret_key=self.PUBLIC_SECRET_KEY,
                    secure=True,
                )
    
    def _generate_filename(self, original_filename: str) -> str:
        """Generate unique filename."""
        ext = Path(original_filename).suffix
        return f"{uuid.uuid4()}{ext}"

    def _object_name_from_url(self, file_url: str) -> Optional[str]:
        """Extract object name (path inside bucket) from a full file URL.

        If a plain object name is provided, return it unchanged.
        """
        if not file_url:
            return None

        # If the URL contains the bucket name, strip the prefix
        marker = f"/{self.bucket_name}/"
        try:
            if marker in file_url:
                return file_url.split(marker, 1)[1]
        except Exception:
            pass

        # Fallback: assume the caller passed the object name already
        return file_url
    
    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        folder: str = "uploads"
    ) -> Dict[str, Any]:
        """
        Upload a file to MinIO storage.
        
        Args:
            file_data: File content as bytes
            filename: Original filename
            content_type: MIME type
            folder: Folder/bucket prefix
            
        Returns:
            Dict with file URL and details
        """
        if not self.client:
            # Return mock data if MinIO not available
            return {
                "success": False,
                "error": "MinIO not available"
            }
        
        try:
            # Generate unique filename
            unique_filename = self._generate_filename(filename)
            object_name = f"{folder}/{unique_filename}"
            
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)

            # Upload file: MinIO expects a file-like object, so wrap raw bytes.
            upload_data = (
                io.BytesIO(file_data)
                if isinstance(file_data, (bytes, bytearray))
                else file_data
            )

            self.client.put_object(
                self.bucket_name,
                object_name,
                upload_data,
                length=len(file_data),
                content_type=content_type,
            )
            
            # Generate public URL
            endpoint_url = self.endpoint_url or f"https://{self.PUBLIC_ENDPOINT}"
            file_url = f"{endpoint_url}/{self.bucket_name}/{object_name}"
            
            return {
                "success": True,
                "filename": unique_filename,
                "original_filename": filename,
                "file_url": file_url,
                "content_type": content_type,
                "size": len(file_data)
            }
            
        except S3Error as e:
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def upload_from_base64(
        self,
        base64_data: str,
        filename: str,
        content_type: str = "image/png",
        folder: str = "uploads"
    ) -> Dict[str, Any]:
        """Upload file from base64 encoded data."""
        import base64
        
        try:
            # Remove data URL prefix if present
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]
            
            file_data = base64.b64decode(base64_data)
            return await self.upload_file(file_data, filename, content_type, folder)
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid base64 data: {str(e)}"
            }
    
    def get_presigned_url(self, filename: str, expires: int = 3600) -> str:
        """
        Get a presigned URL for a file.
        
        Args:
            filename: Full object name
            expires: URL expiration in seconds
            
        Returns:
            Presigned URL
        """
        if not self.client:
            return ""
        
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                filename,
                expires=timedelta(seconds=expires)
            )
            return url
        except:
            return ""
    
    async def delete_file(self, filename: str) -> Dict[str, Any]:
        """Delete a file from storage."""
        if not self.client:
            return {"success": False, "error": "MinIO not available"}
        
        try:
            self.client.remove_object(self.bucket_name, filename)
            return {"success": True}
        except S3Error as e:
            return {"success": False, "error": str(e)}

    def get_object_bytes(self, file_url: str) -> Dict[str, Any]:
        """Retrieve an object from MinIO and return its bytes and content type.

        Args:
            file_url: Full URL returned by upload_file (or object name).

        Returns:
            Dict with keys: success, data (bytes), content_type or error
        """
        if not self.client:
            return {"success": False, "error": "MinIO not available"}

        try:
            object_name = self._object_name_from_url(file_url)
            obj = self.client.get_object(self.bucket_name, object_name)
            try:
                data = obj.read()
            finally:
                try:
                    obj.close()
                    obj.release_conn()
                except Exception:
                    pass

            # Try to infer content-type from headers if available
            content_type = None
            try:
                headers = getattr(obj, 'headers', None) or {}
                content_type = headers.get('Content-Type') or headers.get('content-type')
            except Exception:
                content_type = None

            return {"success": True, "data": data, "content_type": content_type}
        except S3Error as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Create singleton instance
file_storage = FileStorageService()