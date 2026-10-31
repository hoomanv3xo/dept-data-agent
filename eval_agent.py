"""Run 15 test questions and report pass rate and average response time.

Each test has a ground-truth SQL query. The expected values are computed from the
database, and a test passes if every expected value appears in the agent's answer
or in the table it returned. Run:  python eval_agent.py
"""
import time
import re
import sqlite3
import statistics

import agent

TESTS = [
    ("How many courses are in the database?",
     "SELECT COUNT(*) FROM courses"),
    ("How many sections ran in Fall 2025?",
     "SELECT COUNT(*) FROM sections s JOIN terms t USING(term_id) WHERE t.name='Fall 2025'"),
    ("Which department has the most courses?",
     "SELECT department FROM courses GROUP BY department ORDER BY COUNT(*) DESC LIMIT 1"),
    ("What is the total enrollment across all sections in Fall 2026?",
     "SELECT SUM(enrolled) FROM sections s JOIN terms t USING(term_id) WHERE t.name='Fall 2026'"),
    ("Which course had the highest total enrollment in Winter 2025?",
     "SELECT c.title FROM sections s JOIN courses c USING(course_id) JOIN terms t USING(term_id) "
     "WHERE t.name='Winter 2025' GROUP BY c.course_id ORDER BY SUM(enrolled) DESC LIMIT 1"),
    ("How many sections have an average grade above 85?",
     "SELECT COUNT(*) FROM sections WHERE avg_grade > 85"),
    ("How many four-credit courses are there?",
     "SELECT COUNT(*) FROM courses WHERE credits = 4"),
    ("Which department has the largest total enrollment across all terms?",
     "SELECT c.department FROM sections s JOIN courses c USING(course_id) "
     "GROUP BY c.department ORDER BY SUM(enrolled) DESC LIMIT 1"),
    ("How many sections were completely full (enrolled equals capacity)?",
     "SELECT COUNT(*) FROM sections WHERE enrolled = capacity"),
    ("What is the largest capacity of any single section?",
     "SELECT MAX(capacity) FROM sections"),
    ("How many distinct instructors teach Mathematics courses?",
     "SELECT COUNT(DISTINCT instructor) FROM sections s JOIN courses c USING(course_id) "
     "WHERE c.department='Mathematics'"),
    ("Which term had the highest total enrollment?",
     "SELECT t.name FROM sections s JOIN terms t USING(term_id) GROUP BY t.term_id "
     "ORDER BY SUM(enrolled) DESC LIMIT 1"),
    ("How many first-year (level 1) courses are there?",
     "SELECT COUNT(*) FROM courses WHERE level = 1"),
    ("Which course has the lowest average grade across all its sections?",
     "SELECT c.title FROM sections s JOIN courses c USING(course_id) "
     "GROUP BY c.course_id ORDER BY AVG(avg_grade) ASC LIMIT 1"),
    ("How many sections ran across all terms?",
     "SELECT COUNT(*) FROM sections"),
]


def expected_values():
    con = sqlite3.connect("file:university.db?mode=ro", uri=True)
    out = []
    for _, sql in TESTS:
        out.append(str(con.execute(sql).fetchone()[0]))
    con.close()
    return out


def normalize(text):
    return re.sub(r"[,\s]", "", text.lower())


def main():
    expected = expected_values()
    passed, times = 0, []
    for (question, _), exp in zip(TESTS, expected):
        try:
            res = agent.ask(question)
            haystack = res["answer"] + " " + str(res["table"])
            ok = normalize(exp) in normalize(haystack)
            times.append(res["seconds"])
        except Exception as e:
            ok, res = False, {"answer": f"ERROR {getattr(e, 'status_code', '')}: {str(getattr(e, 'body', e))[:150]}"}
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'} | expected {exp!r} | {question}")
        if not ok:
            print("      answer:", res["answer"][:200].replace("\n", " "))
        time.sleep(12)

    avg = statistics.mean(times) if times else float("nan")
    print(f"\n{passed}/{len(TESTS)} passed | average response time {avg:.1f}s")


if __name__ == "__main__":
    main()