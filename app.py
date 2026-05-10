from flask import Flask, jsonify, request, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# Updated database name and added a secret key for sessions
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

def to_utc(local_time_str, user_tz):
    """
    Convert user local time → UTC datetime
    """
    if not local_time_str:
        return None

    # 1. parse string
    naive_dt = datetime.strptime(local_time_str, '%Y-%m-%dT%H:%M')

    # 2. attach user timezone
    tz = pytz.timezone(user_tz)
    local_dt = tz.localize(naive_dt)

    # 3. convert to UTC
    return local_dt.astimezone(pytz.utc).replace(tzinfo=None)

# --- Models ---

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100))
    avatar_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owned_projects = db.relationship(
    'Project',
    backref='owner',
    lazy=True,
    foreign_keys='Project.owner_id'
    )

    assigned_tasks = db.relationship(
        'Task',
        backref='assignee',
        lazy=True,
        foreign_keys='Task.assignee_id'
    )

    created_tasks = db.relationship(
        'Task',
        backref='creator',
        lazy=True,
        foreign_keys='Task.created_by'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Boilerplate for Flask-Login to load a user from the ID
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    tasks = db.relationship('Task', backref='project', cascade="all, delete-orphan", lazy=True)
    members = db.relationship('ProjectMember', backref='project', cascade="all, delete-orphan", lazy=True)

class ProjectMember(db.Model):
    __tablename__ = 'project_members'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    
    # status: todo, in_progress, done
    status = db.Column(db.String(20), default='todo')
    # priority: low, medium, high
    priority = db.Column(db.String(20), default='medium')
    
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    start_date = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# --- Routes ---

@app.route('/')
def index():
    return jsonify({"message": "Task Tracking API is running", "database": "shop_db"})

@app.route('/projects')
@login_required
def projects_page():

    owned_projects = Project.query.filter_by(
        owner_id=current_user.id
    ).all()

    member_projects = Project.query.join(ProjectMember).filter(
        ProjectMember.user_id == current_user.id
    ).all()

    projects = list({
        project.id: project
        for project in (owned_projects + member_projects)
    }.values())

    return render_template(
        'projects.html',
        projects=projects
    )

@app.route('/tasks')
@login_required
def tasks_page():

    now = datetime.utcnow()

    tasks = Task.query.filter_by(
        assignee_id=current_user.id
    ).order_by(
        Task.due_date.asc()
    ).all()

    overdue_tasks = []
    today_tasks = []
    upcoming_tasks = []
    no_due_tasks = []

    for task in tasks:

        if not task.due_date:
            no_due_tasks.append(task)

        elif task.due_date < now and task.status != 'done':
            overdue_tasks.append(task)

        elif task.due_date.date() == now.date():
            today_tasks.append(task)

        else:
            upcoming_tasks.append(task)

    return render_template(
        'tasks.html',
        overdue_tasks=overdue_tasks,
        today_tasks=today_tasks,
        upcoming_tasks=upcoming_tasks,
        no_due_tasks=no_due_tasks,
        now=now
    )

@app.route('/projects/<int:project_id>/tasks', methods=['GET'])
def get_project_tasks(project_id):
    tasks = Task.query.filter_by(project_id=project_id).all()
    return jsonify([{
        "id": t.id,
        "title": t.title,
        "status": t.status,
        "priority": t.priority,
        "assignee": t.assignee.username if t.assignee else "Unassigned"
    } for t in tasks])

# --- Auth Routes ---

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'GET':
        return render_template('register.html')

    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    if User.query.filter_by(username=username).first():
        return "Username already exists"

    user = User(
        username=username,
        email=email
    )

    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return redirect(url_for('login'))
    data = request.get_json()
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already exists"}), 400
    
    new_user = User(
        username=data['username'],
        email=data['email'],
        full_name=data.get('full_name')
    )
    new_user.set_password(data['password'])
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'GET':
        return render_template('login.html')

    username = request.form['username']
    password = request.form['password']

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        return redirect(url_for('dashboard'))

    return "Invalid credentials"

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"}), 200

@app.route('/dashboard')
@login_required
def dashboard():

    # Projects where user is owner
    owned_projects = Project.query.filter_by(
        owner_id=current_user.id
    ).all()

    # Projects where user is a member
    member_projects = Project.query.join(ProjectMember).filter(
        ProjectMember.user_id == current_user.id
    ).all()

    # Merge + remove duplicates
    projects = list({
        project.id: project
        for project in (owned_projects + member_projects)
    }.values())

    # Recent tasks from user's projects
    recent_tasks = Task.query.join(Project).filter(
        Project.id.in_([p.id for p in projects])
    ).order_by(
        Task.created_at.desc()
    ).limit(10).all()

    # Stats
    total_projects = len(projects)

    completed_tasks = Task.query.join(Project).filter(
        Project.id.in_([p.id for p in projects]),
        Task.status == 'done'
    ).count()

    pending_tasks = Task.query.join(Project).filter(
        Project.id.in_([p.id for p in projects]),
        Task.status != 'done'
    ).count()

    return render_template(
        'dashboard.html',
        projects=projects,
        recent_tasks=recent_tasks,
        total_projects=total_projects,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks
    )

@app.route('/create-project', methods=['GET', 'POST'])
@login_required
def create_project():

    if request.method == 'GET':
        return render_template('create_project.html')

    name = request.form['name']
    description = request.form.get('description')

    if not name.strip():
        return "Project name is required"

    project = Project(
        name=name,
        description=description,
        owner_id=current_user.id
    )

    db.session.add(project)
    db.session.commit()

    # Automatically add owner as project member
    member = ProjectMember(
        project_id=project.id,
        user_id=current_user.id
    )

    db.session.add(member)
    db.session.commit()

    return redirect(url_for('dashboard'))

@app.route('/projects/<int:project_id>')
@login_required
def project_detail(project_id):

    project = Project.query.get_or_404(project_id)

    # Optional security check
    is_member = ProjectMember.query.filter_by(
        project_id=project.id,
        user_id=current_user.id
    ).first()

    if not is_member and project.owner_id != current_user.id:
        return "Access denied", 403

    todo_tasks = Task.query.filter_by(
        project_id=project.id,
        status='todo'
    ).all()

    in_progress_tasks = Task.query.filter_by(
        project_id=project.id,
        status='in_progress'
    ).all()

    done_tasks = Task.query.filter_by(
        project_id=project.id,
        status='done'
    ).all()

    members = User.query.join(ProjectMember).filter(
        ProjectMember.project_id == project.id
    ).all()

    return render_template(
        'project_detail.html',
        project=project,
        todo_tasks=todo_tasks,
        in_progress_tasks=in_progress_tasks,
        done_tasks=done_tasks,
        members=members,
        now=datetime.utcnow().replace(tzinfo=None)
    )

@app.route('/projects/<int:project_id>/create-task', methods=['POST'])
@login_required
def create_task(project_id):

    project = Project.query.get_or_404(project_id)

    title = request.form['title']
    description = request.form.get('description')

    priority = request.form.get('priority', 'medium')

    assignee_id = request.form.get('assignee_id')

    start_date = request.form.get('start_date')
    due_date = request.form.get('due_date')

    timezone = request.form.get('timezone')  # MUST come from frontend

    parsed_start_date = to_utc(start_date, timezone)
    parsed_due_date = to_utc(due_date, timezone)
    task = Task(
        project_id=project.id,
        title=title,
        description=description,
        priority=priority,
        status='todo',

        assignee_id=int(assignee_id)
        if assignee_id else None,

        created_by=current_user.id,

        start_date=parsed_start_date,
        due_date=parsed_due_date
    )

    db.session.add(task)
    db.session.commit()

    return redirect(url_for(
        'project_detail',
        project_id=project.id
    ))

@app.route('/projects/<int:project_id>/add-member', methods=['POST'])
@login_required
def add_project_member(project_id):

    project = Project.query.get_or_404(project_id)

    # Only owner can add members
    if project.owner_id != current_user.id:
        return "Access denied", 403

    username = request.form['username']

    user = User.query.filter_by(username=username).first()

    if not user:
        return "User not found"

    # Prevent duplicates
    existing_member = ProjectMember.query.filter_by(
        project_id=project.id,
        user_id=user.id
    ).first()

    if existing_member:
        return "User already in project"

    new_member = ProjectMember(
        project_id=project.id,
        user_id=user.id
    )

    db.session.add(new_member)
    db.session.commit()

    return redirect(url_for(
        'project_detail',
        project_id=project.id
    ))

@app.route('/tasks/<int:task_id>/move', methods=['POST'])
@login_required
def move_task(task_id):

    task = Task.query.get_or_404(task_id)
    data = request.get_json()

    new_status = data.get('status')

    if new_status not in ['todo', 'in_progress', 'done']:
        return jsonify({"success": False}), 400

    # security check
    project = Project.query.get(task.project_id)

    is_member = ProjectMember.query.filter_by(
        project_id=project.id,
        user_id=current_user.id
    ).first()

    if not is_member and project.owner_id != current_user.id:
        return jsonify({"success": False, "error": "Forbidden"}), 403

    task.status = new_status
    task.updated_at = datetime.utcnow()

    db.session.commit()

    return jsonify({"success": True})

@app.route('/tasks/<int:task_id>/edit', methods=['POST'])
@login_required
def edit_task(task_id):

    task = Task.query.get_or_404(task_id)

    project = Project.query.get(task.project_id)

    # permission
    if current_user.id != task.created_by and current_user.id != project.owner_id:
        return "Forbidden", 403

    timezone = request.form.get('timezone')

    task.title = request.form['title']
    task.description = request.form.get('description')
    task.priority = request.form.get('priority', 'medium')

    assignee_id = request.form.get('assignee_id')

    task.assignee_id = int(assignee_id) if assignee_id else None

    task.start_date = to_utc(
        request.form.get('start_date'),
        timezone
    )

    task.due_date = to_utc(
        request.form.get('due_date'),
        timezone
    )

    task.updated_at = datetime.utcnow()

    db.session.commit()

    return redirect(url_for(
        'project_detail',
        project_id=project.id
    ))

@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):

    task = Task.query.get_or_404(task_id)

    project = Project.query.get(task.project_id)

    # permission
    if current_user.id != task.created_by and current_user.id != project.owner_id:
        return "Forbidden", 403

    project_id = project.id

    db.session.delete(task)
    db.session.commit()

    return redirect(url_for(
        'project_detail',
        project_id=project_id
    ))

# Initialize Database
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)