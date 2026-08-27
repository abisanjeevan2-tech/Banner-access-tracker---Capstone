# Winthrop University — Banner Access Tracker

A secure web application for managing Banner system access requests with a single-approval workflow. Built with Python FastAPI, PostgreSQL, and Docker.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Default Accounts](#default-accounts)
- [Role Descriptions](#role-descriptions)
- [How the Application Works](#how-the-application-works)
- [Managing the Application](#managing-the-application)
- [Startup Commands Reference](#startup-commands-reference)
- [Troubleshooting](#troubleshooting)
- [Tech Stack](#tech-stack)

---

## Overview

The Banner Access Tracker is a form request system that allows university staff to request access to Banner system forms. Requests require approval from an authorized Grantor before the Help Desk receives a notification email with the applicant's full information and PDF download links for the approved forms. The Help Desk is then responsible for distributing the approved forms to the applicant.

**User Roles:**
- **Grantee** — Submits access requests
- **Grantor** — Reviews and approves or denies requests
- **Administrator** — Manages all requests, forms, and grantor assignments
- **SuperUser** — Full system control including user management and system settings

---

## Prerequisites

Before you begin make sure you have the following installed on your computer:

### 1. Docker Desktop
- Download from: https://www.docker.com/products/docker-desktop
- Install and open Docker Desktop
- Wait until it shows "Engine running" in the bottom left corner
- The whale icon in your taskbar (Windows) or menu bar (Mac) should be still, not animated

### 2. Git
- Download from: https://git-scm.com/downloads
- Install with default settings

### 3. A Gmail Account (for email notifications)
- Create a free Gmail account at https://gmail.com if you do not already have one dedicated to this application
- You will need to generate an App Password — instructions are in the Configuration section below

---

## Installation

### Step 1 — Clone the Repository

Open PowerShell or Terminal and run:

```bash
git clone https://github.com/WinthropUniversity/project-2025-2026-group-6.git
```

### Step 2 — Navigate to the Project Folder

```bash
cd "project-2025-2026-group-6/Project/FrontEnd/banner-access-tracker/banner-access-tracker"
```

You should see these files in the folder:

```
alembic/
app/
tests/
.env.example
alembic.ini
docker-compose.yml
Dockerfile
requirements.txt
README.md
```

---

## Configuration

Before running the application you must create a .env file with your credentials. This file tells the application how to connect to the database and how to send emails.

### Step 1 — Create the .env file

In the project folder (same folder as docker-compose.yml) create a new file called exactly .env and paste the following contents into it:

```
DATABASE_URL=postgresql://postgres:postgres@db:5432/banner_access
SECRET_KEY=your-secret-key-change-in-production-min-32-chars-long
ENCRYPTION_KEY=encryption-key-change-in-production-must-be-32-url-safe-base64-chars
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_FROM=your.gmail@gmail.com
SMTP_USER=your.gmail@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SMTP_ENABLED=true
HELPDESK_EMAIL=your.gmail@gmail.com
BASE_URL=http://localhost:8000
ENVIRONMENT=development
MAX_UPLOAD_SIZE_MB=10
ALLOWED_UPLOAD_EXTENSIONS=.pdf,.docx,.jpeg,.jpg,.png
```

Replace the following values:
- your.gmail@gmail.com with the Gmail address that will send notification emails
- your-16-char-app-password with your Gmail App Password (see Step 2)

Important: Never share your .env file or commit it to GitHub. It contains sensitive credentials.

### Step 2 — Generate a Gmail App Password

Gmail requires an App Password for third party applications to send email. Your regular Gmail password will not work.

1. Go to https://myaccount.google.com and sign in
2. Click Security in the left sidebar
3. Under How you sign in to Google click 2-Step Verification and enable it
4. After enabling 2-Step Verification go back to Security
5. Search for App Passwords in the search bar at the top
6. Click App Passwords
7. In the App name field type Banner Tracker and click Create
8. Google will show you a 16-character password
9. Copy it and paste it into your .env file as SMTP_PASSWORD and remove any spaces

---

## Running the Application

### Step 1 — Make sure Docker Desktop is running

Open Docker Desktop and wait until it shows Engine running in the bottom left. Do not proceed until Docker is fully started.

### Step 2 — Open PowerShell in the project folder

```bash
cd "project-2025-2026-group-6/Project/FrontEnd/banner-access-tracker/banner-access-tracker"
```

### Step 3 — Build and start the application

Run this command the first time or any time code changes have been made:

```bash
docker-compose up --build
```

For subsequent startups after the initial build:

```bash
docker-compose up
```

### Step 4 — Wait for the application to start

Watch the terminal output. You will see the database being set up and seeded. The application is ready when you see this line:

```
web-1  | INFO:     Application startup complete.
```

This may take 30 to 60 seconds on first run.

### Step 5 — Open the application

Open your browser and go to:

```
http://localhost:8000
```

You should see the Winthrop University Banner Access Tracker login page.

### Step 6 — Log in

Use one of the default accounts listed in the Default Accounts section below.

### Step 7 — Stop the application

When you are done press Ctrl + C in the terminal then run:

```bash
docker-compose down
```

---

## Default Accounts

The application automatically creates these demo accounts on first run. Use these to test and explore the system before creating real accounts.

| Username | Password | Role |
|---|---|---|
| grantee1 | password | Grantee |
| grantor1 | password | Grantor |
| grantor2 | password | Grantor |
| admin1 | password | Administrator |
| superuser1 | password | SuperUser |

Change these passwords immediately before going live. Log in as SuperUser, go to Manage Users, and edit each account.

Note: New Grantor accounts default to no form assignments and will not see any requests until an Administrator or SuperUser assigns forms to them through the Grantor Assignments page.

---

## Role Descriptions

### Grantee
- Submits Banner form access requests specifying Read or Read/Write access type
- Views the status of their own submitted requests
- Receives a confirmation email when a request is submitted
- Can attach supporting documents to their request

### Grantor
- Reviews pending access requests
- Only sees requests containing forms they are authorized to approve
- New grantors default to no assignments and see no requests until assigned
- Can view attached PDF documents inline in the browser without downloading
- Approves or denies requests with an optional comment
- One Grantor approval is required for a request to be fully approved

### Administrator
- Views and manages all requests in the system
- Creates, edits, and deletes Banner forms
- Uploads PDF versions of forms
- Assigns which forms each Grantor is authorized to approve
- Can view attached PDF documents inline in the browser
- Exports the full request log as a CSV file

### SuperUser
- All Administrator permissions
- Creates, edits, and deletes user accounts
- Assigns roles to users
- Imports users in bulk via CSV file
- Manages system settings including the Help Desk email address

---

## How the Application Works

### Request Workflow

```
Grantee logs in and submits a request selecting forms,
access type (Read or Read/Write), and optional notes and attachments
              |
              v
Grantee receives confirmation email
              |
              v
Grantor logs in, reviews request details
and attached documents, then approves or denies
              |
              v
Request is marked as Approved or Rejected
              |
              v
Help Desk receives notification email with full applicant
info, access type, requested forms, and PDF download links
Help Desk distributes approved forms to applicant
```

### Email Notifications

The system sends two types of emails:

1. Submission Confirmation — sent to the Grantee when they submit a request confirming it was received
2. Help Desk Approval Notification — sent to the configured Help Desk email when a request is approved, includes the applicant username, email, CWID, access type, requested forms, and PDF download links

The Help Desk email address can be updated at any time by a SuperUser through the System Settings page.

### Access Types

When submitting a request Grantees must choose one of two access types:

- Read — view access only to the requested Banner forms
- Read/Write — view and edit access to the requested Banner forms

This choice is stored with the request and included in the Help Desk notification email.

### PDF Forms

Administrators upload PDF versions of Banner forms through the Manage Forms page. When a request is approved the Help Desk notification email includes download links for each form that has a PDF uploaded. If no PDF is uploaded for a form the email will note that and the Help Desk should handle distribution manually.

### Inline Document Viewing

Grantors and Administrators can view PDF attachments submitted by Grantees directly in the browser without downloading. A View button opens the document in a popup window within the application. A Download button is also available for saving the file locally.

### Grantor Form Assignments

Administrators control which forms each Grantor is authorized to approve through the Grantor Assignments page.

- All forms checked — Grantor sees all requests
- Some forms checked — Grantor sees only requests containing those forms
- None checked — Grantor sees no requests (default for new grantors)

### CSV User Import

SuperUsers can import multiple users at once via CSV file. The CSV must follow this exact format:

```
cwid,username,password,email,role
12345678,jdoe,password123,jdoe@winthrop.edu,Grantee
87654321,jsmith,password123,jsmith@winthrop.edu,Grantor
```

Rules:
- The first row must be the header exactly as shown
- All fields are required including email
- Role must be exactly one of: Grantee, Grantor, Administrator, SuperUser
- CWID must be exactly 8 digits
- If any row has an error the entire import is rejected and no users are added
- Existing users with the same CWID or username will cause an error

---

## Managing the Application

### Creating User Accounts

1. Log in as SuperUser
2. Click Manage Users in the sidebar
3. Fill in the Add New User form with CWID, username, password, email, and role
4. Click Add User

Or to import multiple users at once use the Import Users from CSV section on the same page.

### Adding Banner Forms

1. Log in as Administrator or SuperUser
2. Click Manage Forms in the sidebar
3. Enter the form code and description and click Add Form
4. To attach a PDF click the Upload PDF button next to the form

### Assigning Forms to Grantors

1. Log in as Administrator or SuperUser
2. Click Grantor Assignments in the sidebar
3. For each Grantor use the search box to find forms and check the ones they should be able to approve
4. Check all forms to let the Grantor see all requests
5. Leave all unchecked (None) to prevent the Grantor from seeing any requests
6. Use Select All or Clear All for quick bulk selection
7. Click Save Assignments

### Updating the Help Desk Email

1. Log in as SuperUser
2. Click System Settings in the sidebar
3. Update the Help Desk Email Address field
4. Click Update Email

All future approval notifications will be sent to the new address immediately.

### Reviewing and Managing Requests

1. Log in as Administrator or SuperUser
2. Click All Requests in the sidebar
3. Use the Status filter and Search box to find specific requests
4. Click View on any request to see full details, view attachments inline, and update its status

### Exporting the Request Log

1. Log in as Administrator or SuperUser
2. Click Export Request Log in the sidebar
3. A CSV file will download containing all request data

### Clearing Test Data

To delete all requests while keeping users, forms, and settings intact run this command while Docker is running:

```bash
docker exec banner-access-tracker-web-1 python -c "
from app.database import SessionLocal
from app.models import AccessRequest, Approval, Attachment, AccessChange
db = SessionLocal()
db.query(Attachment).delete()
db.query(Approval).delete()
db.query(AccessChange).delete()
db.query(AccessRequest).delete()
db.commit()
print('All requests cleared!')
db.close()
"
```

---

## Startup Commands Reference

### First time setup or after code changes

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Normal startup

```bash
docker-compose up
```

### Stop the application

```bash
docker-compose down
```

### View application logs

```bash
docker logs banner-access-tracker-web-1
```

### View recent errors

```bash
docker logs banner-access-tracker-web-1 2>&1 | Select-Object -Last 50
```

---

## Troubleshooting

### Docker Desktop is not running
Open Docker Desktop from the Start menu and wait for it to fully start before running any commands. The whale icon in the taskbar should be still not animated.

### Application will not start
Try a full rebuild:

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Cannot find the .env file
- Make sure the file is named exactly .env with no other extension
- It must be in the same folder as docker-compose.yml
- On Windows use PowerShell to create it to avoid encoding issues
- Hidden files may not show in File Explorer — use PowerShell to verify it exists:

```bash
Get-ChildItem -Force | Where-Object { $_.Name -eq ".env" }
```

### Emails are not being sent
- Make sure SMTP_ENABLED=true in your .env file
- Make sure your Gmail App Password is correct with no spaces
- Make sure 2-Step Verification is enabled on your Gmail account
- Rebuild Docker after any .env changes:

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Login page shows a 500 error
Check the Docker logs for the specific error message:

```bash
docker logs banner-access-tracker-web-1 2>&1 | Select-Object -Last 30
```

### Database errors on startup
If you need to completely reset the database and start fresh run:

```bash
docker-compose down -v
docker-compose up --build
```

Warning: This deletes all data in the database including any user accounts and requests you have created.

### Port 8000 is already in use
Another application is using port 8000. Either stop that application or change the port in docker-compose.yml from 8000:8000 to 8001:8000 and access the app at http://localhost:8001.

### Grantor sees no requests
New Grantors default to no form assignments. An Administrator or SuperUser must assign forms to them through the Grantor Assignments page before they can see any requests.

---

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy + Alembic |
| Templates | Jinja2 |
| Authentication | Session-based + bcrypt |
| Encryption | Fernet (AES-128) |
| Email | SMTP via Gmail |
| Containerization | Docker + Docker Compose |

---

## Support

For technical issues contact Winthrop University IT Support.

For questions about this application contact the development team.
