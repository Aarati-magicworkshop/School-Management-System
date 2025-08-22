
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import List, Optional, Any, Dict, Tuple

from fastapi import FastAPI, HTTPException, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr

DB_PATH = "management.db"

# ---------------- DB helpers ----------------
@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def one(cur) -> Optional[Dict[str, Any]]:
    r = cur.fetchone()
    return dict(r) if r else None

def many(cur) -> List[Dict[str, Any]]:
    return [dict(r) for r in cur.fetchall()]

def ensure_schema():
    # Attempt to detect any table; if not present, import and run managementSchema
    with get_conn() as con:
        try:
            con.execute("SELECT 1 FROM Users LIMIT 1")
        except sqlite3.OperationalError:
            # Fallback: execute DDL from managementSchema.py (import) if available
            try:
                import managementSchema  # type: ignore
                managementSchema.main()
            except Exception as e:
                raise RuntimeError("Database not initialized. Run managementSchema.py first.") from e

# ---------------- Pydantic models ----------------
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    role: str = Field(pattern="^(teacher|student|admin)$")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    role: Optional[str] = Field(default=None, pattern="^(teacher|student|admin)$")

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    created_at: str

class ClassCreate(BaseModel):
    code: str
    title: str
    description: Optional[str] = ""
    # teacher_id: int

class ClassUpdate(BaseModel):
    code: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    # teacher_id: Optional[int] = None

class ClassOut(BaseModel):
    id: int
    code: str
    title: str
    description: Optional[str] = None
    # teacher_id: int
    created_at: str

class TeacherClassCreate(BaseModel):
    teacher_id: int
    class_id: int

class TeacherClassOut(BaseModel):
    teacher_id: int
    class_id: int
    # enrolled_at: str

class EnrollmentCreate(BaseModel):
    user_id: int
    class_id: int

class EnrollmentOut(BaseModel):
    user_id: int
    class_id: int
    enrolled_at: str

class AssignmentCreate(BaseModel):
    class_id: int
    title: str
    description: Optional[str] = ""
    due_at: str  

class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_at: Optional[str] = None

class AssignmentOut(BaseModel):
    id: int
    class_id: int
    title: str
    description: Optional[str] = None
    due_at: str
    created_at: str
    updated_at: Optional[str] = None

class SubmissionCreate(BaseModel):
    assignment_id: int
    student_id: int
    attempt_number: int = 1
    grade: Optional[float] = None
    feedback: Optional[str] = None

class SubmissionUpdate(BaseModel):
    grade: Optional[float] = None
    feedback: Optional[str] = None

class SubmissionOut(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    attempt_number: int
    submitted_at: str
    grade: Optional[float] = None
    feedback: Optional[str] = None

class AttachmentCreate(BaseModel):
    submission_id: int
    kind: str = Field(pattern="^(url|file)$")
    value: str

class AttachmentOut(BaseModel):
    id: int
    submission_id: int
    kind: str
    value: str
    created_at: str

class AnnouncementCreate(BaseModel):
    class_id: int
    author_id: int
    title: str
    body: str

class AnnouncementOut(BaseModel):
    id: int
    class_id: int
    author_id: int
    title: str
    body: str
    posted_at: str

# ---------------- FastAPI setup ----------------
app = FastAPI(title="School Management API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    ensure_schema()

# ---------------- Users ----------------
@app.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    with get_conn() as con:
        try:
            cur = con.execute(
                "INSERT INTO Users(email, full_name, role) VALUES(?,?,?)",
                (user.email, user.full_name, user.role),
            )
        except sqlite3.IntegrityError as e:
            raise HTTPException(409, f"User conflict: {e}")
        uid = cur.lastrowid
        cur = con.execute("SELECT * FROM Users WHERE id=?", (uid,))
        return one(cur)

@app.get("/users", response_model=List[UserOut])
def list_users(role: Optional[str] = Query(default=None), limit: int = 100, offset: int = 0):
    with get_conn() as con:
        if role:
            cur = con.execute("SELECT * FROM Users WHERE role=? ORDER BY id LIMIT ? OFFSET ?", (role, limit, offset))
        else:
            cur = con.execute("SELECT * FROM Users ORDER BY id LIMIT ? OFFSET ?", (limit, offset))
        return many(cur)

@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int):
    with get_conn() as con:
        cur = con.execute("SELECT * FROM Users WHERE id=?", (user_id,))
        row = one(cur)
        if not row: raise HTTPException(404, "User not found")
        return row

@app.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, patch: UserUpdate):
    sets, params = [], []
    if patch.email is not None:
        sets.append("email=?"); params.append(patch.email)
    if patch.full_name is not None:
        sets.append("full_name=?"); params.append(patch.full_name)
    if patch.role is not None:
        sets.append("role=?"); params.append(patch.role)
    if not sets:
        raise HTTPException(400, "No fields to update")
    params.append(user_id)
    with get_conn() as con:
        try:
            con.execute(f"UPDATE Users SET {', '.join(sets)} WHERE id=?", params)
        except sqlite3.IntegrityError as e:
            raise HTTPException(409, f"Update conflict: {e}")
        cur = con.execute("SELECT * FROM Users WHERE id=?", (user_id,))
        row = one(cur)
        if not row: raise HTTPException(404, "User not found")
        return row

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int):
    with get_conn() as con:
        cur = con.execute("DELETE FROM Users WHERE id=?", (user_id,))
        if cur.rowcount == 0: raise HTTPException(404, "User not found")
        return

# ---------------- Classes ----------------
@app.post("/classes", response_model=ClassOut, status_code=status.HTTP_201_CREATED)
def create_class(payload: ClassCreate):
    with get_conn() as con:
        try:
            cur = con.execute(
                "INSERT INTO Classes(code, title, description) VALUES(?,?,?)",
                (payload.code, payload.title, payload.description),
            )
        except sqlite3.IntegrityError as e:
            raise HTTPException(409, f"Class conflict: {e}")
        cid = cur.lastrowid
        cur = con.execute("SELECT * FROM Classes WHERE id=?", (cid,))
        return one(cur)

@app.get("/classes", response_model=List[ClassOut])
def list_classes(id: Optional[int] = None, limit: int = 100, offset: int = 0):
    with get_conn() as con:
        if id is not None:
            cur = con.execute("SELECT * FROM Classes WHERE id=? ORDER BY id LIMIT ? OFFSET ?", (id, limit, offset))
        else:
            cur = con.execute("SELECT * FROM Classes ORDER BY id LIMIT ? OFFSET ?", (limit, offset))
        return many(cur)

@app.get("/classes/{class_id}", response_model=ClassOut)
def get_class(class_id: int):
    with get_conn() as con:
        cur = con.execute("SELECT * FROM Classes WHERE id=?", (class_id,))
        row = one(cur)
        if not row: raise HTTPException(404, "Class not found")
        return row

@app.patch("/classes/{class_id}", response_model=ClassOut)
def update_class(class_id: int, patch: ClassUpdate):
    sets, params = [], []
    for field, value in patch.dict(exclude_unset=True).items():
        sets.append(f"{field}=?"); params.append(value)
    if not sets:
        raise HTTPException(400, "No fields to update")
    params.append(class_id)
    with get_conn() as con:
        try:
            con.execute(f"UPDATE Classes SET {', '.join(sets)} WHERE id=?", params)
        except sqlite3.IntegrityError as e:
            raise HTTPException(409, f"Update conflict: {e}")
        cur = con.execute("SELECT * FROM Classes WHERE id=?", (class_id,))
        row = one(cur)
        if not row: raise HTTPException(404, "Class not found")
        return row

@app.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(class_id: int):
    with get_conn() as con:
        cur = con.execute("DELETE FROM Classes WHERE id=?", (class_id,))
        if cur.rowcount == 0: raise HTTPException(404, "Class not found")
        return

# ---------------- Enrollments ----------------
@app.post("/enrollments", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED)
def enroll(payload: EnrollmentCreate):
    with get_conn() as con:
        try:
            con.execute("INSERT INTO Enrollments(user_id, class_id) VALUES(?,?)", (payload.user_id, payload.class_id))
        except sqlite3.IntegrityError as e:
            raise HTTPException(409, f"Enrollment failed: {e}")
        cur = con.execute("SELECT * FROM Enrollments WHERE user_id=? AND class_id=?", (payload.user_id, payload.class_id))
        return one(cur)

@app.get("/enrollments", response_model=List[EnrollmentOut])
def list_enrollments(class_id: Optional[int] = None, user_id: Optional[int] = None, limit: int = 100, offset: int = 0):
    with get_conn() as con:
        if class_id is not None and user_id is not None:
            cur = con.execute("SELECT * FROM Enrollments WHERE class_id=? AND user_id=? ORDER BY enrolled_at LIMIT ? OFFSET ?", (class_id, user_id, limit, offset))
        elif class_id is not None:
            cur = con.execute("SELECT * FROM Enrollments WHERE class_id=? ORDER BY user_id LIMIT ? OFFSET ?", (class_id, limit, offset))
        elif user_id is not None:
            cur = con.execute("SELECT * FROM Enrollments WHERE user_id=? ORDER BY class_id LIMIT ? OFFSET ?", (user_id, limit, offset))
        else:
            cur = con.execute("SELECT * FROM Enrollments ORDER BY class_id, user_id LIMIT ? OFFSET ?", (limit, offset))
        return many(cur)

@app.delete("/enrollments", status_code=status.HTTP_204_NO_CONTENT)
def unenroll(user_id: int, class_id: int):
    with get_conn() as con:
        cur = con.execute("DELETE FROM Enrollments WHERE user_id=? AND class_id=?", (user_id, class_id))
        if cur.rowcount == 0: raise HTTPException(404, "Enrollment not found")
        return


# ---------------- TeacherClass ----------------
@app.post("/teacherassigned", response_model=TeacherClassOut, status_code=status.HTTP_201_CREATED)
def teacherassigne(payload: TeacherClassCreate):
    with get_conn() as con:
        try:
            con.execute("INSERT INTO TeacherClass(teacher_id, class_id) VALUES(?,?)", (payload.teacher_id, payload.class_id))
        except sqlite3.IntegrityError as e:
            raise HTTPException(409, f"Teacher class assignment failed: {e}")
        cur = con.execute("SELECT * FROM TeacherClass WHERE teacher_id=? AND class_id=?", (payload.teacher_id, payload.class_id))
        return one(cur)

@app.get("/teacherassigned", response_model=List[TeacherClassOut])
def list_teacherassigned(teacher_id: Optional[int] = None, class_id: Optional[int] = None, limit: int = 100, offset: int = 0):
    with get_conn() as con:
        if class_id is not None and teacher_id is not None:
            cur = con.execute("SELECT * FROM TeacherClass WHERE class_id=? AND teacher_id=? ORDER BY teacher_id LIMIT ? OFFSET ?", (class_id, teacher_id, limit, offset))
        elif class_id is not None:
            cur = con.execute("SELECT * FROM TeacherClass WHERE class_id=? ORDER BY teacher_id LIMIT ? OFFSET ?", (class_id, limit, offset))
        elif teacher_id is not None:
            cur = con.execute("SELECT * FROM TeacherClass WHERE teacher_id=? ORDER BY class_id LIMIT ? OFFSET ?", (teacher_id, limit, offset))
        else:
            cur = con.execute("SELECT * FROM TeacherClass ORDER BY teacher_id, class_id LIMIT ? OFFSET ?", (limit, offset))
        return many(cur)

@app.delete("/teacherassigned", status_code=status.HTTP_204_NO_CONTENT)
def unenroll(teacher_id: int, class_id: int):
    with get_conn() as con:
        cur = con.execute("DELETE FROM TeacherClass WHERE teacher_id=? AND class_id=?", (teacher_id, class_id))
        if cur.rowcount == 0: raise HTTPException(404, "Enrollment not found")
        return


# ---------------- Assignments ----------------
@app.post("/assignments", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment(payload: AssignmentCreate):
    with get_conn() as con:
        try:
            cur = con.execute(
                "INSERT INTO Assignments(class_id, title, description, due_at) VALUES(?,?,?,?)",
                (payload.class_id, payload.title, payload.description, payload.due_at),
            )
        except sqlite3.IntegrityError as e:
            raise HTTPException(409, f"Assignment conflict: {e}")
        aid = cur.lastrowid
        cur = con.execute("SELECT * FROM Assignments WHERE id=?", (aid,))
        return one(cur)

@app.get("/assignments", response_model=List[AssignmentOut])
def list_assignments(class_id: Optional[int] = None, limit: int = 100, offset: int = 0):
    with get_conn() as con:
        if class_id is not None:
            cur = con.execute("SELECT * FROM Assignments WHERE class_id=? ORDER BY due_at LIMIT ? OFFSET ?", (class_id, limit, offset))
        else:
            cur = con.execute("SELECT * FROM Assignments ORDER BY due_at LIMIT ? OFFSET ?", (limit, offset))
        return many(cur)

@app.get("/assignments/{assignment_id}", response_model=AssignmentOut)
def get_assignment(assignment_id: int):
    with get_conn() as con:
        cur = con.execute("SELECT * FROM Assignments WHERE id=?", (assignment_id,))
        row = one(cur)
        if not row: raise HTTPException(404, "Assignment not found")
        return row

@app.patch("/assignments/{assignment_id}", response_model=AssignmentOut)
def update_assignment(assignment_id: int, patch: AssignmentUpdate):
    sets, params = [], []
    for field, value in patch.dict(exclude_unset=True).items():
        sets.append(f"{field}=?"); params.append(value)
    if not sets:
        raise HTTPException(400, "No fields to update")
    params.append(assignment_id)
    with get_conn() as con:
        con.execute(f"UPDATE Assignments SET {', '.join(sets)} WHERE id=?", params)
        cur = con.execute("SELECT * FROM Assignments WHERE id=?", (assignment_id,))
        row = one(cur)
        if not row: raise HTTPException(404, "Assignment not found")
        return row

@app.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(assignment_id: int):
    with get_conn() as con:
        cur = con.execute("DELETE FROM Assignments WHERE id=?", (assignment_id,))
        if cur.rowcount == 0: raise HTTPException(404, "Assignment not found")
        return

# ---------------- Submissions ----------------
# @app.post("/submissions", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
# def create_submission(payload: SubmissionCreate):
#     with get_conn() as con:
#         try:
#             cur = con.execute(
#                 "INSERT INTO Submissions(assignment_id, student_id, attempt_number, grade, feedback) VALUES(?,?,?,?,?)",
#                 (payload.assignment_id, payload.student_id, payload.attempt_number, payload.grade, payload.feedback),
#             )
#         except sqlite3.IntegrityError as e:
#             raise HTTPException(409, f"Submission conflict: {e}")
#         sid = cur.lastrowid
#         cur = con.execute("SELECT * FROM Submissions WHERE id=?", (sid,))
#         return one(cur)


#automatically increment attempt_number
@app.post("/submissions", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
def create_submission(payload: SubmissionCreate):
    with get_conn() as con:
        # find last attempt for this student+assignment
        cur = con.execute(
            "SELECT COALESCE(MAX(attempt_number), 0) FROM Submissions WHERE assignment_id=? AND student_id=?",
            (payload.assignment_id, payload.student_id)
        )
        last_attempt = cur.fetchone()[0]
        new_attempt = last_attempt + 1

        try:
            cur = con.execute(
                "INSERT INTO Submissions(assignment_id, student_id, attempt_number, grade, feedback) VALUES(?,?,?,?,?)",
                (payload.assignment_id, payload.student_id, new_attempt, payload.grade, payload.feedback),
            )
        except sqlite3.IntegrityError as e:
            raise HTTPException(409, f"Submission conflict: {e}")

        sid = cur.lastrowid
        cur = con.execute("SELECT * FROM Submissions WHERE id=?", (sid,))
        return one(cur)


@app.get("/submissions", response_model=List[SubmissionOut])
def list_submissions(assignment_id: Optional[int] = None, student_id: Optional[int] = None, limit: int = 100, offset: int = 0):
    with get_conn() as con:
        if assignment_id is not None and student_id is not None:
            cur = con.execute("SELECT * FROM Submissions WHERE assignment_id=? AND student_id=? ORDER BY attempt_number LIMIT ? OFFSET ?", (assignment_id, student_id, limit, offset))
        elif assignment_id is not None:
            cur = con.execute("SELECT * FROM Submissions WHERE assignment_id=? ORDER BY student_id, attempt_number LIMIT ? OFFSET ?", (assignment_id, limit, offset))
        elif student_id is not None:
            cur = con.execute("SELECT * FROM Submissions WHERE student_id=? ORDER BY assignment_id, attempt_number LIMIT ? OFFSET ?", (student_id, limit, offset))
        else:
            cur = con.execute("SELECT * FROM Submissions ORDER BY id LIMIT ? OFFSET ?", (limit, offset))
        return many(cur)

@app.patch("/submissions/{submission_id}", response_model=SubmissionOut)
def update_submission(submission_id: int, patch: SubmissionUpdate):
    sets, params = [], []
    for field, value in patch.dict(exclude_unset=True).items():
        sets.append(f"{field}=?"); params.append(value)
    if not sets:
        raise HTTPException(400, "No fields to update")
    params.append(submission_id)
    with get_conn() as con:
        con.execute(f"UPDATE Submissions SET {', '.join(sets)} WHERE id=?", params)
        cur = con.execute("SELECT * FROM Submissions WHERE id=?", (submission_id,))
        row = one(cur)
        if not row: raise HTTPException(404, "Submission not found")
        return row

@app.delete("/submissions/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_submission(submission_id: int):
    with get_conn() as con:
        cur = con.execute("DELETE FROM Submissions WHERE id=?", (submission_id,))
        if cur.rowcount == 0: raise HTTPException(404, "Submission not found")
        return

# ---------------- Attachments ----------------
@app.post("/attachments", response_model=AttachmentOut, status_code=status.HTTP_201_CREATED)
def create_attachment(payload: AttachmentCreate):
    with get_conn() as con:
        try:
            cur = con.execute(
                "INSERT INTO SubmissionAttachments(submission_id, kind, value) VALUES(?,?,?)",
                (payload.submission_id, payload.kind, payload.value),
            )
        except sqlite3.IntegrityError as e:
            raise HTTPException(409, f"Attachment conflict: {e}")
        aid = cur.lastrowid
        cur = con.execute("SELECT * FROM SubmissionAttachments WHERE id=?", (aid,))
        return one(cur)

@app.get("/attachments", response_model=List[AttachmentOut])
def list_attachments(submission_id: Optional[int] = None, limit: int = 100, offset: int = 0):
    with get_conn() as con:
        if submission_id is not None:
            cur = con.execute("SELECT * FROM SubmissionAttachments WHERE submission_id=? ORDER BY id LIMIT ? OFFSET ?", (submission_id, limit, offset))
        else:
            cur = con.execute("SELECT * FROM SubmissionAttachments ORDER BY id LIMIT ? OFFSET ?", (limit, offset))
        return many(cur)

@app.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(attachment_id: int):
    with get_conn() as con:
        cur = con.execute("DELETE FROM SubmissionAttachments WHERE id=?", (attachment_id,))
        if cur.rowcount == 0: raise HTTPException(404, "Attachment not found")
        return

# ---------------- Announcements ----------------
@app.post("/announcements", response_model=AnnouncementOut, status_code=status.HTTP_201_CREATED)
def create_announcement(payload: AnnouncementCreate):
    with get_conn() as con:
        try:
            cur = con.execute(
                "INSERT INTO Announcements(class_id, author_id, title, body) VALUES(?,?,?,?)",
                (payload.class_id, payload.author_id, payload.title, payload.body),
            )
        except sqlite3.IntegrityError as e:
            raise HTTPException(409, f"Announcement conflict: {e}")
        aid = cur.lastrowid
        cur = con.execute("SELECT * FROM Announcements WHERE id=?", (aid,))
        return one(cur)

@app.get("/announcements", response_model=List[AnnouncementOut])
def list_announcements(class_id: int, limit: int = 100, offset: int = 0):
    with get_conn() as con:
        cur = con.execute("SELECT * FROM Announcements WHERE class_id=? ORDER BY posted_at DESC LIMIT ? OFFSET ?", (class_id, limit, offset))
        return many(cur)

@app.delete("/announcements/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(announcement_id: int):
    with get_conn() as con:
        cur = con.execute("DELETE FROM Announcements WHERE id=?", (announcement_id,))
        if cur.rowcount == 0: raise HTTPException(404, "Announcement not found")
        return

