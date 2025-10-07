"""
Centralized configuration management using Pydantic.

This module defines the Settings class which loads and validates application
configuration from environment variables or .env file.

Module Input:
    - Environment variables from OS
    - .env file in project root (optional)
    - Default values defined in class

Module Output:
    - Validated configuration object (singleton)
    - Helper methods for bucket/prefix resolution
    - Database connection strings
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    
    Uses Pydantic's BaseSettings to provide validated configuration with
    automatic type conversion and environment variable loading. Supports
    both development (.env file) and production (environment variables)
    configuration methods.
    
    Attributes:
        AWS Configuration:
            aws_access_key_id (Optional[str]): AWS access key for API calls
            aws_secret_access_key (Optional[str]): AWS secret key
            aws_default_region (str): Default AWS region (default: "us-east-1")
            aws_profile (Optional[str]): Named AWS profile to use
            
        S3 Configuration:
            s3_bucket_mba (str): S3 bucket for MBA data files
            s3_bucket_policy (str): S3 bucket for policy documents
            s3_prefix_mba (str): Key prefix for MBA files (must end with /)
            s3_prefix_policy (str): Key prefix for policy files (must end with /)
            s3_sse (str): Server-side encryption type (default: "AES256")
            
        Database Configuration:
            RDS_HOST (str): MySQL RDS endpoint hostname
            RDS_PORT (int): MySQL port (default: 3306)
            RDS_DATABASE (str): Database name
            RDS_USERNAME (str): Database user
            RDS_PASSWORD (str): Database password
            RDS_params (str): Additional connection parameters
            
        Logging Configuration:
            log_level (str): Minimum log level (default: "INFO")
            log_dir (Path): Directory for log files (default: "logs")
            log_file (str): Log file name (default: "app.log")
    """

    # ---------------- AWS Configuration ----------------
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_default_region: str = "us-east-1"
    aws_profile: Optional[str] = None  # Profile overrides env/role

    # ---------------- S3 Buckets ----------------
    s3_bucket_mba: str = "memberbenefitassistant-bucket"
    s3_bucket_policy: str = "policy-bucket"

    # ---------------- S3 Prefixes ----------------
    s3_prefix_mba: str = "mba/"      # Trailing slash required
    s3_prefix_policy: str = "policy/"

    # Optional: server-side encryption for uploads (AES256 or aws:kms)
    s3_sse: str = "AES256"

    # ---------------- Database (MySQL/RDS) ----------------
    RDS_HOST: str = "mysql-hma.cobyueoimrmh.us-east-1.rds.amazonaws.com"
    RDS_PORT: int = 3306
    RDS_DATABASE: str = "mba_mysql"
    RDS_USERNAME: str = "admin"
    RDS_PASSWORD: str = "Admin12345"
    RDS_params: str = "charset=utf8mb4"  # Extra params for SQLAlchemy URL

    # ---------------- Logging ----------------
    log_level: str = "INFO"
    log_dir: Path = Path("logs")
    log_file: str = "app.log"

    # ---------------- Model Configuration ----------------
    model_provider: str = "bedrock"
    model_name: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    model_region: str = "us-east-1"

    # ---------------- Pydantic Settings ----------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------------- Helper Methods ----------------
    def get_bucket(self, scope: str) -> str:
        """
        Get bucket name for given scope.
        
        Maps scope identifier to corresponding S3 bucket name.
        
        Args:
            scope (str): Scope identifier ("mba" or "policy")
            
        Returns:
            str: S3 bucket name for the scope
            
        Raises:
            ValueError: If scope is not "mba" or "policy"
        """
        s = scope.strip().lower()
        if s == "mba":
            return self.s3_bucket_mba
        if s == "policy":
            return self.s3_bucket_policy
        raise ValueError(f"Invalid scope: {scope}")

    def get_prefix(self, scope: str) -> str:
        """
        Get S3 prefix for given scope.
        
        Maps scope identifier to corresponding S3 key prefix.
        
        Args:
            scope (str): Scope identifier ("mba" or "policy")
            
        Returns:
            str: S3 prefix ending with '/'
            
        Raises:
            ValueError: If scope is not "mba" or "policy"
        """
        s = scope.strip().lower()
        if s == "mba":
            return self.s3_prefix_mba
        if s == "policy":
            return self.s3_prefix_policy
        raise ValueError(f"Invalid scope: {scope}")
    
    def db_url(self) -> str:
        """
        Generate MySQL connection URL from RDS settings.
        
        Constructs a SQLAlchemy-compatible database URL with proper
        encoding of special characters in passwords.
        
        Input:
            None (uses instance attributes)
            
        Returns:
            str: Complete MySQL connection URL
            
        Raises:
            ValueError: If required database settings are missing
            
        Example Output:
            "mysql+pymysql://user:pass%40word@host:3306/database?charset=utf8mb4"
        """
        host = self.RDS_HOST
        port = self.RDS_PORT
        name = self.RDS_DATABASE
        user = self.RDS_USERNAME
        pwd = self.RDS_PASSWORD
        params = self.RDS_params
        
        if not all([host, name, user, pwd]):
            missing = [k for k, v in {
                "RDS_HOST": host, 
                "RDS_DATABASE": name, 
                "RDS_USERNAME": user, 
                "RDS_PASSWORD": pwd
            }.items() if not v]
            raise ValueError(f"Missing required DB settings: {', '.join(missing)}")
        
        # URL-encode password to handle special characters
        encoded_pwd = quote_plus(pwd)
        
        # Build URL with parameters
        base_url = f"mysql+pymysql://{user}:{encoded_pwd}@{host}:{port}/{name}"
        if params:
            base_url += f"?{params}"
        
        return base_url

    def validate_db_connection_string(self) -> bool:
        """Validate that the database connection string can be generated."""
        try:
            self.db_url()
            return True
        except Exception:
            return False


# Singleton instance shared across the app
settings = Settings()