
from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple, Dict, Any
import subprocess
import sys
from pathlib import Path

DB_PATH = Path("management.db")

# ----------------------- helpers -----------------------
@contextmanager
def connect(db_path: Path = DB_PATH):
    """Context manager that yields a sqlite3 connection with FK enforcement on."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
        conn.commit()
    finally:
        conn.close()

def row_to_dict(cursor: sqlite3.Cursor, row: Tuple[Any, ...]) -> Dict[str, Any]:
    return {d[0]: v for d, v in zip(cursor.description, row)}

def fetchone_dict(cur: sqlite3.Cursor) -> Optional[Dict[str, Any]]:
    row = cur.fetchone()
    return row_to_dict(cur, row) if row else None

def fetchall_dicts(cur: sqlite3.Cursor) -> List[Dict[str, Any]]:
    rows = cur.fetchall()
    return [row_to_dict(cur, r) for r in rows]

# ----------------------- Users Entity CRUD Operations -----------------------
def create_user(email: str, full_name: str, role: str) -> int:
    with connect() as con:
        cur = con.execute(
            "INSERT INTO Users(email, full_name, role) VALUES(?,?,?)",
            (email, full_name, role),
        )
        return cur.lastrowid

def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    with connect() as con:
        cur = con.execute("SELECT * FROM Users WHERE id=?", (user_id,))
        return fetchone_dict(cur)

def list_users(role: Optional[str] = None) -> List[Dict[str, Any]]:
    with connect() as con:
        if role:
            cur = con.execute("SELECT * FROM Users WHERE role=? ORDER BY id", (role,))
        else:
            cur = con.execute("SELECT * FROM Users ORDER BY id")
        return fetchall_dicts(cur)

def update_user(user_id: int, *, email: Optional[str]=None, full_name: Optional[str]=None, role: Optional[str]=None) -> int:
    sets, params = [], []
    if email is not None:
        sets.append("email=?"); params.append(email)
    if full_name is not None:
        sets.append("full_name=?"); params.append(full_name)
    if role is not None:
        sets.append("role=?"); params.append(role)
    if not sets:
        return 0
    params.append(user_id)
    with connect() as con:
        cur = con.execute(f"UPDATE Users SET {', '.join(sets)} WHERE id=?", params)
        return cur.rowcount

def delete_user(user_id: int) -> int:
    with connect() as con:
        cur = con.execute("DELETE FROM Users WHERE id=?", (user_id,))
        return cur.rowcount

# ----------------------- Classes entity CRUD operations -----------------------
def create_class(code: str, title: str, description: str) -> int:
    with connect() as con:
        cur = con.execute(
            "INSERT INTO Classes(code, title, description) VALUES(?,?,?)",
            (code, title, description),
        )
        return cur.lastrowid

def get_class(class_id: int) -> Optional[Dict[str, Any]]:
    with connect() as con:
        cur = con.execute("SELECT * FROM Classes WHERE id=?", (class_id,))
        return fetchone_dict(cur)

def list_classes():
    with connect() as con:
        cur = con.execute("SELECT * FROM Classes ORDER BY id")
        return fetchall_dicts(cur)

def update_class(class_id: int, *, code: Optional[str]=None, title: Optional[str]=None, description: Optional[str]=None) -> int:
    sets, params = [], []
    if code is not None:
        sets.append("code=?"); params.append(code)
    if title is not None:
        sets.append("title=?"); params.append(title)
    if description is not None:
        sets.append("description=?"); params.append(description)
    if not sets:
        return 0
    params.append(class_id)
    with connect() as con:
        cur = con.execute(f"UPDATE Classes SET {', '.join(sets)} WHERE id=?", params)
        return cur.rowcount

def delete_class(class_id: int) -> int:
    with connect() as con:
        cur = con.execute("DELETE FROM Classes WHERE id=?", (class_id,))
        return cur.rowcount

# ----------------------- Enrollment entity CRUD operations -----------------------
def enroll_student(user_id: int, class_id: int) -> None:
    with connect() as con:
        con.execute("INSERT INTO Enrollments(user_id, class_id) VALUES(?,?)", (user_id, class_id))

def list_enrollments(class_id: Optional[int]=None, user_id: Optional[int]=None) -> List[Dict[str, Any]]:
    with connect() as con:
        if class_id is not None and user_id is not None:
            cur = con.execute("SELECT * FROM Enrollments WHERE class_id=? AND user_id=? ORDER BY class_id, user_id", (class_id, user_id))
        elif class_id is not None:
            cur = con.execute("SELECT * FROM Enrollments WHERE class_id=? ORDER BY user_id", (class_id,))
        elif user_id is not None:
            cur = con.execute("SELECT * FROM Enrollments WHERE user_id=? ORDER BY class_id", (user_id,))
        else:
            cur = con.execute("SELECT * FROM Enrollments ORDER BY class_id, user_id")
        return fetchall_dicts(cur)

def unenroll_student(user_id: int, class_id: int) -> int:
    with connect() as con:
        cur = con.execute("DELETE FROM Enrollments WHERE user_id=? AND class_id=?", (user_id, class_id))
        return cur.rowcount
    
# ----------------------- TeacherClass entity CRUD operations -----------------------
def assign_teacher_to_class(teacher_id: int, class_id: int) -> None:
    with connect() as con:
        con.execute("INSERT INTO TeacherClasses(teacher_id, class_id) VALUES(?,?)", (teacher_id, class_id))

def list_teacherclasses(teacher_id: Optional[int]=None, class_id: Optional[int]=None) -> List[Dict[str, Any]]:
    with connect() as con:
        if teacher_id is not None and class_id is not None:
            cur = con.execute("SELECT * FROM TeacherClass WHERE teacher_id=? AND class_id=? ORDER BY teacher_id, class_id", (teacher_id, class_id))
        if teacher_id is not None:
            cur = con.execute("SELECT * FROM TeacherClass WHERE teacher_id=? ORDER BY class_id", (teacher_id,))
        elif class_id is not None:
            cur = con.execute("SELECT * FROM TeacherClass WHERE class_id=? ORDER BY teacher_id", (class_id,))
        else:
            cur = con.execute("SELECT * FROM TeacherClass ORDER BY teacher_id, class_id")
        return fetchall_dicts(cur)

def remove_teacher_from_class(teacher_id: int, class_id: int) -> int:
    with connect() as con:
        cur = con.execute("DELETE FROM TeacherClasses WHERE teacher_id=? AND class_id=?", (teacher_id, class_id))
        return cur.rowcount



# ----------------------- Assignments entity CRUD operations -----------------------
def create_assignment(class_id: int, title: str, description: str, due_at: str) -> int:
    with connect() as con:
        cur = con.execute(
            "INSERT INTO Assignments(class_id, title, description, due_at) VALUES(?,?,?,?)",
            (class_id, title, description, due_at),
        )
        return cur.lastrowid

def update_assignment(assignment_id: int, *, title: Optional[str]=None, description: Optional[str]=None, due_at: Optional[str]=None) -> int:
    sets, params = [], []
    if title is not None:
        sets.append("title=?"); params.append(title)
    if description is not None:
        sets.append("description=?"); params.append(description)
    if due_at is not None:
        sets.append("due_at=?"); params.append(due_at)
    if not sets:
        return 0
    params.append(assignment_id)
    with connect() as con:
        cur = con.execute(f"UPDATE Assignments SET {', '.join(sets)} WHERE id=?", params)
        return cur.rowcount

def get_assignment(assignment_id: int) -> Optional[Dict[str, Any]]:
    with connect() as con:
        cur = con.execute("SELECT * FROM Assignments WHERE id=?", (assignment_id,))
        return fetchone_dict(cur)

def delete_assignment(assignment_id: int) -> int:
    with connect() as con:
        cur = con.execute("DELETE FROM Assignments WHERE id=?", (assignment_id,))
        return cur.rowcount

# ----------------------- Submissions & Attachments CRUD -----------------------
def create_submission(assignment_id: int, student_id: int, attempt_number: int=1, grade: Optional[float]=None, feedback: Optional[str]=None) -> int:
    with connect() as con:
        cur = con.execute(
            "INSERT INTO Submissions(assignment_id, student_id, attempt_number, grade, feedback) VALUES(?,?,?,?,?)",
            (assignment_id, student_id, attempt_number, grade, feedback),
        )
        return cur.lastrowid

def add_attachment(submission_id: int, kind: str, value: str) -> int:
    with connect() as con:
        cur = con.execute(
            "INSERT INTO SubmissionAttachments(submission_id, kind, value) VALUES(?,?,?)",
            (submission_id, kind, value),
        )
        return cur.lastrowid

def grade_submission(submission_id: int, grade: float, feedback: Optional[str]=None) -> int:
    with connect() as con:
        cur = con.execute(
            "UPDATE Submissions SET grade=?, feedback=? WHERE id=?",
            (grade, feedback, submission_id),
        )
        return cur.rowcount

def list_submissions(assignment_id: Optional[int]=None, student_id: Optional[int]=None) -> List[Dict[str, Any]]:
    with connect() as con:
        if assignment_id is not None and student_id is not None:
            cur = con.execute("SELECT * FROM Submissions WHERE assignment_id=? AND student_id=? ORDER BY attempt_number", (assignment_id, student_id))
        elif assignment_id is not None:
            cur = con.execute("SELECT * FROM Submissions WHERE assignment_id=? ORDER BY student_id, attempt_number", (assignment_id,))
        elif student_id is not None:
            cur = con.execute("SELECT * FROM Submissions WHERE student_id=? ORDER BY assignment_id, attempt_number", (student_id,))
        else:
            cur = con.execute("SELECT * FROM Submissions ORDER BY id")
        return fetchall_dicts(cur)

def delete_submission(submission_id: int) -> int:
    with connect() as con:
        cur = con.execute("DELETE FROM Submissions WHERE id=?", (submission_id,))
        return cur.rowcount

# ----------------------- Announcements CRUD -----------------------
def create_announcement(class_id: int, author_id: int, title: str, body: str) -> int:
    with connect() as con:
        cur = con.execute(
            "INSERT INTO Announcements(class_id, author_id, title, body) VALUES(?,?,?,?)",
            (class_id, author_id, title, body),
        )
        return cur.lastrowid

def list_announcements(class_id: int) -> List[Dict[str, Any]]:
    with connect() as con:
        cur = con.execute("SELECT * FROM Announcements WHERE class_id=? ORDER BY posted_at DESC", (class_id,))
        return fetchall_dicts(cur)

def delete_announcement(announcement_id: int) -> int:
    with connect() as con:
        cur = con.execute("DELETE FROM Announcements WHERE id=?", (announcement_id,))
        return cur.rowcount


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        subprocess.check_call([sys.executable, "managementSchema.py"])
    # demo()
