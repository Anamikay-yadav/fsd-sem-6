import sqlite3
from datetime import datetime
from config import Config


def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            filename      TEXT    NOT NULL,
            original_name TEXT    NOT NULL,
            s3_url        TEXT    DEFAULT '',
            status        TEXT    NOT NULL DEFAULT 'done',
            page_count    INTEGER,
            summary       TEXT,
            extracted_text TEXT,
            error_message TEXT,
            created_at    TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS quiz_questions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id   INTEGER NOT NULL,
            question      TEXT    NOT NULL,
            option_a      TEXT    NOT NULL,
            option_b      TEXT    NOT NULL,
            option_c      TEXT    NOT NULL,
            option_d      TEXT    NOT NULL,
            correct_index INTEGER NOT NULL,
            explanation   TEXT,
            order_index   INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id    INTEGER NOT NULL,
            question_id    INTEGER NOT NULL,
            selected_index INTEGER NOT NULL,
            is_correct     INTEGER NOT NULL,
            answered_at    TEXT    NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES quiz_questions(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


def save_document(filename, original_name, s3_url, page_count, summary, extracted_text) -> int:
    conn = get_db_connection()
    cursor = conn.execute(
        """INSERT INTO documents
           (filename, original_name, s3_url, page_count, summary, extracted_text, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'done', ?)""",
        (filename, original_name, s3_url, page_count, summary, extracted_text, datetime.now().isoformat()),
    )
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return doc_id


def save_quiz_questions(document_id: int, questions: list) -> None:
    if not questions:
        return
    conn = get_db_connection()
    rows = []
    for idx, q in enumerate(questions):
        options = q.get("options", ["", "", "", ""])
        while len(options) < 4:
            options.append("")
        rows.append((
            document_id, q.get("question", ""),
            options[0], options[1], options[2], options[3],
            q.get("correct_index", 0), q.get("explanation", ""), idx,
        ))
    conn.executemany(
        """INSERT INTO quiz_questions
           (document_id, question, option_a, option_b, option_c, option_d, correct_index, explanation, order_index)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()
    conn.close()


def get_all_documents() -> list:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_document(doc_id: int) -> dict | None:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_quiz_questions(document_id: int) -> list:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM quiz_questions WHERE document_id = ? ORDER BY order_index",
        (document_id,),
    ).fetchall()
    conn.close()
    questions = []
    for row in rows:
        q = dict(row)
        q["options"] = [q["option_a"], q["option_b"], q["option_c"], q["option_d"]]
        questions.append(q)
    return questions


def get_question_by_id(question_id: int) -> dict | None:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM quiz_questions WHERE id = ?", (question_id,)).fetchone()
    conn.close()
    if not row:
        return None
    q = dict(row)
    q["options"] = [q["option_a"], q["option_b"], q["option_c"], q["option_d"]]
    return q


def save_attempt(doc_id: int, question_id: int, selected_index: int, is_correct: bool) -> None:
    conn = get_db_connection()
    conn.execute(
        """INSERT INTO quiz_attempts
           (document_id, question_id, selected_index, is_correct, answered_at)
           VALUES (?, ?, ?, ?, ?)""",
        (doc_id, question_id, selected_index, 1 if is_correct else 0, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = get_db_connection()
    total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    total_quizzes = conn.execute("SELECT COUNT(*) FROM quiz_questions").fetchone()[0]
    avg_score = conn.execute(
        "SELECT COALESCE(AVG(is_correct) * 100, 0) FROM quiz_attempts"
    ).fetchone()[0]
    conn.close()
    return {
        "total_documents": total,
        "processed_documents": total,
        "total_quizzes": total_quizzes,
        "average_score": round(avg_score, 1),
    }


def delete_document_db(doc_id: int) -> None:
    conn = get_db_connection()
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()
