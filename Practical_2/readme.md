# ITUC301 - Data Engineering
## Practical 2: Data Sources and Data Generation

### Objective
Generate data from multiple sources, perform data profiling, identify data quality issues, and prepare clean data for ingestion.

---

## Technologies Used

- Python 3.x
- Pandas
- Faker
- Requests
- SQLite
- VS Code

---

## Setup

### Install Required Libraries

```bash
pip install pandas faker requests
```

### Verify Installation

```bash
pip list
```

---

## Project Structure

```text
Practical_2/
│
├── generate_data.py
├── database.py
├── read_database.py
├── api_data.py
├── profile.py
├── validate_email.py
├── duplicate.py
├── clean_data.py
│
├── customers.csv
├── clean_customers.csv
├── customers.db
│
└── README.md
```

---

## Workflow

```text
Generate Data
      ↓
CSV File
      ↓
SQLite Database
      ↓
API Data
      ↓
Data Profiling
      ↓
Data Validation
      ↓
Duplicate Detection
      ↓
Data Cleaning
      ↓
Clean Dataset
```

---

## Practical Steps

### 1. Generate Synthetic Data

**File:** `generate_data.py`

Creates fake customer records using Faker and stores them in `customers.csv`.

Run:

```bash
python generate_data.py
```

Expected Output:

```text
customers.csv created successfully
```

---

### 2. Store Data in SQLite

**File:** `database.py`

Loads CSV data into SQLite database.

Run:

```bash
python database.py
```

Expected Output:

```text
Database created successfully
```

Generated File:

```text
customers.db
```

---

### 3. Read Data from Database

**File:** `read_database.py`

Fetches records from SQLite using SQL queries.

Run:

```bash
python read_database.py
```

---

### 4. Read Data from API

**File:** `api_data.py`

Fetches JSON data from a public REST API.

Run:

```bash
python api_data.py
```

Example API:

```text
https://jsonplaceholder.typicode.com/users
```

---

### 5. Data Profiling

**File:** `profile.py`

Used to analyze dataset structure and quality.

Checks:

- Column information
- Data types
- Summary statistics
- Missing values

Run:

```bash
python profile.py
```

---

### 6. Validate Email Addresses

**File:** `validate_email.py`

Detects invalid email formats.

Run:

```bash
python validate_email.py
```

Example:

```text
Valid  : user@gmail.com
Invalid: usergmail.com
```

---

### 7. Detect Duplicate Records

**File:** `duplicate.py`

Finds duplicate rows in the dataset.

Run:

```bash
python duplicate.py
```

Expected Output:

```text
No duplicate records found.
```

or

```text
Total Duplicate Records: X
```

---

### 8. Clean Dataset

**File:** `clean_data.py`

Removes records containing missing values and exports a clean dataset.

Run:

```bash
python clean_data.py
```

Generated File:

```text
clean_customers.csv
```

---

## Data Quality Checks Performed

- Missing Value Detection
- Email Validation
- Duplicate Record Detection
- Data Cleaning

---

## Learning Outcomes

After completing this practical, I learned:

- Data generation using Faker
- Working with CSV files
- SQLite database operations
- REST API integration
- Data profiling using Pandas
- Data validation techniques
- Duplicate detection
- Dataset cleaning and preprocessing

---

## Commands Summary

```bash
python generate_data.py
python database.py
python read_database.py
python api_data.py
python profile.py
python validate_email.py
python duplicate.py
python clean_data.py
```

---

## Conclusion

This practical demonstrates how to generate, collect, validate, profile, and clean data from multiple sources. These are fundamental tasks in the Data Engineering lifecycle and serve as the foundation for building reliable data pipelines.