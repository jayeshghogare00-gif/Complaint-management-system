# College Grievance Management System

A complete Flask + SQLite college complaint/grievance management system.

## Features

- Student registration and login
- Admin login
- Password hashing
- Role-based authorization
- Student complaint submission
- Unique complaint tracking IDs
- Student complaint history
- Complaint detail page
- Admin dashboard
- Status management
- Admin response
- Priority management
- Search/filter-ready admin interface
- Protected delete/update actions
- JSON API endpoints
- SQLite database
- Responsive mobile-friendly UI

## Run

```bash
python -m venv venv
```

Windows:
```bash
venv\Scripts\activate
```

Android/Termux/Linux:
```bash
source venv/bin/activate
```

Install:
```bash
pip install -r requirements.txt
```

Run:
```bash
python app.py
```

Open:
`http://127.0.0.1:5000`

## Deploy to Render (Step-by-Step)

The project is pre-configured with `render.yaml` and `Procfile`.

### Method 1: Deploy with Git / GitHub (Recommended)
1. Push this folder to a GitHub repository:
   - Initialize git: `git init`
   - Stage and commit: `git add .` then `git commit -m "Initial commit"`
   - Push to your GitHub repo: `git remote add origin <your-repo-url>` and `git push -u origin main`
2. Go to [render.com](https://render.com) and log in.
3. Click **New +** > **Web Service**.
4. Connect your GitHub repository.
5. Render will automatically detect the settings from `render.yaml` or you can verify:
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
6. Under **Environment Variables**, add:
   - `SECRET_KEY` = (A secure random string)
   - *(Optional for persistent database)*: `DATABASE_URL` = (Your PostgreSQL internal URL from Render)
7. Click **Deploy Web Service**.

### Method 2: One-Click Blueprint
1. In Render, select **New +** > **Blueprint**.
2. Select your repository. Render will read `render.yaml` and configure the service automatically.

## Default Admin

Email:
`admin@college.local`

Password:
`Admin@123`

Change the admin password and SECRET_KEY before deploying publicly.
