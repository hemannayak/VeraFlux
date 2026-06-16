"""
Veraflux Configuration Settings
Production-ready configuration management using Pydantic settings

This module provides comprehensive configuration management for the Veraflux platform,
with environment variable loading, validation, and production safety features.
"""

import os
from typing import List, Optional, Union
from pydantic import BaseSettings, Field, validator


class DatabaseSettings(BaseSettings):
    """
    Database configuration settings
    
    Handles PostgreSQL database connection parameters and pool settings.
    All sensitive values should be provided via environment variables.
    """
    
    # PostgreSQL connection URL
    # Format: postgresql://user:password@host:port/database
    database_url: str = Field(
        default="postgresql://user:password@localhost:5432/veraflux",
        env="DATABASE_URL",
        description="PostgreSQL database connection URL"
    )
    
    # Connection pool settings for optimal performance
    db_pool_size: int = Field(
        default=10,
        env="DB_POOL_SIZE",
        description="Number of connections to maintain in pool"
    )
    db_max_overflow: int = Field(
        default=20,
        env="DB_MAX_OVERFLOW",
        description="Maximum additional connections beyond pool size"
    )
    db_pool_timeout: int = Field(
        default=30,
        env="DB_POOL_TIMEOUT",
        description="Timeout in seconds for getting connection from pool"
    )
    
    class Config:
        env_prefix = "DB_"


class CacheSettings(BaseSettings):
    """
    Cache configuration settings
    
    Handles Redis connection and caching parameters for performance optimization.
    Redis is used for session storage, API response caching, and real-time data.
    """
    
    # Redis connection settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL",
        description="Redis connection URL for caching and sessions"
    )
    redis_host: str = Field(
        default="localhost",
        env="REDIS_HOST",
        description="Redis server hostname"
    )
    redis_port: int = Field(
        default=6379,
        env="REDIS_PORT",
        description="Redis server port"
    )
    redis_db: int = Field(
        default=0,
        env="REDIS_DB",
        description="Redis database number"
    )
    redis_password: Optional[str] = Field(
        default=None,
        env="REDIS_PASSWORD",
        description="Redis authentication password (if required)"
    )
    
    # Cache configuration
    cache_ttl_seconds: int = Field(
        default=3600,
        env="CACHE_TTL_SECONDS",
        description="Default time-to-live for cached items in seconds"
    )
    cache_max_size: int = Field(
        default=1000,
        env="CACHE_MAX_SIZE",
        description="Maximum number of items to cache"
    )
    
    class Config:
        env_prefix = "REDIS_"


class VectorStoreSettings(BaseSettings):
    """
    Vector store configuration settings
    
    Handles vector database connection for semantic search and similarity matching.
    Supports multiple vector database backends (Pinecone, Weaviate, ChromaDB).
    """
    
    # Vector database connection
    vector_db_url: str = Field(
        default="http://localhost:8080",
        env="VECTOR_DB_URL",
        description="Vector database connection URL"
    )
    vector_db_api_key: Optional[str] = Field(
        default=None,
        env="VECTOR_DB_API_KEY",
        description="API key for vector database service"
    )
    vector_db_type: str = Field(
        default="chroma",
        env="VECTOR_DB_TYPE",
        description="Type of vector database (chroma, pinecone, weaviate)"
    )
    
    # Embedding model configuration
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        env="EMBEDDING_MODEL",
        description="HuggingFace model name for text embeddings"
    )
    embedding_dimension: int = Field(
        default=768,
        env="EMBEDDING_DIMENSION",
        description="Dimension of embedding vectors"
    )
    embedding_batch_size: int = Field(
        default=32,
        env="EMBEDDING_BATCH_SIZE",
        description="Batch size for embedding generation"
    )
    
    class Config:
        env_prefix = "VECTOR_"


class APISettings(BaseSettings):
    """
    API configuration settings
    
    Handles FastAPI server configuration, CORS, rate limiting, and API behavior.
    """
    
    # API metadata
    api_title: str = Field(
        default="Veraflux API",
        env="API_TITLE",
        description="Title of the API service"
    )
    api_version: str = Field(
        default="1.0.0",
        env="API_VERSION",
        description="Current API version"
    )
    api_description: str = Field(
        default="Real-time Disaster Intelligence Platform API",
        env="API_DESCRIPTION",
        description="Description of the API service"
    )
    
    # Server configuration
    host: str = Field(
        default="0.0.0.0",
        env="HOST",
        description="Host address to bind the server"
    )
    port: int = Field(
        default=8000,
        env="PORT",
        description="Port number for the API server"
    )
    debug: bool = Field(
        default=False,
        env="DEBUG",
        description="Enable debug mode (development only)"
    )
    
    # CORS configuration for cross-origin requests
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS",
        description="List of allowed origins for CORS"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        env="CORS_ALLOW_CREDENTIALS",
        description="Allow credentials in CORS requests"
    )
    
    # Rate limiting for API protection
    rate_limit_per_minute: int = Field(
        default=60,
        env="RATE_LIMIT_PER_MINUTE",
        description="Maximum requests per minute per client"
    )
    rate_limit_burst: int = Field(
        default=10,
        env="RATE_LIMIT_BURST",
        description="Maximum burst size for rate limiting"
    )
    
    class Config:
        env_prefix = "API_"


class IngestionSettings(BaseSettings):
    """
    Data ingestion configuration settings
    
    Handles configuration for external data sources including social media,
    news APIs, and sensor data collection.
    """
    
    # Twitter/X API configuration for real-time disaster monitoring
    twitter_api_key: Optional[str] = Field(
        default=None,
        env="TWITTER_API_KEY",
        description="Twitter API consumer key"
    )
    twitter_api_secret: Optional[str] = Field(
        default=None,
        env="TWITTER_API_SECRET",
        description="Twitter API consumer secret"
    )
    twitter_access_token: Optional[str] = Field(
        default=None,
        env="TWITTER_ACCESS_TOKEN",
        description="Twitter API access token"
    )
    twitter_access_token_secret: Optional[str] = Field(
        default=None,
        env="TWITTER_ACCESS_TOKEN_SECRET",
        description="Twitter API access token secret"
    )
    twitter_bearer_token: Optional[str] = Field(
        default=None,
        env="TWITTER_BEARER_TOKEN",
        description="Twitter API v2 bearer token"
    )
    
    # News API configuration for disaster news collection
    news_api_key: Optional[str] = Field(
        default=None,
        env="NEWS_API_KEY",
        description="News API key for disaster news collection"
    )
    news_sources: List[str] = Field(
        default=[],
        env="NEWS_SOURCES",
        description="List of news sources to monitor"
    )
    
    # Sensor data configuration
    sensor_api_endpoints: List[str] = Field(
        default=[],
        env="SENSOR_API_ENDPOINTS",
        description="List of sensor API endpoints for data collection"
    )
    sensor_api_key: Optional[str] = Field(
        default=None,
        env="SENSOR_API_KEY",
        description="API key for sensor data access"
    )
    
    # Ingestion performance settings
    ingestion_interval_seconds: int = Field(
        default=60,
        env="INGESTION_INTERVAL_SECONDS",
        description="Interval between data ingestion cycles"
    )
    max_events_per_batch: int = Field(
        default=100,
        env="MAX_EVENTS_PER_BATCH",
        description="Maximum events to process in a single batch"
    )
    ingestion_workers: int = Field(
        default=4,
        env="INGESTION_WORKERS",
        description="Number of worker processes for data ingestion"
    )
    
    class Config:
        env_prefix = "INGESTION_"


class ProcessingSettings(BaseSettings):
    """
    Data processing configuration settings
    
    Handles filtering, deduplication, and processing parameters for disaster data.
    """
    
    # Content filtering thresholds
    content_similarity_threshold: float = Field(
        default=0.8,
        env="CONTENT_SIMILARITY_THRESHOLD",
        description="Threshold for content similarity in deduplication (0.0-1.0)"
    )
    time_threshold_minutes: int = Field(
        default=30,
        env="TIME_THRESHOLD_MINUTES",
        description="Time window for duplicate detection in minutes"
    )
    location_threshold_km: float = Field(
        default=5.0,
        env="LOCATION_THRESHOLD_KM",
        description="Distance threshold for location-based deduplication in km"
    )
    
    # Processing performance settings
    deduplication_batch_size: int = Field(
        default=1000,
        env="DEDUPLICATION_BATCH_SIZE",
        description="Batch size for deduplication processing"
    )
    max_processing_workers: int = Field(
        default=4,
        env="MAX_PROCESSING_WORKERS",
        description="Maximum number of parallel processing workers"
    )
    processing_timeout_seconds: int = Field(
        default=300,
        env="PROCESSING_TIMEOUT_SECONDS",
        description="Timeout for processing operations"
    )
    
    # Quality thresholds
    min_content_length: int = Field(
        default=10,
        env="MIN_CONTENT_LENGTH",
        description="Minimum content length for valid events"
    )
    max_content_length: int = Field(
        default=10000,
        env="MAX_CONTENT_LENGTH",
        description="Maximum content length for events"
    )
    
    class Config:
        env_prefix = "PROCESSING_"


class VerificationSettings(BaseSettings):
    """
    Verification configuration settings
    
    Handles text and media verification parameters for disaster data authenticity.
    """
    
    # Text verification thresholds
    min_credibility_threshold: float = Field(
        default=0.5,
        env="MIN_CREDIBILITY_THRESHOLD",
        description="Minimum credibility score for verified events (0.0-1.0)"
    )
    source_reliability_weight: float = Field(
        default=0.4,
        env="SOURCE_RELIABILITY_WEIGHT",
        description="Weight for source reliability in verification (0.0-1.0)"
    )
    
    # Media verification settings
    max_file_size_mb: int = Field(
        default=50,
        env="MAX_FILE_SIZE_MB",
        description="Maximum file size for uploaded media in MB"
    )
    allowed_media_types: List[str] = Field(
        default=["image/jpeg", "image/png", "video/mp4", "image/webp"],
        env="ALLOWED_MEDIA_TYPES",
        description="List of allowed media MIME types"
    )
    
    # External verification services
    reverse_image_search_api_key: Optional[str] = Field(
        default=None,
        env="REVERSE_IMAGE_SEARCH_API_KEY",
        description="API key for reverse image search verification"
    )
    content_moderation_api_key: Optional[str] = Field(
        default=None,
        env="CONTENT_MODERATION_API_KEY",
        description="API key for content moderation service"
    )
    
    # Verification performance
    verification_timeout_seconds: int = Field(
        default=120,
        env="VERIFICATION_TIMEOUT_SECONDS",
        description="Timeout for verification operations"
    )
    max_verification_attempts: int = Field(
        default=3,
        env="MAX_VERIFICATION_ATTEMPTS",
        description="Maximum retry attempts for verification"
    )
    
    class Config:
        env_prefix = "VERIFICATION_"


class StorageSettings(BaseSettings):
    """
    Storage configuration settings
    
    Handles file storage configuration for media files and data persistence.
    """
    
    # Storage type and location
    storage_type: str = Field(
        default="local",
        env="STORAGE_TYPE",
        description="Storage backend type (local, s3, gcs, azure)"
    )
    storage_path: str = Field(
        default="./storage",
        env="STORAGE_PATH",
        description="Local storage path for files"
    )
    
    # AWS S3 configuration (if using S3)
    aws_access_key_id: Optional[str] = Field(
        default=None,
        env="AWS_ACCESS_KEY_ID",
        description="AWS access key ID for S3 storage"
    )
    aws_secret_access_key: Optional[str] = Field(
        default=None,
        env="AWS_SECRET_ACCESS_KEY",
        description="AWS secret access key for S3 storage"
    )
    aws_region: str = Field(
        default="us-west-2",
        env="AWS_REGION",
        description="AWS region for S3 storage"
    )
    s3_bucket_name: Optional[str] = Field(
        default=None,
        env="S3_BUCKET_NAME",
        description="S3 bucket name for file storage"
    )
    
    # Google Cloud Storage configuration (if using GCS)
    gcp_service_account_path: Optional[str] = Field(
        default=None,
        env="GCP_SERVICE_ACCOUNT_PATH",
        description="Path to GCP service account JSON file"
    )
    gcs_bucket_name: Optional[str] = Field(
        default=None,
        env="GCS_BUCKET_NAME",
        description="GCS bucket name for file storage"
    )
    
    # Storage performance settings
    storage_retention_days: int = Field(
        default=365,
        env="STORAGE_RETENTION_DAYS",
        description="Number of days to retain files in storage"
    )
    storage_cleanup_interval_hours: int = Field(
        default=24,
        env="STORAGE_CLEANUP_INTERVAL_HOURS",
        description="Interval for storage cleanup operations"
    )
    
    class Config:
        env_prefix = "STORAGE_"


class MonitoringSettings(BaseSettings):
    """
    Monitoring and logging configuration settings
    
    Handles application monitoring, logging, metrics, and alerting configuration.
    """
    
    # Logging configuration
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_file_path: Optional[str] = Field(
        default=None,
        env="LOG_FILE_PATH",
        description="Path to log file (if not specified, logs to console)"
    )
    log_format: str = Field(
        default="json",
        env="LOG_FORMAT",
        description="Log format (json, text)"
    )
    
    # Metrics and monitoring
    enable_metrics: bool = Field(
        default=True,
        env="ENABLE_METRICS",
        description="Enable Prometheus metrics collection"
    )
    metrics_port: int = Field(
        default=9090,
        env="METRICS_PORT",
        description="Port for metrics endpoint"
    )
    metrics_path: str = Field(
        default="/metrics",
        env="METRICS_PATH",
        description="Path for metrics endpoint"
    )
    
    # Health check configuration
    health_check_interval_seconds: int = Field(
        default=30,
        env="HEALTH_CHECK_INTERVAL_SECONDS",
        description="Interval for health check operations"
    )
    health_check_timeout_seconds: int = Field(
        default=10,
        env="HEALTH_CHECK_TIMEOUT_SECONDS",
        description="Timeout for health check operations"
    )
    
    # Alerting configuration
    alert_webhook_url: Optional[str] = Field(
        default=None,
        env="ALERT_WEBHOOK_URL",
        description="Webhook URL for alert notifications"
    )
    alert_email_smtp_host: Optional[str] = Field(
        default=None,
        env="ALERT_EMAIL_SMTP_HOST",
        description="SMTP host for email alerts"
    )
    alert_email_smtp_port: int = Field(
        default=587,
        env="ALERT_EMAIL_SMTP_PORT",
        description="SMTP port for email alerts"
    )
    alert_email_username: Optional[str] = Field(
        default=None,
        env="ALERT_EMAIL_USERNAME",
        description="SMTP username for email alerts"
    )
    alert_email_password: Optional[str] = Field(
        default=None,
        env="ALERT_EMAIL_PASSWORD",
        description="SMTP password for email alerts"
    )
    
    class Config:
        env_prefix = "MONITORING_"


class SecuritySettings(BaseSettings):
    """
    Security configuration settings
    
    Handles authentication, authorization, and security parameters.
    """
    
    # JWT configuration
    secret_key: str = Field(
        default="your-secret-key-change-this-in-production",
        env="SECRET_KEY",
        description="Secret key for JWT token signing"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        env="JWT_ALGORITHM",
        description="Algorithm for JWT token signing"
    )
    jwt_expiration_hours: int = Field(
        default=24,
        env="JWT_EXPIRATION_HOURS",
        description="JWT token expiration time in hours"
    )
    jwt_refresh_expiration_days: int = Field(
        default=7,
        env="JWT_REFRESH_EXPIRATION_DAYS",
        description="JWT refresh token expiration time in days"
    )
    
    # API security
    api_key_header: str = Field(
        default="X-API-Key",
        env="API_KEY_HEADER",
        description="Header name for API key authentication"
    )
    require_https: bool = Field(
        default=True,
        env="REQUIRE_HTTPS",
        description="Require HTTPS for API requests"
    )
    
    # Rate limiting security
    enable_rate_limiting: bool = Field(
        default=True,
        env="ENABLE_RATE_LIMITING",
        description="Enable API rate limiting"
    )
    
    class Config:
        env_prefix = "SECURITY_"


class Settings(BaseSettings):
    """
    Main application settings
    
    Central configuration class that aggregates all settings modules
    and provides environment-based configuration management.
    """
    
    # Environment configuration
    environment: str = Field(
        default="development",
        env="ENVIRONMENT",
        description="Application environment (development, staging, production)"
    )
    
    # Application metadata
    app_name: str = Field(
        default="Veraflux",
        env="APP_NAME",
        description="Application name"
    )
    app_version: str = Field(
        default="1.0.0",
        env="APP_VERSION",
        description="Application version"
    )
    
    # Sub-settings modules
    database: DatabaseSettings = DatabaseSettings()
    cache: CacheSettings = CacheSettings()
    vector_store: VectorStoreSettings = VectorStoreSettings()
    api: APISettings = APISettings()
    ingestion: IngestionSettings = IngestionSettings()
    processing: ProcessingSettings = ProcessingSettings()
    verification: VerificationSettings = VerificationSettings()
    storage: StorageSettings = StorageSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    security: SecuritySettings = SecuritySettings()
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value"""
        valid_environments = ["development", "staging", "production", "testing"]
        if v.lower() not in valid_environments:
            raise ValueError(f"Environment must be one of: {valid_environments}")
        return v.lower()
    
    @validator("secret_key")
    def validate_secret_key(cls, v, values):
        """Validate secret key for production"""
        if values.get("environment") == "production" and v == "your-secret-key-change-this-in-production":
            raise ValueError("Secret key must be changed in production")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance - singleton pattern
settings = Settings()


def get_settings() -> Settings:
    """
    Get the global settings instance
    
    Returns:
        Settings: The application settings instance
    """
    return settings


def is_development() -> bool:
    """
    Check if running in development mode
    
    Returns:
        bool: True if in development environment
    """
    return settings.environment == "development"


def is_production() -> bool:
    """
    Check if running in production mode
    
    Returns:
        bool: True if in production environment
    """
    return settings.environment == "production"


def is_staging() -> bool:
    """
    Check if running in staging mode
    
    Returns:
        bool: True if in staging environment
    """
    return settings.environment == "staging"


def is_testing() -> bool:
    """
    Check if running in testing mode
    
    Returns:
        bool: True if in testing environment
    """
    return settings.environment == "testing"
