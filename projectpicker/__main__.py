#!/usr/bin/env python3
"""
ProjectPicker — load project and student definitions from CSV files.

xaratustrah@github

"""

import csv
import sys
import json
import argparse
from typing import List
from loguru import logger
from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableRow, TableCell
from odf.text import P
from odf.style import Style, TableCellProperties, TextProperties

from .__version__ import __version__


# ---------------------------------------------------------------------------
# Project Model
# ---------------------------------------------------------------------------

class Project:
    """Represents a single school project."""

    def __init__(
        self,
        project_number: int,
        project_name: str,
        allowed_class_levels: List[int],
        max_students: int,
        min_students: int,
        description: str,
        teachers: list[str] | None = None,
    ):
        self.project_number = project_number
        self.project_name = project_name
        self.allowed_class_levels = allowed_class_levels
        self.max_students = max_students
        self.min_students = min_students
        self.description = description
        self.teachers = teachers if teachers else []
        self.assigned_students: list[Student] = []
        self.is_under_min: bool = False

    def __repr__(self) -> str:
        return (
            f"Project(number={self.project_number}, "
            f"name={self.project_name!r}, "
            f"levels={self.allowed_class_levels}, "
            f"min={self.min_students}, max={self.max_students}, "
            f"teachers={self.teachers})"
        )

    def __str__(self) -> str:
        levels = ", ".join(str(l) for l in self.allowed_class_levels)
        teacher_list = ", ".join(self.teachers) if self.teachers else "(none)"
        return (
            f"Project {self.project_number}: {self.project_name}\n"
            f"  Allowed class levels : {levels}\n"
            f"  Min students         : {self.min_students}\n"
            f"  Max students         : {self.max_students}\n"
            f"  Teachers             : {teacher_list}\n"
            f"  Description:\n"
            f"    {self.description}\n"
        )


class ProjectDataError(Exception):
    """Raised when required project fields are missing or invalid."""
    pass


# ---------------------------------------------------------------------------
# Project related functions
# ---------------------------------------------------------------------------

def colorize(text: str, color: str) -> str:
    colors = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "reset": "\033[0m",
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"

def load_projects_from_csv(path: str) -> List[Project]:
    """Load projects from a CSV file and return a list of Project objects."""
    projects: List[Project] = []

    logger.info(f"Loading project CSV: {path}")

    try:
        with open(path, mode="r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)

            # Skip first line (e.g. meta info)
            next(reader, None)

            # Header line
            headers = next(reader, None)
            if headers is None:
                raise ProjectDataError("CSV file has no header row.")

            # Identify class-level columns
            level_columns = []
            for idx, name in enumerate(headers):
                if name.strip().isdigit():
                    level_columns.append((idx, int(name.strip())))

            # Required fields
            try:
                idx_number = headers.index("Projektnummer")
                idx_name = headers.index("Projektname")
                idx_max = headers.index("Max Anzahl")
                idx_min = headers.index("Min Anzahl")
                idx_desc = headers.index("Beschreibung")
            except ValueError as e:
                raise ProjectDataError(f"Missing required header: {e}")

            # Optional teacher column
            idx_teachers = headers.index("Lehrer") if "Lehrer" in headers else None

            # Process rows
            for line_number, row in enumerate(reader, start=3):
                if not any(cell.strip() for cell in row):
                    continue

                def require(idx, label):
                    if idx >= len(row) or not row[idx].strip():
                        raise ProjectDataError(
                            f"Missing required field '{label}' in line {line_number}."
                        )
                    return row[idx].strip()

                project_number = int(require(idx_number, "Projektnummer"))
                project_name = require(idx_name, "Projektname")

                allowed_class_levels = [
                    level for col_idx, level in level_columns
                    if col_idx < len(row) and row[col_idx].strip() == "1"
                ]

                if not allowed_class_levels:
                    raise ProjectDataError(
                        f"Project {project_number} has no allowed class levels (line {line_number})."
                    )

                max_students = int(require(idx_max, "Max Anzahl"))
                min_students = int(row[idx_min]) if row[idx_min].strip() else 0
                description = row[idx_desc].strip() if row[idx_desc].strip() else ""

                # Teacher parsing (optional)
                if idx_teachers is not None and idx_teachers < len(row):
                    teacher_raw = row[idx_teachers].strip()
                    teachers = [t.strip() for t in teacher_raw.split(";")] if teacher_raw else []
                else:
                    teachers = []

                project = Project(
                    project_number=project_number,
                    project_name=project_name,
                    allowed_class_levels=allowed_class_levels,
                    max_students=max_students,
                    min_students=min_students,
                    description=description,
                    teachers=teachers,
                )

                projects.append(project)

        logger.success(f"Loaded {len(projects)} projects.")

    except FileNotFoundError:
        logger.error(f"File not found: {path}")
        raise
    except ProjectDataError as e:
        logger.error(f"Data error: {e}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error while loading project CSV: {e}")
        raise

    return projects

def print_project_status(projects):
    for p in projects:
        if p.is_under_min:
            print(colorize(f"⚠️  Project {p.project_number} under minimum ({len(p.assigned_students)}/{p.min_students})", "yellow"))
        else:
            print(colorize(f"✔️  Project {p.project_number} OK ({len(p.assigned_students)}/{p.min_students})", "green"))


def pretty_print_projects(projects: list[Project], show_students: bool = True):
    for p in projects:
        count = len(p.assigned_students)

        # Determine color based on health
        if getattr(p, "is_under_min", False):
            color = "yellow"
            status = "UNDER MIN"
        elif count > p.max_students:
            color = "red"
            status = "OVER MAX"
        else:
            color = "green"
            status = "OK"

        header = (
            f"Projekt {p.project_number}: {p.project_name} "
            f"[{count}/{p.min_students}-{p.max_students}] "
            f"Status: {status}"
        )

        print(colorize(header, color))

        if show_students:
            for s in p.assigned_students:
                print("   - " + colorize(f"{s.lastname}, {s.firstname}", color))

        print()  # spacing

from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableRow, TableCell
from odf.text import P
from odf.style import Style, TableCellProperties, TextProperties


def _add_row(table, values, header=False):
    """Helper: add a row with optional header styling."""
    tr = TableRow()
    for v in values:
        tc = TableCell()
        if header:
            tc.setAttribute("stylename", "HeaderStyle")
        tc.addElement(P(text=str(v)))
        tr.addElement(tc)
    table.addElement(tr)


def export_projects_to_ods(projects, filename="projects.ods"):
    doc = OpenDocumentSpreadsheet()

    # ---------------------------------------------------------
    # Styles: orange background + bold text for header cells
    # ---------------------------------------------------------
    header_style = Style(name="HeaderStyle", family="table-cell")
    header_style.addElement(TableCellProperties(backgroundcolor="#FFA500"))
    header_style.addElement(TextProperties(fontweight="bold"))
    doc.styles.addElement(header_style)

    # ---------------------------------------------------------
    # Sheet 0: Summary
    # ---------------------------------------------------------
    summary = Table(name="Summary")
    doc.spreadsheet.addElement(summary)

    _add_row(summary, [
        "Project Number", "Project Name", "Teachers",
        "Min", "Max", "Assigned", "Under Min", "Over Max"
    ], header=True)

    for p in projects:
        teachers = "; ".join(p.teachers)
        _add_row(summary, [
            p.project_number,
            p.project_name,
            teachers,
            p.min_students,
            p.max_students,
            len(p.assigned_students),
            getattr(p, "is_under_min", False),
            len(p.assigned_students) > p.max_students
        ])

    # ---------------------------------------------------------
    # One sheet per project
    # ---------------------------------------------------------
    for p in projects:
        sheet_name = f"{p.project_number}_{p.project_name[:20]}"
        table = Table(name=sheet_name)
        doc.spreadsheet.addElement(table)

        # Metadata block
        _add_row(table, ["Project Number", p.project_number])
        _add_row(table, ["Project Name", p.project_name])
        _add_row(table, ["Teachers", "; ".join(p.teachers)])
        _add_row(table, ["Allowed Levels", ", ".join(map(str, p.allowed_class_levels))])
        _add_row(table, ["Min Students", p.min_students])
        _add_row(table, ["Max Students", p.max_students])
        _add_row(table, ["Assigned Count", len(p.assigned_students)])
        _add_row(table, ["Under Min", getattr(p, "is_under_min", False)])
        _add_row(table, ["", ""])  # spacer row

        # Student table header
        _add_row(table, [
            "Firstname", "Lastname", "Class Level",
            "Track", "Responded", "Choice Rank", "Comment"
        ], header=True)

        # Student rows
        for s in p.assigned_students:
            choice_rank = "-"
            if s.assigned_project_number in s.project_choices:
                idx = s.project_choices.index(s.assigned_project_number)
                choice_rank = idx + 1

            _add_row(table, [
                s.firstname,
                s.lastname,
                s.class_level,
                s.track,
                s.responded,
                choice_rank,
                s.comments or ""
            ])

    # ---------------------------------------------------------
    # Save ODS file
    # ---------------------------------------------------------
    doc.save(filename)


# ---------------------------------------------------------------------------
# Student Model
# ---------------------------------------------------------------------------

class Student:
    """Represents a single student participating in ProjectPicker."""

    def __init__(
        self,
        lastname: str,
        firstname: str,
        class_level: str | int,
        comments: str = "",
        responded: bool = False,
        can_be_assigned: bool = True,
        has_been_assigned: bool = False,
        assigned_project_number: int | None = None,
        project_choices: list[int] | None = None,
    ):
        # --- NEW: normalize class_level + extract track ---
        raw = str(class_level).strip().lower().replace(" ", "")
        digits = "".join(ch for ch in raw if ch.isdigit())
        letters = "".join(ch for ch in raw if ch.isalpha())

        self.class_level = int(digits) if digits else None
        self.track = letters if letters else None  # always lowercase

        # --- existing fields ---
        self.lastname = lastname
        self.firstname = firstname
        self.comments = comments
        self.responded = responded
        self.can_be_assigned = can_be_assigned
        self.has_been_assigned = has_been_assigned
        self.assigned_project_number = assigned_project_number
        self.project_choices = project_choices if project_choices else []

    def __repr__(self) -> str:
        return (
            f"Student(lastname={self.lastname!r}, "
            f"firstname={self.firstname!r}, "
            f"class_level={self.class_level!r}, "
            f"track={self.track!r}, "
            f"responded={self.responded!r}, "
            f"assigned_project_number={self.assigned_project_number!r}, "
            f"project_choices={self.project_choices!r})"
        )

    def __str__(self) -> str:
        klasse = f"{self.class_level}{self.track or ''}"
        assigned = self.assigned_project_number if self.assigned_project_number is not None else "(none)"
        choices = ", ".join(str(p) for p in self.project_choices) if self.project_choices else "(none)"
        return (
            f"{self.firstname} {self.lastname} ({klasse})\n"
            f"  Responded           : {'yes' if self.responded else 'no'}\n"
            f"  Can be assigned     : {'yes' if self.can_be_assigned else 'no'}\n"
            f"  Has been assigned   : {'yes' if self.has_been_assigned else 'no'}\n"
            f"  Assigned project    : {assigned}\n"
            f"  Project choices     : {choices}\n"
            f"  Comments            : {self.comments or '(none)'}"
        )
    
    def to_dict(self):
        return {
            "lastname": self.lastname,
            "firstname": self.firstname,
            "class_level": self.class_level,
            "track": self.track,
            "comments": self.comments,
            "responded": self.responded,
            "can_be_assigned": self.can_be_assigned,
            "has_been_assigned": self.has_been_assigned,
            "assigned_project_number": self.assigned_project_number,
            "project_choices": self.project_choices,
        }

    @classmethod
    def from_dict(cls, data):
        # reconstruct original grade string for __init__
        grade_str = str(data["class_level"])
        if data.get("track"):
            grade_str += data["track"]

        return cls(
            lastname=data["lastname"],
            firstname=data["firstname"],
            class_level=grade_str,
            comments=data.get("comments", ""),
            responded=data.get("responded", False),
            can_be_assigned=data.get("can_be_assigned", True),
            has_been_assigned=data.get("has_been_assigned", False),
            assigned_project_number=data.get("assigned_project_number"),
            project_choices=data.get("project_choices", []),
        )


class StudentDataError(Exception):
    """Raised when required student fields are missing or invalid."""
    pass


# ---------------------------------------------------------------------------
# Student related functions
# ---------------------------------------------------------------------------

def find_duplicate_students(students: list[Student]) -> list[Student]:
    seen = {}
    duplicates = []

    for s in students:
        key = (s.firstname.strip().lower(), s.lastname.strip().lower())

        if key in seen:
            duplicates.append(s)
        else:
            seen[key] = s

    return duplicates


def load_students_from_csv(path: str) -> List[Student]:
    """Load students from a CSV file and return a list of Student objects."""
    students: List[Student] = []

    logger.info(f"Loading student CSV: {path}")

    try:
        with open(path, mode="r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)

            headers = next(reader, None)
            if headers is None:
                raise StudentDataError("CSV file has no header row.")

            # Required fields
            try:
                idx_lastname = headers.index("Nachname")
                idx_firstname = headers.index("Vorname")
                idx_class = headers.index("Klasse")
            except ValueError as e:
                raise StudentDataError(f"Missing required header: {e}")

            # Optional fields
            idx_projA = headers.index("Projekt A") if "Projekt A" in headers else None
            idx_projB = headers.index("Projekt B") if "Projekt B" in headers else None
            idx_projC = headers.index("Projekt C") if "Projekt C" in headers else None
            idx_comment = headers.index("Kommentar") if "Kommentar" in headers else None

            # Process rows
            for line_number, row in enumerate(reader, start=2):
                if not any(cell.strip() for cell in row):
                    continue

                def require(idx, label):
                    if idx is None or idx >= len(row) or not row[idx].strip():
                        raise StudentDataError(
                            f"Missing required field '{label}' in line {line_number}."
                        )
                    return row[idx].strip()

                lastname = require(idx_lastname, "Nachname")
                firstname = require(idx_firstname, "Vorname")

                # --- extract digits + track ---
                class_raw = require(idx_class, "Klasse")
                cleaned = class_raw.strip().lower().replace(" ", "")
                digits = "".join(ch for ch in cleaned if ch.isdigit())
                letters = "".join(ch for ch in cleaned if ch.isalpha())

                if not digits:
                    raise StudentDataError(
                        f"Invalid class format '{class_raw}' in line {line_number}."
                    )

                class_level = int(digits)
                track = letters if letters else None

                # Optional project choices
                project_choices: list[int] = []
                for idx in (idx_projA, idx_projB, idx_projC):
                    if idx is not None and idx < len(row) and row[idx].strip():
                        try:
                            project_choices.append(int(row[idx].strip()))
                        except ValueError:
                            raise StudentDataError(
                                f"Invalid project number in line {line_number}."
                            )

                responded = len(project_choices) > 0

                comments = (
                    row[idx_comment].strip()
                    if idx_comment is not None and row[idx_comment].strip()
                    else ""
                )

                # --- UPDATED: pass track into Student ---
                student = Student(
                    lastname=lastname,
                    firstname=firstname,
                    class_level=f"{class_level}{track or ''}",
                    comments=comments,
                    responded=responded,
                    project_choices=project_choices,
                )

                students.append(student)

        logger.success(f"Loaded {len(students)} students.")

    except FileNotFoundError:
        logger.error(f"File not found: {path}")
        raise
    except StudentDataError as e:
        logger.error(f"Data error: {e}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error while loading student CSV: {e}")
        raise

    return students

def write_students_to_csv(students: list[Student], path: str) -> None:
    """Write student assignment results to a CSV file."""

    headers = [
        "Nachname",
        "Vorname",
        "Klasse",
        "Zug",
        "Zugewiesenes Projekt",
        "Kommentar",
    ]

    with open(path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for s in students:
            writer.writerow([
                s.lastname,
                s.firstname,
                s.class_level,                    # numeric grade
                s.track if s.track else "",       # letter track (lowercase)
                s.assigned_project_number or "",  # empty if None
                s.comments or "",                 # optional comment
            ])

def save_students_to_json(students: list[Student], path: str) -> None:
    """Save a list of Student objects to a JSON file."""
    data = [s.to_dict() for s in students]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_students_from_json(path: str) -> list[Student]:
    """Load students from a JSON file and return Student objects."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [Student.from_dict(entry) for entry in data]

def diff_student_lists(list_a: list[Student], list_b: list[Student]):
    """
    Compare two student lists and return:
    - students only in A
    - students only in B

    Identity is based on: lastname, firstname, class_level, track.
    """

    def key(s: Student):
        return (
            s.lastname.lower(),
            s.firstname.lower(),
            s.class_level,
            s.track,
        )

    map_a = {key(s): s for s in list_a}
    map_b = {key(s): s for s in list_b}

    only_in_a = [map_a[k] for k in map_a.keys() - map_b.keys()]
    only_in_b = [map_b[k] for k in map_b.keys() - map_a.keys()]

    return only_in_a, only_in_b

def pretty_print_student_list(students, title: str = "Studentenliste", color="cyan"):
    # Normalize input
    if isinstance(students, Student):
        students = [students]
    elif students is None:
        students = []

    print(colorize(f"\n=== {title} ({len(students)}) ===", color))

    for s in students:
        track = s.track or ""
        proj = s.assigned_project_number or "-"
        comment = s.comments or "-"

        line = (
            f"{s.lastname}, {s.firstname} "
            f"(Klasse {s.class_level}{track}) "
            f"Projekt: {proj} "
            f"Kommentar: {comment}"
        )

        print(colorize(line, color))

def add_student_lists(base_list: list[Student], new_students: list[Student]):
    """
    Adds students from new_students into base_list,
    avoiding duplicates (firstname + lastname).
    Returns (merged_list, added_students).
    """
    merged = list(base_list)  # copy
    added = []

    # Build a set of existing name keys
    existing_keys = {
        (s.firstname.strip().lower(), s.lastname.strip().lower())
        for s in base_list
    }

    for s in new_students:
        key = (s.firstname.strip().lower(), s.lastname.strip().lower())

        if key not in existing_keys:
            merged.append(s)
            added.append(s)
            existing_keys.add(key)

    return merged, added

# ---------------------------------------------------------------------------
# Matching Engine
# ---------------------------------------------------------------------------

def match_students_to_projects(
    students: list[Student],
    projects: list[Project],
):
    import random

    project_by_number = {p.project_number: p for p in projects}

    # Reset state
    for p in projects:
        p.assigned_students = []
    for s in students:
        s.assigned_project_number = None
        s.has_been_assigned = False

    # Split responders vs non-responders
    responders = [s for s in students if s.responded and s.can_be_assigned]
    non_responders = [s for s in students if not s.responded and s.can_be_assigned]

    # Helper: can student join project?
    def can_join(project: Project, student: Student) -> bool:
        if student.class_level not in project.allowed_class_levels:
            return False
        if len(project.assigned_students) >= project.max_students:
            return False
        return True

    # Helper: assign student
    def assign(student: Student, project: Project) -> bool:
        if not can_join(project, student):
            return False
        project.assigned_students.append(student)
        student.assigned_project_number = project.project_number
        student.has_been_assigned = True
        return True

    # Try A/B/C choices
    def try_choices(student: Student):
        for proj_num in student.project_choices:
            p = project_by_number.get(proj_num)
            if p and assign(student, p):
                return True
        return False

    # Pass 1–3: responders get priority
    for s in responders:
        try_choices(s)

    # Non-responders: random fallback
    random.shuffle(non_responders)
    for s in non_responders:
        for p in projects:
            if assign(s, p):
                break

    # Final attempt: any leftover responders
    leftovers = [s for s in students if not s.has_been_assigned and s.can_be_assigned]
    for s in leftovers:
        for p in projects:
            if assign(s, p):
                break

    # Final leftovers (still unassigned)
    unassigned = [s for s in students if not s.has_been_assigned and s.can_be_assigned]

    # After all assignments:
    for p in projects:
        p.is_under_min = len(p.assigned_students) < p.min_students

    return projects, unassigned

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="ProjectPicker CSV processor.")

    parser.add_argument(
        "--projects",
        required=True,
        help="CSV file containing project definitions."
    )

    parser.add_argument(
        "--students-all",
        help="CSV file with all students."
    )

    parser.add_argument(
        "--students-responded",
        help="CSV file with students who submitted preferences."
    )

    parser.add_argument(
        "--students-exempted",
        help="CSV file with students who cannot participate."
    )

    parser.add_argument(
        "--output",
        default="output.csv",
        help="Output CSV file (default: output.csv)."
    )

    return parser.parse_args()



def parse_args():
    parser = argparse.ArgumentParser(description="Project allocation tool")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # -----------------------------
    # find-duplicates command
    # -----------------------------
    dup = subparsers.add_parser("find-duplicates", help="Find duplicate students")
    dup.add_argument("--students-responded", required=True, help="CSV of responded students")

    # -----------------------------
    # match command
    # -----------------------------
    match = subparsers.add_parser("match", help="Run project matching")
    match.add_argument("--projects", required=True, help="CSV of projects")
    match.add_argument("--students-all", required=True, help="CSV of all students")
    match.add_argument("--students-responded", required=True, help="CSV of responded students")
    match.add_argument("--students-exempted", required=False, help="CSV of exempted students")

    return parser.parse_args()

def main():
    
    args = parse_args()

    if args.command == "find-duplicates":
        students_responded_list = load_students_from_csv(args.students_responded)
        pretty_print_student_list(students_responded_list, 'Geantwortet', 'blue')

        logger.info('Duplikate')
        pretty_print_student_list(find_duplicate_students(students_responded_list), 'Duplicates')
        # create a duplicate free list
        #students_responded_list_duplicate_free, _ = diff_student_lists(students_responded_list, find_duplicate_students(students_responded_list))
        #pretty_print_student_list(students_responded_list_duplicate_free)
        #write_students_to_csv(students_responded_list_duplicate_free, 'students_responded_list_duplicate_free.csv')
        
        sys.exit(0)


    elif args.command == "match":
        projects_list = load_projects_from_csv(args.projects)
        pretty_print_projects(projects_list)

        students_all_list = load_students_from_csv(args.students_all)
        pretty_print_student_list(students_all_list, 'Alle Schüler', 'yellow')

        students_responded_list = load_students_from_csv(args.students_responded)
        pretty_print_student_list(students_responded_list, 'Geantwortet', 'blue')

        if args.students_exempted:
            students_exempted_list = load_students_from_csv(args.students_exempted)
            pretty_print_student_list(students_exempted_list, 'Befreit', 'green')
            for p in students_exempted_list:
                p.can_be_assigned = False

        logger.info('Finding out total non-responders')
        not_responded_list, _ = diff_student_lists(students_all_list, students_responded_list)
        for p in not_responded_list:
            p.responded = False
        pretty_print_student_list(not_responded_list, 'nicht geantwortet und befreit', 'red')
        
        logger.info('Separating exempted students from true non-responders')
        not_responded_list_final, _ = diff_student_lists(not_responded_list, students_exempted_list)
        pretty_print_student_list(not_responded_list_final, 'nicht geantwortet', 'red')
        write_students_to_csv(not_responded_list_final, './nicht_geantwortet_final.csv')
        
        logger.info('Determining the final processing list.')
        merge, _ = add_student_lists(students_responded_list, not_responded_list_final)
        pretty_print_student_list(merge)
        
        p, s = match_students_to_projects(merge, projects_list)
        pretty_print_projects(p, show_students= True)
        pretty_print_student_list(s, 'nicht gepasst')
        write_students_to_csv(s, 'nicht_zugewiesen.csv')
            
        logger.info('Creating an ODS file.')
        export_projects_to_ods(p, 'report.ods')
        
        sys.exit(0)

if __name__ == "__main__":
    main()


#----------------------------------------------------------------------
## trash can


# some tests
# save_students_to_json(students_all_list, './blah.json')
# for s in load_students_from_json('./blah.json'):
#     print(s)
# write_students_to_csv(students_all_list, './blooh.csv')



