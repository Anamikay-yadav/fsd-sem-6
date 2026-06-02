import json
import boto3
from botocore.exceptions import ClientError, BotoCoreError

from config import Config


def upload_to_s3(local_file_path: str, s3_key: str) -> str:
    if not Config.S3_BUCKET_NAME:
        return f"local://{local_file_path}"

    try:
        s3_client = boto3.client("s3", region_name=Config.AWS_REGION)
        s3_client.upload_file(
            local_file_path,
            Config.S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={"ContentType": "application/pdf"}
        )
        return f"https://{Config.S3_BUCKET_NAME}.s3.{Config.AWS_REGION}.amazonaws.com/{s3_key}"
    except ClientError as e:
        raise RuntimeError(f"S3 upload failed: {e.response['Error']['Code']}") from e
    except BotoCoreError as e:
        raise RuntimeError(f"S3 connection failed: {e}") from e


def get_s3_presigned_url(s3_key: str, expiry_seconds: int = 3600) -> str:
    s3_client = boto3.client("s3", region_name=Config.AWS_REGION)
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": Config.S3_BUCKET_NAME, "Key": s3_key},
        ExpiresIn=expiry_seconds,
    )


def _call_bedrock(prompt: str, max_tokens: int = 1000) -> str:
    client = boto3.client("bedrock-runtime", region_name=Config.AWS_REGION)
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }
    response = client.invoke_model(
        modelId=Config.BEDROCK_MODEL_ID,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    return json.loads(response["body"].read())["content"][0]["text"]


def _call_openai(prompt: str, max_tokens: int = 1000, json_mode: bool = False) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=Config.OPENAI_API_KEY)
    kwargs = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.4,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    return client.chat.completions.create(**kwargs).choices[0].message.content.strip()


def _ai(prompt: str, max_tokens: int = 1000, json_mode: bool = False) -> str:
    if Config.AI_PROVIDER == "bedrock":
        return _call_bedrock(prompt, max_tokens)
    return _call_openai(prompt, max_tokens, json_mode)


def generate_summary(text: str) -> str:
    truncated = " ".join(text.split()[:4000])
    prompt = f"""You are a study assistant. Summarize the following academic notes in 3-5 clear paragraphs for a student.

Notes:
{truncated}

Summary:"""
    try:
        return _ai(prompt, max_tokens=800)
    except Exception as e:
        raise RuntimeError(f"Summary generation failed: {e}") from e


def generate_quiz(text: str) -> list:
    truncated = " ".join(text.split()[:4000])
    prompt = f"""Generate exactly 10 multiple-choice questions based on the study notes below.
Return ONLY valid JSON, no other text:
{{
  "questions": [
    {{
      "question": "...",
      "options": ["A text", "B text", "C text", "D text"],
      "correct_index": 0,
      "explanation": "..."
    }}
  ]
}}
correct_index is 0-based (0=A, 1=B, 2=C, 3=D).

Notes:
{truncated}"""
    try:
        raw = _ai(prompt, max_tokens=2500, json_mode=True)
        return json.loads(raw).get("questions", [])[:10]
    except json.JSONDecodeError as e:
        raise RuntimeError("AI returned invalid quiz format") from e
    except Exception as e:
        raise RuntimeError(f"Quiz generation failed: {e}") from e


def invoke_lambda_processor(doc_id: int, s3_key: str) -> dict:
    client = boto3.client("lambda", region_name=Config.AWS_REGION)
    response = client.invoke(
        FunctionName=Config.LAMBDA_FUNCTION_NAME,
        InvocationType="Event",
        Payload=json.dumps({"doc_id": doc_id, "s3_key": s3_key, "bucket": Config.S3_BUCKET_NAME}),
    )
    return {"status_code": response["StatusCode"]}
