"""Create a SYNTHETIC university database (no real people or records)."""
import random
import sqlite3

random.seed(42)
DB = "university.db"

DEPARTMENTS = {
    "Computer Science": ["Intro to Programming", "Data Structures", "Algorithms", "Databases",
                         "Operating Systems", "Software Engineering", "Web Development",
                         "Machine Learning", "Computer Networks", "Cybersecurity"],
    "Mathematics": ["Calculus I", "Calculus II", "Linear Algebra", "Discrete Math",
                    "Probability", "Statistics", "Numerical Methods", "Abstract Algebra"],
    "Mechanical Engineering": ["Statics", "Dynamics", "Thermodynamics", "Fluid Mechanics",
                               "Materials Science", "Machine Design", "Heat Transfer", "Controls"],
    "Electrical Engineering": ["Circuits I", "Circuits II", "Signals and Systems", "Digital Logic",
                               "Electromagnetics", "Power Systems", "Embedded Systems", "Microelectronics"],
    "Civil Engineering": ["Structural Analysis", "Soil Mechanics", "Hydrology", "Transportation",
                          "Construction Management", "Surveying"],
}
TERMS = ["Fall 2024", "Winter 2025", "Fall 2025", "Winter 2026", "Fall 2026"]
FIRST = ["Alex", "Sam", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Avery", "Quinn"]
LAST = ["Nguyen", "Patel", "Okafor", "Silva", "Kim", "Haddad", "Novak", "Moreau", "Tanaka", "Singh"]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.executescript("""
        DROP TABLE IF EXISTS sections; DROP TABLE IF EXISTS courses; DROP TABLE IF EXISTS terms;
        CREATE TABLE terms (term_id INTEGER PRIMARY KEY, name TEXT, year INTEGER, season TEXT);
        CREATE TABLE courses (course_id INTEGER PRIMARY KEY, code TEXT, title TEXT,
                              department TEXT, credits INTEGER, level INTEGER);
        CREATE TABLE sections (section_id INTEGER PRIMARY KEY, course_id INTEGER, term_id INTEGER,
                               section_no INTEGER, instructor TEXT, capacity INTEGER,
                               enrolled INTEGER, avg_grade REAL,
                               FOREIGN KEY (course_id) REFERENCES courses(course_id),
                               FOREIGN KEY (term_id) REFERENCES terms(term_id));
    """)
    for i, name in enumerate(TERMS, 1):
        season, year = name.split()
        cur.execute("INSERT INTO terms VALUES (?,?,?,?)", (i, name, int(year), season))

    cid = 0
    instructors = {d: [f"{random.choice(FIRST)} {random.choice(LAST)}" for _ in range(6)] for d in DEPARTMENTS}
    popularity = {}
    for dept, titles in DEPARTMENTS.items():
        prefix = "".join(w[0] for w in dept.split())
        for n, title in enumerate(titles):
            cid += 1
            level = random.choice([1, 2, 3, 4])
            cur.execute("INSERT INTO courses VALUES (?,?,?,?,?,?)",
                        (cid, f"{prefix}{level}{n:02d}", title, dept, random.choice([3, 3, 3, 4]), level))
            popularity[cid] = random.uniform(0.45, 1.0) * (1.15 if dept == "Computer Science" else 1.0)

    sid = 0
    for course_id, pop in popularity.items():
        dept = cur.execute("SELECT department FROM courses WHERE course_id=?", (course_id,)).fetchone()[0]
        for term_id in range(1, len(TERMS) + 1):
            for section_no in range(1, random.choice([3, 4, 5, 6]) + 1):
                sid += 1
                cap = random.choice([30, 40, 60, 80, 120])
                enrolled = min(cap, int(cap * min(1.0, pop * random.uniform(0.6, 1.05))))
                grade = round(max(55, min(92, random.gauss(74, 6))), 1)
                cur.execute("INSERT INTO sections VALUES (?,?,?,?,?,?,?,?)",
                            (sid, course_id, term_id, section_no, random.choice(instructors[dept]),
                             cap, enrolled, grade))
    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM sections").fetchone()[0]
    print(f"Created {DB}: {cid} courses, {len(TERMS)} terms, {n} sections (synthetic data).")
    con.close()


if __name__ == "__main__":
    main()
