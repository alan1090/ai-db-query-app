# TechCorp HR Database Schema

## Overview

This database models a mid-size technology company's HR system with **8 tables** and **1,300+ records**. It covers employee management, compensation tracking, project work, performance evaluations, and professional development.

---

## Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────┐       ┌───────────────────┐
│  departments │       │  job_titles  │       │    projects       │
│──────────────│       │──────────────│       │───────────────────│
│ dept_id (PK) │──┐    │ title_id (PK)│──┐    │ project_id (PK)  │──┐
│ dept_name    │  │    │ title        │  │    │ project_name     │  │
│ location     │  │    │ dept_id (FK) │──┘    │ dept_id (FK)     │──┘
│ annual_budget│  │    │ level        │       │ budget           │
│ division     │  │    │ min_salary   │       │ start_date       │
│ established  │  │    │ max_salary   │       │ end_date         │
└──────────────┘  │    └──────────────┘       │ status           │
                  │                           │ priority         │
                  │                           └───────────────────┘
                  │                                    │
                  ▼                                    ▼
         ┌──────────────────┐              ┌────────────────────┐
         │    employees     │              │project_assignments │
         │──────────────────│              │────────────────────│
         │ emp_id (PK)      │──────────────│ assignment_id (PK) │
         │ first_name       │              │ project_id (FK)    │
         │ last_name        │              │ emp_id (FK)        │
         │ email            │              │ role               │
         │ dept_id (FK)     │              │ hours_per_week     │
         │ title_id (FK)    │              └────────────────────┘
         │ salary           │
         │ hire_date        │
         │ gender           │
         │ employment_status│
         │ termination_date │
         │ work_mode        │
         │ manager_id (FK)  │──┐ (self-referencing)
         └──────────────────┘  │
              │    │    │      │
              │    │    │      │
              ▼    ▼    ▼      ▼
     ┌────────┐ ┌─────────┐ ┌─────────────────┐
     │salary_ │ │perform- │ │ training_       │
     │history │ │ance_    │ │ records         │
     │────────│ │reviews  │ │─────────────────│
     │hist_id │ │─────────│ │ record_id (PK)  │
     │emp_id  │ │review_id│ │ emp_id (FK)     │
     │old_sal │ │emp_id   │ │ course_name     │
     │new_sal │ │year     │ │ category        │
     │eff_date│ │rating   │ │ hours           │
     │reason  │ │goals_pct│ │ enrollment_date │
     └────────┘ │comments │ │ completion_date │
                │rev_date │ │ status          │
                └─────────┘ │ score           │
                            └─────────────────┘
```

---

## Table Details

### departments (8 rows)
The organizational units of TechCorp.

| Column | Type | Description |
|--------|------|-------------|
| dept_id | INTEGER | Primary key |
| dept_name | TEXT | Department name (Engineering, Marketing, Sales, etc.) |
| location | TEXT | Office city (San Francisco, New York, Chicago, Austin) |
| annual_budget | INTEGER | Annual department budget in USD |
| division | TEXT | Business division (Technology, Growth, Revenue, Operations) |
| established_date | TEXT | When the department was created |

### job_titles (38 rows)
Defines all positions with salary bands and career levels.

| Column | Type | Description |
|--------|------|-------------|
| title_id | INTEGER | Primary key |
| title | TEXT | Official job title |
| dept_id | INTEGER | FK → departments.dept_id |
| level | TEXT | Career level: Executive, Manager, Senior, Mid, Entry |
| min_salary | INTEGER | Minimum salary for this role |
| max_salary | INTEGER | Maximum salary for this role |

### employees (120 rows)
All company employees (current and former).

| Column | Type | Description |
|--------|------|-------------|
| emp_id | INTEGER | Primary key |
| first_name | TEXT | First name |
| last_name | TEXT | Last name |
| email | TEXT | Company email |
| dept_id | INTEGER | FK → departments.dept_id |
| title_id | INTEGER | FK → job_titles.title_id |
| salary | INTEGER | Current annual salary (USD) |
| hire_date | TEXT | Date hired (YYYY-MM-DD) |
| gender | TEXT | M or F |
| employment_status | TEXT | Active, Terminated, or On Leave |
| termination_date | TEXT | Date of termination (if applicable) |
| work_mode | TEXT | Remote, Hybrid, or On-site |
| manager_id | INTEGER | FK → employees.emp_id (self-referencing) |

### salary_history (308 rows)
Tracks every salary change for every employee.

| Column | Type | Description |
|--------|------|-------------|
| history_id | INTEGER | Primary key |
| emp_id | INTEGER | FK → employees.emp_id |
| old_salary | INTEGER | Previous salary |
| new_salary | INTEGER | New salary |
| effective_date | TEXT | When the change took effect |
| reason | TEXT | Annual Review, Promotion, Market Adjustment, etc. |

### projects (20 rows)
Company projects across all departments.

| Column | Type | Description |
|--------|------|-------------|
| project_id | INTEGER | Primary key |
| project_name | TEXT | Project name |
| dept_id | INTEGER | FK → departments.dept_id (owning department) |
| budget | INTEGER | Project budget in USD |
| start_date | TEXT | Project start date |
| end_date | TEXT | Target/actual end date |
| status | TEXT | Completed or In Progress |
| priority | TEXT | Critical, High, Medium, or Low |

### project_assignments (138 rows)
Maps employees to projects (many-to-many relationship).

| Column | Type | Description |
|--------|------|-------------|
| assignment_id | INTEGER | Primary key |
| project_id | INTEGER | FK → projects.project_id |
| emp_id | INTEGER | FK → employees.emp_id |
| role | TEXT | Role on project: Lead, Developer, Analyst, etc. |
| hours_per_week | INTEGER | Weekly hours allocated |

### performance_reviews (293 rows)
Annual performance evaluations (2022-2024).

| Column | Type | Description |
|--------|------|-------------|
| review_id | INTEGER | Primary key |
| emp_id | INTEGER | FK → employees.emp_id |
| review_year | INTEGER | Year of review (2022, 2023, 2024) |
| rating | INTEGER | 1-5 scale (1=Poor, 5=Exceptional) |
| goals_met_pct | INTEGER | Percentage of goals achieved (0-100) |
| reviewer_comments | TEXT | Manager's written feedback |
| review_date | TEXT | Date of review |

### training_records (418 rows)
Professional development and training completion.

| Column | Type | Description |
|--------|------|-------------|
| record_id | INTEGER | Primary key |
| emp_id | INTEGER | FK → employees.emp_id |
| course_name | TEXT | Name of training course |
| category | TEXT | Technical, Leadership, Soft Skills, Compliance, etc. |
| hours | INTEGER | Course duration in hours |
| enrollment_date | TEXT | When enrolled |
| completion_date | TEXT | When completed (blank if not yet) |
| status | TEXT | Completed, In Progress, or Enrolled |
| score | INTEGER | Final score (blank if not completed) |

---

## Key Relationships

1. **departments → employees**: One department has many employees
2. **departments → projects**: One department owns many projects
3. **departments → job_titles**: Each job title belongs to one department
4. **job_titles → employees**: Many employees can hold the same title
5. **employees → employees**: Self-referencing (manager_id → emp_id)
6. **employees ↔ projects**: Many-to-many via project_assignments
7. **employees → salary_history**: One employee has many salary changes
8. **employees → performance_reviews**: One employee has many annual reviews
9. **employees → training_records**: One employee takes many courses

---

## Common Query Patterns

These multi-table joins are representative of real HR analytics:

- **Compensation analysis**: employees + job_titles + departments + salary_history
- **Performance tracking**: employees + performance_reviews + departments
- **Project staffing**: projects + project_assignments + employees + departments
- **Training ROI**: training_records + employees + performance_reviews
- **Workforce planning**: employees + departments + job_titles (status, tenure, levels)
- **Manager reporting**: employees self-join (employee → manager hierarchy)
