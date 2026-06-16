# **projectpicker - Shool Project Allocation Tool**

A lightweight command‑line tool for managing school project assignments.  
It loads CSV files for projects and students, detects duplicates, and performs automatic matching based on student choices and project constraints.  
Output can be exported to ODS for easy review by teachers.

---

## **✨ Features**

- **Find duplicate students**  
  Detects students appearing multiple times across CSV files.

- **Match students to projects**  
  Uses project limits, student choices, exemptions, and class levels.

- **ODS export**  
  Generates a clean multi‑sheet ODS file with styled headers.

- **Teacher parsing**  
  Supports semicolon‑separated teacher names.

- **Colored terminal output**  
  Helps visualize student groups (all, responded, exempted).

---

## Example Input Files**

In all CSV files, columns can appear in arbitrary order.

### **projects.csv**

```
project_number;project_name;teachers;min_students;max_students;allowed_levels
101;Robotics;Müller;2;5;9,10
102;Art Workshop;Schmidt;3;6;8,9,10
103;Chemistry Lab;Kaya;2;4;10
```

## Student input



### **students_all.csv**


```
firstname;lastname;class_level;track;project_choices
Anna;Becker;9;A;101,102,103
Lukas;Meyer;10;B;103,101,102
Sara;Klein;8;A;102,101
```

### **students_responded.csv**

```
firstname;lastname;class_level;track;project_choices
Anna;Becker;9;A;101,102,103
Lukas;Meyer;10;B;103,101,102
```

### **students_exempted.csv**

```
firstname;lastname;class_level;track
Sara;Klein;8;A
```

---

## Installation

Inside the project folder:

```bash
pip install .
```

Editable mode (recommended during development):

```bash
pip install -e .
```

---

## **🧭 Command Line Usage**

The tool provides two commands:

### **1. Find duplicates**

```bash
projectpicker find-duplicates --students-all students_all.csv
```

### **2. Match students to projects**

Minimal:

```bash
projectpicker match \
    --projects projects.csv \
    --students-all students_all.csv \
    --students-responded students_responded.csv
```

With exempted students:

```bash
projectpicker match \
    --projects projects.csv \
    --students-all students_all.csv \
    --students-responded students_responded.csv \
    --students-exempted students_exempted.csv
```

---

## Output

- Terminal summary of loaded data  
- Duplicate detection report  
- Matching results  
- ODS export with:
  - One sheet per project  
  - Summary sheet  
  - Orange bold headers  
  - Clean formatting  

---

## Licensing

Please see the file [LICENSE.md](./LICENSE.md) for further information about how the content is licensed.

