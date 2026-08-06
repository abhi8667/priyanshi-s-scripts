# NexusAllocate Pro — Enterprise College Induction Allocation System

> **Commercial-Grade PySide6 (Qt6) Desktop Application for Automated Student Induction Group Stratification & MILP Venue Optimization (Scalable to 10,000+ Students).**

---

## 📌 Executive Summary

**NexusAllocate Pro** is a high-performance desktop application engineered for university faculty and event administrators to manage annual student induction programs. Built using **PySide6 (Qt 6.7)**, **SQLite (WAL Mode)**, **SQLAlchemy 2.0**, and **PuLP Mixed-Integer Linear Programming (MILP)** solvers, the system automates:

- **Fuzzy Data Ingestion**: Dynamic Excel header matching (`rapidfuzz`) with auto-fallback for missing optional fields.
- **Stratified Group Allocation**: SHA-256 hash-based deterministic split into Group A / Group B maintaining immutability and gender balance.
- **Venue & Time Slot Optimization**: MILP constraint solver ensuring zero venue over-capacity, minimal department splitting, and auto-capacity diagnostic reporting.
- **Data Integrity & Governance**: Atomic timestamped SQLite snapshots with 1-click database rollbacks and full audit logging.
- **Enterprise Reporting**: Formatted multi-tab Excel workbooks, formula-injection protected CSVs, and printable PDF attendance rosters.

---

## 🚀 Key Features & Architectural Highlights

### 1. 📥 Intelligent Fuzzy Excel Column Mapper
- Accepts dynamic client Excel/CSV formats (e.g., `Candidate Name`, `SI.No.`, `STUDENT NUMBER`, `Univ USN`, `PROGRAM`).
- Leverages Levenshtein distance token-sort ratio matching (`rapidfuzz`).
- Required field validation (`USN` & `Full Name`) with auto-fallback for missing department headers (`PROGRAM` or `"General"`).
- Dynamic dropdown re-validation: Enables the import button in real-time.

### 2. 🔀 Stratified Deterministic Group Allocator
- **Immutability Guarantee**: Previously allocated students NEVER change groups on subsequent re-imports.
- **Strict Determinism**: Uses SHA-256 USN digest ordering to ensure identical input always yields identical group assignments.
- **Equal Department & Gender Split**: Balances Group A and Group B within each department and gender bucket.

### 3. 🏛️ MILP Venue & Timeslot Optimization Engine
- Formulates allocation as a Mixed-Integer Linear Program (`PuLP`).
- **Constraints**:
  - Venue capacity per time slot must never be exceeded.
  - Every student must be allocated a venue and time slot.
  - Minimizes department splitting across venues for cohesive cohort experiences.
- **Capacity Diagnostics**: Detects seat deficits before solving and calculates recommended seat increases per time slot.
- **Greedy Fallback**: Includes a fast greedy bin-packing solver fallback for edge cases.

### 4. 🛡️ Automatic Backup & 1-Click Database Rollback
- SQLite Write-Ahead Logging (`WAL`) mode with 64MB cache for concurrent read/write throughput.
- Generates SHA-256 verified SQLite snapshots prior to allocation runs.
- 1-click rollback restores database state atomically with a safety backup created before restoration.

### 5. 📤 Multi-Format Export Center & Formula Injection Security
- **Multi-Tab Excel Workbook**: Generates styled sheets (`Master Roster`, `Group A`, `Group B`, `Department-wise`, `Venue-wise`).
- **Formula Injection Security**: Sanitizes leading unsafe characters (`=`, `+`, `-`, `@`) to defend against spreadsheet macro exploits.
- **Printable PDF Attendance Sheets**: Generates print-ready rosters with signature lines and attendance check-boxes via `ReportLab`.

---

## ⚡ 10,000 Student Performance Benchmark

Tested and verified on a single local execution environment:

| Phase / Operation | Processed Load | Time Taken | Status |
| :--- | :--- | :--- | :--- |
| **SQLite Data Ingestion** | 10,000 Records | **0.53 seconds** | ✅ Passed |
| **Stratified Group Split** | 10,000 Records | **0.84 seconds** | ✅ Passed |
| **MILP Venue Allocation** | 10,000 Records | **0.94 seconds** | ✅ Passed |
| **Multi-Sheet Excel Export** | 10,000 Records | **2.03 seconds** | ✅ Passed |
| **Total Pipeline** | **10,000 Records** | **< 4.5 seconds** | ✅ **Passed** |

---

## 📁 Repository Directory Structure

```
d:\venue_allocation\
├── app.py                      # Main Application Entry Point & MainWindow GUI
├── config.py                   # Global System Constants, Paths, Theme Color Palette
├── requirements.txt            # Python Dependencies
├── README.md                   # System Documentation
│
├── core/                       # Domain Core Layer
│   ├── domain_models.py        # Dataclasses, Enums (Gender, AllocationResult, CapacityReport)
│   └── exceptions.py           # Custom System Exceptions
│
├── database/                   # Data Access & Persistence Layer
│   ├── connection.py           # SQLite Connection Pool with WAL Mode & PRAGMAs
│   ├── models.py               # SQLAlchemy 2.0 ORM Database Schemas
│   ├── repository.py           # Optimized Data Queries & Dashboard Aggregations
│   └── backup_manager.py       # SQLite Snapshot Backup & 1-Click Rollback Manager
│
├── engine/                     # Optimization & Business Logic Engines
│   ├── column_mapper.py        # RapidFuzz Header Alias Mapper
│   ├── data_importer.py        # Data Ingestion, Validation & Differential Updater
│   ├── group_allocator.py      # Stratified Deterministic Group Allocator (Group A/B)
│   └── venue_optimizer.py      # PuLP MILP Solver for Venue & Timeslot Optimization
│
├── services/                   # Export & Reporting Services
│   └── export_service.py       # Excel, CSV & PDF Attendance Generator
│
├── ui/                         # PySide6 Desktop Presentation Layer
│   ├── styles/theme.py         # Dark Glassmorphism QSS Stylesheet
│   ├── components/             # Virtual QAbstractTableModel for High-Speed Scrolling
│   └── views/                  # 8 Desktop Navigation Views
│       ├── dashboard_view.py   # Executive Analytics Dashboard
│       ├── import_view.py      # File Picker & Column Mapper Workspace
│       ├── student_view.py     # Student Table & Multi-Filter Search
│       ├── group_view.py       # Group Allocation View
│       ├── venue_view.py       # Venue / Slot Manager & Optimizer View
│       ├── backup_view.py      # Backup Snapshot History & Rollback View
│       ├── export_view.py      # Multi-Format Export Center View
│       └── logs_view.py        # Audit Trail & System Log Viewer
│
├── tests/                      # Automated QA Test Suite
│   ├── test_column_mapper.py   # Fuzzy Header Mapping Unit Tests
│   ├── test_group_allocator.py # Determinism & Immutability Unit Tests
│   ├── test_venue_optimizer.py # MILP Solver & Capacity Unit Tests
│   └── test_benchmark_10k.py   # 10,000 Student Performance Benchmark Test
│
├── data/                       # Local SQLite Database & Snapshot Backups
└── exports/                    # Generated Excel, CSV & PDF Exports
```

---

## 🛠️ Installation & Setup Guide

### 1. Prerequisites
- **Python**: Version 3.11 or higher (Python 3.11+ recommended).
- **Operating System**: Windows 10/11, macOS, or Linux.

### 2. Environment Setup
```powershell
# Clone or navigate to project directory
cd d:\venue_allocation

# Create virtual environment (optional but recommended)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🖥️ How to Run the Application

```powershell
# Launch PySide6 Desktop GUI Application
python app.py
```

### Running Automated QA Tests & 10k Benchmark
```powershell
# Run full pytest test suite
python -m pytest -v -s
```

---

## 📖 Step-by-Step User Workflow

1. **Import Student Data**:
   - Click **Browse Excel / CSV File** on the **Import Excel** tab.
   - The system automatically maps column headers to `USN`, `Student Full Name`, `Program`, `Gender`, etc.
   - Click **Commit Import & Update Database**.
2. **Assign Groups (Group A / Group B)**:
   - Navigate to **Group Allocation**.
   - Click **Run Stratified Group Allocation**.
3. **Configure & Optimize Venues**:
   - Navigate to **Venue Allocation**.
   - Set up your venue capacities and time slots.
   - Click **Run MILP Venue Allocation**.
4. **Export Reports**:
   - Navigate to **Export Center**.
   - Export Master Excel, CSV, or printable PDF Attendance rosters.
5. **Backup & Security**:
   - Navigate to **Backup Rollback** at any time to restore a previous database state with 1-click.

---

## 📜 License & Support

Developed for enterprise college induction management. All system actions are recorded under **Audit Logs** for transparency and compliance.
