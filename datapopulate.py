import sqlite3

data = {
    "users": [
        ("teacher1@example.com", "Alice Teacher", "teacher"),
        ("teacher2@example.com", "Bob Instructor", "teacher"),
        ("student1@example.com", "Charlie Student", "student"),
        ("student2@example.com", "Diana Learner", "student"),
        ("student3@example.com", "Ethan Pupil", "student"),
        ("admin1@example.com", "Admin One", "admin"),
    ],
    "classes": [
        ("CS101", "Intro to Computer Science", "Basics of programming and algorithms"),
        ("MATH201", "Discrete Mathematics", "Logic, sets, combinatorics, and graphs"),
    ],
    "teacher_class": [(1, 1), (2, 2),(1,2),(2,1)],
    "enrollments": [(3, 1), (4, 1), (5, 2), (3, 2)],
    "assignments": [
        (1, "Assignment 1", "Write a Python program for Fibonacci numbers", "2025-09-01 23:59:00"),
        (1, "Assignment 2", "Implement bubble sort in any language", "2025-09-10 23:59:00"),
        (2, "Homework 1", "Solve 10 problems on set theory", "2025-09-05 23:59:00"),
    ],
    "submissions": [
        (1, 3, 1, 90, "Excellent work"),
        (1, 4, 1, 75, "Good effort, optimize your code"),
        (2, 3, 1, 88, "Well done"),
        (3, 5, 1, None, "Pending grading"),
    ],
    "attachments": [
        (1, "file", "/uploads/charlie_fib.py"),
        (2, "file", "/uploads/diana_fib.py"),
        (3, "url", "https://github.com/charlie/bubblesort"),
        (4, "file", "/uploads/ethan_sets.pdf"),
    ],
    "announcements": [
        (1, 1, "Welcome to CS101", "Please install Python before the next class."),
        (2, 2, "Welcome to Math201", "Bring your discrete math textbook. Homework will be weekly."),
    ],
}

conn = sqlite3.connect("management.db")
cur = conn.cursor()

cur.executemany("INSERT INTO Users (email, full_name, role) VALUES (?, ?, ?)", data["users"])
cur.executemany("INSERT INTO Classes (code, title, description) VALUES (?, ?, ?)", data["classes"])
cur.executemany("INSERT INTO TeacherClass (teacher_id, class_id) VALUES (?, ?)", data["teacher_class"])
cur.executemany("INSERT INTO Enrollments (user_id, class_id) VALUES (?, ?)", data["enrollments"])
cur.executemany("INSERT INTO Assignments (class_id, title, description, due_at) VALUES (?, ?, ?, ?)", data["assignments"])
cur.executemany("INSERT INTO Submissions (assignment_id, student_id, attempt_number, grade, feedback) VALUES (?, ?, ?, ?, ?)", data["submissions"])
cur.executemany("INSERT INTO SubmissionAttachments (submission_id, kind, value) VALUES (?, ?, ?)", data["attachments"])
cur.executemany("INSERT INTO Announcements (class_id, author_id, title, body) VALUES (?, ?, ?, ?)", data["announcements"])

conn.commit()
conn.close()

print("Database seeded successfully ✅")
