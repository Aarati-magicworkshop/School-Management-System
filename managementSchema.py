
################################################################################
# This script sets up a simple school management system using SQLite.
# It creates tables for users, classes, enrollments, assignments, submissions,
# and announcements.
################################################################################
################################## USER STORY ##################################
################################################################################

# As a system architect, I want to design a relational database schema that 
# supports user roles, classes, assignments, and submissions.

# Requirements:
    # Database includes tables for Users, Classes, Enrollments, Assignments, 
            # Submissions, and Announcements.
    # Each user can have a role: teacher, student, or admin.
    # A class can have one teacher and multiple students.
    # A user can be enrolled in multiple classes.
    # Assignments are linked to a class and have due dates.
    # Students can submit assignments with timestamps and attached files/URLs.
    # Announcements are linked to classes and visible to all enrolled users.
    # Schema is normalized (3NF) and indexed appropriately for performance.
    # An ER diagram is created and documented.

################################################################################

# ER link
# https://drive.google.com/file/d/1jGHi9hpP4KlwfOHF5KQrZoUxr0FDbPO8/view?usp=sharing

################################################################################
import sqlite3
import datetime
import textwrap
from pathlib import Path


DB_PATH = Path("management.db")
SCHEMA_PATH= Path("schema.sql")

DDL = """
PRAGMA foreign_keys = ON;



-- USERS: Teachers, Students, Admins
CREATE TABLE IF NOT EXISTS Users (
    id            INTEGER PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('teacher','student','admin')),
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);


-- CLASSES table: drop teacher_id to allow multiple teachers per class
CREATE TABLE IF NOT EXISTS Classes (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    description TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Teacher_Class: Junction table to link teachers and classes (M:N)
CREATE TABLE IF NOT EXISTS TeacherClass (
    teacher_id  INTEGER NOT NULL,
    class_id    INTEGER NOT NULL,
    PRIMARY KEY (teacher_id, class_id),
    FOREIGN KEY (teacher_id) REFERENCES Users(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES Classes(id) ON DELETE CASCADE
);


-- ENROLLMENTS: Students in classes
CREATE TABLE IF NOT EXISTS Enrollments (
    user_id     INTEGER NOT NULL,
    class_id    INTEGER NOT NULL,
    enrolled_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, class_id),
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES Classes(id) ON DELETE CASCADE
);

-- ASSIGNMENTS: Belong to a class
CREATE TABLE IF NOT EXISTS Assignments (
    id           INTEGER PRIMARY KEY,
    class_id     INTEGER NOT NULL,
    title        TEXT NOT NULL,
    description  TEXT,
    due_at       TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (class_id) REFERENCES Classes(id) ON DELETE CASCADE
);

-- SUBMISSIONS: Multiple attempts per student per assignment
CREATE TABLE IF NOT EXISTS Submissions (
    id             INTEGER PRIMARY KEY,
    assignment_id  INTEGER NOT NULL,
    student_id     INTEGER NOT NULL,
    attempt_number INTEGER NOT NULL DEFAULT 1,
    submitted_at   TEXT NOT NULL DEFAULT (datetime('now')),
    grade          REAL,
    feedback       TEXT,
    UNIQUE (assignment_id, student_id, attempt_number),
    FOREIGN KEY (assignment_id) REFERENCES Assignments(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- SUBMISSION ATTACHMENTS: URLs or file paths
CREATE TABLE IF NOT EXISTS SubmissionAttachments (
    id             INTEGER PRIMARY KEY,
    submission_id  INTEGER NOT NULL,
    kind           TEXT NOT NULL CHECK (kind IN ('url','file')),
    value          TEXT NOT NULL,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (submission_id) REFERENCES Submissions(id) ON DELETE CASCADE
);

-- ANNOUNCEMENTS: Linked to classes
CREATE TABLE IF NOT EXISTS Announcements (
    id          INTEGER PRIMARY KEY,
    class_id    INTEGER NOT NULL,
    author_id   INTEGER NOT NULL,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL,
    posted_at   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (class_id) REFERENCES Classes(id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES Users(id) ON DELETE RESTRICT
);

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_teacherclass_teacher  ON TeacherClass(teacher_id);
CREATE INDEX IF NOT EXISTS idx_teacherclass_class    ON TeacherClass(class_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_user     ON Enrollments(user_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_class    ON Enrollments(class_id);
CREATE INDEX IF NOT EXISTS idx_assignments_class    ON Assignments(class_id);
CREATE INDEX IF NOT EXISTS idx_assignments_due      ON Assignments(due_at);
CREATE INDEX IF NOT EXISTS idx_submissions_assign   ON Submissions(assignment_id);
CREATE INDEX IF NOT EXISTS idx_submissions_student  ON Submissions(student_id);
CREATE INDEX IF NOT EXISTS idx_submissions_time     ON Submissions(submitted_at);
CREATE INDEX IF NOT EXISTS idx_attach_submission    ON SubmissionAttachments(submission_id);
CREATE INDEX IF NOT EXISTS idx_announcements_class  ON Announcements(class_id);
CREATE INDEX IF NOT EXISTS idx_announcements_time   ON Announcements(posted_at);

-- TRIGGERS

-- Only teachers can be set as TeacherClass.teacher_id
CREATE TRIGGER IF NOT EXISTS trg_teacherclass_teacher_role
BEFORE INSERT ON TeacherClass
FOR EACH ROW
WHEN (SELECT role FROM Users WHERE id = NEW.teacher_id) <> 'teacher'
BEGIN
  SELECT RAISE(ABORT, 'TeacherClass.teacher_id must reference a user with role=teacher');
END;


-- Enrollments must reference students
CREATE TRIGGER IF NOT EXISTS trg_enrollments_student_role
BEFORE INSERT ON Enrollments
FOR EACH ROW
WHEN (SELECT role FROM Users WHERE id = NEW.user_id) <> 'student'
BEGIN
  SELECT RAISE(ABORT, 'Enrollments.user_id must reference a user with role=student');
END;

-- Submissions must be by students
CREATE TRIGGER IF NOT EXISTS trg_submissions_student_role
BEFORE INSERT ON Submissions
FOR EACH ROW
WHEN (SELECT role FROM Users WHERE id = NEW.student_id) <> 'student'
BEGIN
  SELECT RAISE(ABORT, 'Submissions.student_id must reference a user with role=student');
END;

-- Submitting student must be enrolled in the assignment's class
CREATE TRIGGER IF NOT EXISTS trg_submissions_student_enrolled
BEFORE INSERT ON Submissions
FOR EACH ROW
WHEN NOT EXISTS (
    SELECT 1
    FROM Assignments a
    JOIN Enrollments e ON e.class_id = a.class_id AND e.user_id = NEW.student_id
    WHERE a.id = NEW.assignment_id
)
BEGIN
  SELECT RAISE(ABORT, 'Student must be enrolled in the class for this assignment');
END;

-- Announcements must be authored by the class's teacher
CREATE TRIGGER IF NOT EXISTS trg_announcements_author_is_assigned_teacher
BEFORE INSERT ON Announcements
FOR EACH ROW
WHEN NOT EXISTS (
  SELECT 1 FROM TeacherClass
  WHERE class_id = NEW.class_id
    AND teacher_id = NEW.author_id
)
BEGIN
  SELECT RAISE(ABORT, 'Announcements.author_id must be a teacher assigned to this class');
END;
"""

def create_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(DDL)
    conn.commit()
    return conn

def write_schema():
    SCHEMA_PATH.write_text(textwrap.dedent(DDL).strip() + "\n", encoding="utf-8")

def main():
    write_schema()
    conn = create_db()
    print("Created:", DB_PATH, "and schema:", SCHEMA_PATH)


if __name__ == "__main__":
    main()
