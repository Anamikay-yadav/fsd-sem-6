# Smart Study Assistant — Python/Flask + AWS

Upload PDF notes → AI generates a summary + 10 quiz questions.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
python app.py
```

Visit: http://localhost:5000

## Stack

- Flask (web framework)
- pdfplumber (PDF text extraction)
- OpenAI GPT-4o-mini or Amazon Bedrock Claude (AI)
- Amazon S3 (PDF storage)
- SQLite (database, swap for Amazon RDS in production)

## Project Structure

```
smart_study_assistant/
├── app.py              — Flask routes
├── config.py           — Configuration
├── aws_services.py     — S3 + Bedrock + Lambda helpers
├── pdf_processor.py    — PDF text extraction
├── database.py         — SQLite CRUD
├── templates/          — Jinja2 HTML templates
└── static/             — CSS + JS
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Flask session secret |
| `AI_PROVIDER` | `openai` or `bedrock` |
| `OPENAI_API_KEY` | OpenAI API key |
| `AWS_REGION` | AWS region (e.g. us-east-1) |
| `S3_BUCKET_NAME` | S3 bucket for PDF storage |
| `BEDROCK_MODEL_ID` | Bedrock model ID |

## Production Deployment

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```
