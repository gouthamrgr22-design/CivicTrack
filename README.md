# CivicTrack V4.0.0

### Public Grievance & Civic Issue Reporting Platform

CivicTrack is a web-based civic grievance reporting and management platform designed to help citizens report public infrastructure problems, track complaint progress, and improve communication between citizens and responsible administrators.

The project provides a citizen-facing reporting experience alongside authentication, complaint tracking, employee workflows, and administrative management.

**Current release:** V4.0.0 — Visual Revolution  
**Project type:** Full-stack web application  
**License:** Not yet specified

---

## Features

### Citizen
- Citizen registration and login
- Google Sign-In integration
- Email verification
- Submit civic complaints
- Track complaint status
- View complaint information
- Responsive user interface

### Employee
- Employee account registration
- Administrator-controlled employee approval
- Employee dashboard
- Complaint management workflows
- Complaint status updates and history

### Administrator
- Administrator authentication
- Administrative dashboard
- Overview of complaint activity
- Employee approval and rejection
- Account and complaint management

### Platform
- Python HTTP server
- REST-style API endpoints
- SQLite database
- Session-based authentication
- Email verification through Resend
- Google identity token verification
- Leaflet-based map interface with OpenStreetMap

---

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | HTML5, CSS3, JavaScript |
| Backend | Python |
| HTTP server | Python standard library |
| Database | SQLite |
| Authentication | Python authentication services |
| Google authentication | Google Identity Services |
| Email delivery | Resend |
| Maps | Leaflet and OpenStreetMap |
| Version control | Git |

CivicTrack uses a lightweight architecture without requiring a large web framework.

---

# Installation

You can download CivicTrack and run your own local instance on your computer.

## 1. Requirements

Before installing, make sure you have:

- Python 3.10 or newer
- Git (only required for cloning)
- A modern web browser
- Internet access for installing dependencies and using external services

## 2. Download CivicTrack

### Option A — Download ZIP

1. Open the [CivicTrack GitHub repository](https://github.com/gouthamrgr22-design/CivicTrack).
2. Select the `v4.0.0` release/tag.
3. Download the source ZIP archive.
4. Extract the archive.
5. Open a terminal inside the extracted `CivicTrack` directory.

### Option B — Clone using Git

```bash
git clone https://github.com/gouthamrgr22-design/CivicTrack.git

cd CivicTrack

git checkout v4.0.0
```

## 3. Create a Python virtual environment

A virtual environment keeps CivicTrack's Python dependencies separate from your system Python installation.

### Linux — Bash

```bash
python -m venv .venv

source .venv/bin/activate
```

### Arch Linux — Fish

```fish
python -m venv .venv

source .venv/bin/activate.fish
```

### Windows — PowerShell

```powershell
py -m venv .venv

.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can use the virtual environment's Python executable directly:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 4. Install dependencies

With the virtual environment activated, run:

```bash
python -m pip install --upgrade pip

python -m pip install -r requirements.txt
```

CivicTrack's Python dependency list is maintained in `requirements.txt`.

## 5. Configure environment variables

Create your local environment configuration:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Open `.env` in your preferred editor and configure the required values.

```env
GOOGLE_CLIENT_ID=your-google-web-client-id.apps.googleusercontent.com

RESEND_API_KEY=re_your_resend_api_key

RESEND_FROM=CivicTrack <onboarding@resend.dev>

CIVICTRACK_BASE_URL=http://127.0.0.1:8000
```

### Google Sign-In

To enable Google Sign-In:

1. Create a Google OAuth client in Google Cloud Console.
2. Configure it as a Web application.
3. Add the following authorized JavaScript origin:

   `http://127.0.0.1:8000`

4. Copy the Web client ID into `GOOGLE_CLIENT_ID`.

Google Sign-In will not work until it is configured.

### Email verification

CivicTrack uses Resend for email delivery.

To enable verification emails:

1. Create a Resend account.
2. Generate an API key.
3. Configure an authorized sender address.
4. Add the API key and sender address to `.env`.

Email verification and the initial administrator setup require working email delivery.

**Important:** External service credentials are not included with the downloaded project. Each installation must use its own credentials.

Never publish your `.env` file or share API keys.

---

## 6. Start CivicTrack

From the project root, with the virtual environment activated, run:

```bash
python app/main.py
```

The application initializes its SQLite database automatically when the server starts.

You should see the server startup information in your terminal.

## 7. Open CivicTrack

Open your browser and visit:

**Citizen website**

http://127.0.0.1:8000/

**Login page**

http://127.0.0.1:8000/templates/login.html

**Employee dashboard**

http://127.0.0.1:8000/employee

**Administrator dashboard**

http://127.0.0.1:8000/admin

To stop the server, press:

`Ctrl + C`

---

# Initial Administrator Setup

A fresh installation does not automatically contain an administrator account.

Configure Resend first, then run the administrator setup script from the project root:

```bash
python scripts/bootstrap_admin.py
```

The script asks for:

- Administrator full name
- Username
- Email address
- Password
- Password confirmation

The administrator account is created locally, and a verification email is sent.

Verify the administrator email before attempting to log in.

The script prevents creating another administrator if one already exists.

---

# Database

CivicTrack uses SQLite.

The database is automatically created at:

```text
data/civictrack.db
```

Each installation maintains its own local database.

This means downloading CivicTrack does not download another user's accounts, complaints, or database records.

Keep backups of your database if you need to preserve your local data.

---

# Project Structure

```text
CivicTrack/
├── app/
│   ├── core/
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── static/
│   │   ├── css/
│   │   ├── images/
│   │   └── js/
│   ├── templates/
│   └── main.py
├── data/
├── docs/
├── scripts/
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

# Troubleshooting

### Python command not found

Check your Python installation:

```bash
python --version
```

On Windows, try:

```powershell
py --version
```

### Dependency installation fails

Make sure your virtual environment is activated, then run:

```bash
python -m pip install -r requirements.txt
```

### Port 8000 is already in use

Another application may already be using port 8000. Stop that application before starting CivicTrack.

### Google Sign-In is unavailable

Check that `GOOGLE_CLIENT_ID` is configured correctly and that the OAuth client has the local origin registered.

### Verification emails are not arriving

Check the Resend API key, sender configuration, account status, and email delivery logs.

### Database problems

Stop the application and check that the `data` directory is writable.

Do not delete your database unless you intentionally want to remove your local application data.

---

# Security Notes

- Never commit `.env` or API keys.
- Never publish private database files.
- Do not reuse another installation's administrator credentials.
- Employee accounts require administrator approval.
- Use HTTPS and appropriate production security configuration before making an instance publicly accessible.

**Local installation is intended for personal or development use.** The development server binds to `127.0.0.1` and is not configured as a public production hosting server.

---

# Contributing

Contributions, bug reports, suggestions, and improvements are welcome.

If you want to contribute:

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Test your changes.
5. Submit a pull request.

---

# Project Vision

CivicTrack aims to make civic issue reporting more accessible, transparent, and manageable through technology.

The long-term goal is to develop a reliable platform connecting citizens, employees, and administrators through a structured grievance management workflow.

---

## Repository

**GitHub:** https://github.com/gouthamrgr22-design/CivicTrack

**Release:** V4.0.0 — Visual Revolution

**Developed with Python, SQLite, HTML, CSS, and JavaScript.**
