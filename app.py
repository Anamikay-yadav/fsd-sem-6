import os
import uuid
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename

from config import Config
from aws_services import upload_to_s3, generate_summary, generate_quiz
from pdf_processor import extract_text_from_pdf
from database import init_db, save_document, get_all_documents, get_document, save_quiz_questions, get_quiz_questions, save_attempt, get_stats

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

with app.app_context():
    init_db()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


@app.route("/")
def index():
    documents = get_all_documents()
    stats = get_stats()
    return render_template("index.html", documents=documents, stats=stats)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file selected", "error")
            return redirect(request.url)

        file = request.files["file"]

        if file.filename == "":
            flash("No file selected", "error")
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash("Only PDF files are allowed", "error")
            return redirect(request.url)

        original_name = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_name}"
        local_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
        file.save(local_path)

        try:
            s3_key = f"uploads/{unique_filename}"
            s3_url = upload_to_s3(local_path, s3_key)
            extracted_text = extract_text_from_pdf(local_path)

            if not extracted_text or len(extracted_text.strip()) < 50:
                flash("Could not extract text. Make sure PDF is not scanned/image-only.", "error")
                return redirect(request.url)

            summary = generate_summary(extracted_text)
            quiz_questions = generate_quiz(extracted_text)

            doc_id = save_document(
                filename=unique_filename,
                original_name=original_name,
                s3_url=s3_url,
                page_count=None,
                summary=summary,
                extracted_text=extracted_text,
            )

            save_quiz_questions(doc_id, quiz_questions)
            flash("Document processed successfully!", "success")
            return redirect(url_for("document_detail", doc_id=doc_id))

        except Exception as e:
            flash(f"Processing failed: {str(e)}", "error")
            return redirect(request.url)
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    return render_template("upload.html")


@app.route("/document/<int:doc_id>")
def document_detail(doc_id):
    doc = get_document(doc_id)
    if not doc:
        flash("Document not found", "error")
        return redirect(url_for("index"))
    questions = get_quiz_questions(doc_id)
    return render_template("document.html", document=doc, questions=questions)


@app.route("/api/answer", methods=["POST"])
def submit_answer():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    question_id = data.get("question_id")
    selected_index = data.get("selected_index")
    doc_id = data.get("doc_id")

    if question_id is None or selected_index is None:
        return jsonify({"error": "Missing question_id or selected_index"}), 400

    from database import get_question_by_id
    question = get_question_by_id(question_id)

    if not question:
        return jsonify({"error": "Question not found"}), 404

    is_correct = selected_index == question["correct_index"]
    save_attempt(doc_id=doc_id, question_id=question_id,
                 selected_index=selected_index, is_correct=is_correct)

    return jsonify({
        "correct": is_correct,
        "correct_index": question["correct_index"],
        "explanation": question.get("explanation", ""),
    })


@app.route("/document/<int:doc_id>/delete", methods=["POST"])
def delete_document(doc_id):
    from database import delete_document_db
    delete_document_db(doc_id)
    flash("Document deleted", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
