from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=True)  # Make email nullable for students who use username
    username = db.Column(db.String(120), unique=True, nullable=True)  # For students
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    # Additional fields for advisors
    school_name = db.Column(db.String(120), nullable=True)
    subjects = db.Column(db.String(255), nullable=True)  # Comma-separated
    phone = db.Column(db.String(20), nullable=True)
    home_address = db.Column(db.String(255), nullable=True)
    approved = db.Column(db.Boolean, nullable=False, default=False)
    rejected = db.Column(db.Boolean, nullable=False, default=False)
    registration_rule = db.Column(db.String(120), nullable=True)
    student_profile = db.relationship('Student', backref='user', uselist=False)
    notifications = db.relationship('Notification', backref='user', lazy=True)

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    form_level = db.Column(db.String(10), nullable=False)
    combination = db.Column(db.String(20), nullable=False)
    attendance_rate = db.Column(db.Float, nullable=False, default=0.0)
    prediction = db.Column(db.String(20), nullable=False, default='Average')
    risk_level = db.Column(db.String(10), nullable=False, default='average')
    alerts = db.relationship('Alert', backref='student', lazy=True)
    results = db.relationship('Result', backref='student', lazy=True)

class Result(db.Model):
    __tablename__ = 'results'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    subject = db.Column(db.String(80), nullable=False)
    score = db.Column(db.Float, nullable=False)
    assessment_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    message = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, nullable=False, default=False)
