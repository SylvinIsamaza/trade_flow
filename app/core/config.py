from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration settings."""
    
    # Application
    app_name: str = "TradeZella Clone API"
    debug: bool = True
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tradezella"
    
    # JWT Authentication
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Redis (optional - for caching)
    redis_url: Optional[str] = None
    
    # CORS
    cors_origins: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Email / SMTP
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: str = "noreply@tradezella.com"
    smtp_from_name: str = "TradeZella"
    smtp_use_tls: bool = True
    
    # Aliases for email config
    @property
    def SMTP_HOST(self) -> Optional[str]:
        return self.smtp_host
    
    @property
    def SMTP_PORT(self) -> int:
        return self.smtp_port
    
    @property
    def SMTP_USER(self) -> Optional[str]:
        return self.smtp_user
    
    @property
    def SMTP_PASSWORD(self) -> Optional[str]:
        return self.smtp_password
    
    @property
    def SMTP_FROM_EMAIL(self) -> str:
        return self.smtp_from_email
    
    @property
    def SMTP_FROM_NAME(self) -> str:
        return self.smtp_from_name
    
    @property
    def SMTP_USE_TLS(self) -> bool:
        return self.smtp_use_tls
    
    # MinIO / S3 Settings
    minio_endpoint: Optional[str] = None
    minio_access_key: Optional[str] = None
    minio_secret_key: Optional[str] = None
    minio_secure: bool = True
    minio_bucket: str = "tradezella"
    
    @property
    def MINIO_ENDPOINT(self) -> Optional[str]:
        return self.minio_endpoint
    
    @property
    def MINIO_ACCESS_KEY(self) -> Optional[str]:
        return self.minio_access_key
    
    @property
    def MINIO_SECRET_KEY(self) -> Optional[str]:
        return self.minio_secret_key
    
    @property
    def MINIO_SECURE(self) -> bool:
        return self.minio_secure
    
    @property
    def MINIO_BUCKET(self) -> str:
        return self.minio_bucket
    
    # App URL for generating links
    app_url: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create settings instance
settings = Settings()