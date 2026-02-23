"""
File Storage Service
MinIO/S3-compatible storage for file uploads
"""
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
    PUBLIC_ENDPOINT = "play.min.io"
    PUBLIC_ACCESS_KEY = "Q3AM3UQ867SPQQA43P2F"
    PUBLIC_SECRET_KEY = "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYYBdTG"
    
    def __init__(self):
        """Initialize MinIO client."""
        self.client = None
        self.bucket_name = "tradezella"
        
        # Use public credentials if no custom config
        if MINIO_AVAILABLE:
            if settings.MINIO_ENDPOINT and settings.MINIO_ACCESS_KEY:
                # Custom MinIO/S3 config
                self.client = Minio(
                    settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=settings.MINIO_SECURE
                )
            else:
                # Use public MinIO playground
                self.client = Minio(
                    self.PUBLIC_ENDPOINT,
                    access_key=self.PUBLIC_ACCESS_KEY,
                    secret_key=self.PUBLIC_SECRET_KEY,
                    secure=True
                )
    
    def _generate_filename(self, original_filename: str) -> str:
        """Generate unique filename."""
        ext = Path(original_filename).suffix
        return f"{uuid.uuid4()}{ext}"
    
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
            
            # Upload file
            self.client.put_object(
                self.bucket_name,
                object_name,
                file_data,
                length=len(file_data),
                content_type=content_type
            )
            
            # Generate public URL
            file_url = f"https://{self.PUBLIC_ENDPOINT}/{self.bucket_name}/{object_name}"
            
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


# Create singleton instance
file_storage = FileStorageService()