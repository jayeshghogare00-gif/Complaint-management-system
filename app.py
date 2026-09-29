from datetime import datetime, timezone
from functools import wraps
import os
import re
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url or ("sqlite:///" + os.path.join(BASE_DIR, "college_cms.db"))
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

ALLOWED_CATEGORIES = {"Academic", "Hostel", "Library", "IT / Computer", "Infrastructure", "Transport", "Other"}
ALLOWED_PRIORITIES = {"Low", "Medium", "High", "Urgent"}
ALLOWED_STATUSES = {"Pending", "In Progress", "Resolved", "Rejected"}


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    roll_number = db.Column(db.String(30), unique=True, nullable=True, index=True)
    department = db.Column(db.String(100), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    complaints = db.relationship("Complaint", backref="student", lazy=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tracking_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="Medium")
    status = db.Column(db.String(30), nullable=False, default="Pending")
    admin_response = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") != role:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def valid_email(email):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email or ""))


def next_tracking_number():
    year = datetime.now().year
    last = Complaint.query.order_by(Complaint.id.desc()).first()
    number = (last.id + 1) if last else 1
    return f"CMP-{year}-{number:04d}"


@app.context_processor
def inject_user():
    return {"current_user": db.session.get(User, session["user_id"]) if session.get("user_id") else None}


@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("student_dashboard"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        roll_number = request.form.get("roll_number", "").strip().upper()
        department = request.form.get("department", "").strip()
        password = request.form.get("password", "")

        errors = []
        if len(name) < 2 or len(name) > 100:
            errors.append("Enter a valid name.")
        if not valid_email(email):
            errors.append("Enter a valid email address.")
        if not roll_number or len(roll_number) > 30:
            errors.append("Enter a valid roll number.")
        if len(department) < 2 or len(department) > 100:
            errors.append("Enter a valid department.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if User.query.filter_by(email=email).first():
            errors.append("Email is already registered.")
        if User.query.filter_by(roll_number=roll_number).first():
            errors.append("Roll number is already registered.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("register.html")

        user = User(
            name=name,
            email=email,
            roll_number=roll_number,
            department=department,
            password_hash=generate_password_hash(password),
            role="student",
        )
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user.id
        session["role"] = user.role
        session["name"] = user.name

        if user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("student_dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/admin/account", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_account():
    admin = db.get_or_404(User, session["user_id"])

    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not check_password_hash(admin.password_hash, current_password):
            flash("Current password is incorrect.", "error")
        elif len(email) > 150 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Enter a valid email or login address.", "error")
        elif User.query.filter(User.email == email, User.id != admin.id).first():
            flash("That email address is already in use.", "error")
        elif len(password) < 8:
            flash("New password must be at least 8 characters.", "error")
        elif password != confirm_password:
            flash("New passwords do not match.", "error")
        else:
            admin.email = email
            admin.password_hash = generate_password_hash(password)
            db.session.commit()
            flash("Admin email and password updated.", "success")
            return redirect(url_for("admin_account"))

    return render_template("admin_account.html", admin=admin)


@app.route("/student")
@login_required
@role_required("student")
def student_dashboard():
    complaints = Complaint.query.filter_by(student_id=session["user_id"]).order_by(Complaint.created_at.desc()).all()
    return render_template("student.html", complaints=complaints)


@app.route("/admin")
@login_required
@role_required("admin")
def admin_dashboard():
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    stats = {
        "total": Complaint.query.count(),
        "pending": Complaint.query.filter_by(status="Pending").count(),
        "progress": Complaint.query.filter_by(status="In Progress").count(),
        "resolved": Complaint.query.filter_by(status="Resolved").count(),
        "urgent": Complaint.query.filter_by(priority="Urgent").count(),
    }
    return render_template("admin.html", complaints=complaints, stats=stats)


@app.route("/complaint/<int:complaint_id>")
@login_required
def complaint_detail(complaint_id):
    complaint = db.get_or_404(Complaint, complaint_id)
    if session["role"] == "student" and complaint.student_id != session["user_id"]:
        abort(403)
    return render_template("detail.html", complaint=complaint)


@app.route("/complaints/create", methods=["POST"])
@login_required
@role_required("student")
def create_complaint():
    category = request.form.get("category", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    priority = request.form.get("priority", "Medium").strip()

    if category not in ALLOWED_CATEGORIES:
        flash("Invalid category.", "error")
    elif priority not in ALLOWED_PRIORITIES:
        flash("Invalid priority.", "error")
    elif not (5 <= len(title) <= 150):
        flash("Title must be between 5 and 150 characters.", "error")
    elif not (10 <= len(description) <= 5000):
        flash("Description must be between 10 and 5000 characters.", "error")
    else:
        complaint = Complaint(
            tracking_number=next_tracking_number(),
            student_id=session["user_id"],
            category=category,
            title=title,
            description=description,
            priority=priority,
            status="Pending",
        )
        db.session.add(complaint)
        db.session.commit()
        flash(f"Complaint submitted successfully. Tracking ID: {complaint.tracking_number}", "success")

    return redirect(url_for("student_dashboard"))


@app.route("/admin/complaint/<int:complaint_id>/update", methods=["POST"])
@login_required
@role_required("admin")
def update_complaint(complaint_id):
    complaint = db.get_or_404(Complaint, complaint_id)
    status = request.form.get("status", "")
    response = request.form.get("admin_response", "").strip()

    if status not in ALLOWED_STATUSES:
        flash("Invalid status.", "error")
        return redirect(url_for("admin_dashboard"))

    complaint.status = status
    complaint.admin_response = response[:5000] if response else None
    complaint.updated_at = datetime.now(timezone.utc)
    complaint.resolved_at = datetime.now(timezone.utc) if status == "Resolved" else None
    db.session.commit()

    flash(f"{complaint.tracking_number} updated successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/complaint/<int:complaint_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_complaint(complaint_id):
    complaint = db.get_or_404(Complaint, complaint_id)
    db.session.delete(complaint)
    db.session.commit()
    flash("Complaint deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/api/my-complaints")
@login_required
@role_required("student")
def api_my_complaints():
    complaints = Complaint.query.filter_by(student_id=session["user_id"]).order_by(Complaint.created_at.desc()).all()
    return jsonify([serialize_complaint(c) for c in complaints])


@app.route("/api/complaints")
@login_required
@role_required("admin")
def api_complaints():
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return jsonify([serialize_complaint(c, include_student=True) for c in complaints])


def serialize_complaint(c, include_student=False):
    data = {
        "id": c.id,
        "tracking_number": c.tracking_number,
        "category": c.category,
        "title": c.title,
        "description": c.description,
        "priority": c.priority,
        "status": c.status,
        "admin_response": c.admin_response,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
        "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
    }
    if include_student:
        data["student"] = {
            "name": c.student.name,
            "email": c.student.email,
            "roll_number": c.student.roll_number,
            "department": c.student.department,
        }
    return data


def seed_admin():
    if not User.query.filter_by(role="admin").first():
        admin = User(
            name="System Administrator",
            email="BSCIT@gmail.com",
            password_hash=generate_password_hash("Junnar@123"),
            role="admin",
        )
        db.session.add(admin)
        db.session.commit()
       


with app.app_context():
    db.create_all()
    seed_admin()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
