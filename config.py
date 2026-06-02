import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/tmp/smart_study_uploads")
    ALLOWED_EXTENSIONS = {"pdf"}
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024

    DATABASE_FILE = "smart_study.db"

    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "")
    BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
    LAMBDA_FUNCTION_NAME = os.environ.get("LAMBDA_FUNCTION_NAME", "smart-study-processor")

    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "openai")
