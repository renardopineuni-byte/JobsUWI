from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from models.user import User, Employer, Student, Employee
from extensions import db

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('presenter_bp.loadDashboard'))
        else:
            flash('Login failed. Check your username and password.')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        role = request.form.get('role')
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Username already exists.')
        else:
            if role == 'employer':
                new_user = Employer(username=username, password=password, email=email)
            elif role == 'student':
                new_user = Student(username=username, password=password, email=email)
            elif role == 'employee':
                new_user = Employee(username=username, password=password, email=email)
            else:
                new_user = User(username=username, password=password, role=role)
                
            db.session.add(new_user)
            db.session.commit()
            flash('Account created! You can now login.')
            return redirect(url_for('auth_bp.login'))
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('presenter_bp.loadJobListings'))
