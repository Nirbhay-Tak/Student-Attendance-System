from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import date
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'secret123')

base_dir = os.path.abspath(os.path.dirname(__file__))
database_path = os.path.join(base_dir, 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + database_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    attendances = db.relationship('Attendance', backref='student', lazy=True)


class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(250))
    attendances = db.relationship('Attendance', backref='class_ref', lazy=True)


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(20), nullable=False)


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            if user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            return redirect(url_for('student_dashboard'))

        return render_template('login.html', error='Invalid username or password.')

    return render_template('login.html')


@app.route('/teacher')
def teacher_dashboard():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))

    records = Attendance.query.order_by(Attendance.date.desc()).all()
    classes = Class.query.order_by(Class.class_name).all()
    return render_template('teacher_dashboard.html', records=records, classes=classes)


@app.route('/student')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    student_id = session.get('user_id')
    records = Attendance.query.filter_by(student_id=student_id).order_by(Attendance.date.desc()).all()
    total = len(records)
    present = sum(1 for record in records if record.status == 'Present')
    percentage = round((present / total) * 100, 1) if total else 0
    return render_template('student_dashboard.html', records=records, percentage=percentage)


@app.route('/take_attendance', methods=['GET', 'POST'])
def take_attendance():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))

    classes = Class.query.order_by(Class.class_name).all()
    selected_class_id = request.args.get('class_id', type=int)
    selected_class = None
    if selected_class_id:
        selected_class = Class.query.get(selected_class_id)
    if not selected_class and classes:
        selected_class = classes[0]

    students = User.query.filter_by(role='student').order_by(User.username).all()

    if request.method == 'POST':
        class_id = int(request.form['class_id'])
        for student in students:
            status = request.form.get(f'status_{student.id}', 'Absent')
            db.session.add(Attendance(student_id=student.id, class_id=class_id, date=date.today(), status=status))
        db.session.commit()
        return redirect(url_for('teacher_dashboard'))

    return render_template('take_attendance.html', classes=classes, selected_class=selected_class, students=students)


@app.route('/create_class', methods=['GET', 'POST'])
def create_class():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))

    if request.method == 'POST':
        class_name = request.form['class_name'].strip()
        subject = request.form['subject'].strip()
        description = request.form['description'].strip()

        db.session.add(Class(class_name=class_name, subject=subject, description=description))
        db.session.commit()
        return redirect(url_for('teacher_dashboard'))

    return render_template('create_class.html')


@app.route('/delete_attendance/<int:attendance_id>')
def delete_attendance(attendance_id):
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))

    record = Attendance.query.get_or_404(attendance_id)
    db.session.delete(record)
    db.session.commit()
    return redirect(url_for('teacher_dashboard'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


def seed_data():
    if not User.query.filter_by(role='teacher').first():
        db.session.add(User(username='teacher1', password='123', role='teacher'))

    if User.query.filter_by(role='student').count() == 0:
        for number in range(101, 116):
            db.session.add(User(username=str(number), password='123', role='student'))

    if Class.query.count() == 0:
        db.session.add(Class(class_name='Math 101', subject='Mathematics', description='Basic math concepts'))
        db.session.add(Class(class_name='English 201', subject='English', description='Reading and writing practice'))
        db.session.add(Class(class_name='Science 301', subject='Science', description='Fundamentals of science'))

    db.session.commit()

    if Attendance.query.count() == 0:
        sample_students = User.query.filter_by(role='student').limit(5).all()
        sample_class = Class.query.first()
        for student in sample_students:
            db.session.add(Attendance(student_id=student.id, class_id=sample_class.id, date=date.today(), status='Present'))
        db.session.commit()


with app.app_context():
    db.create_all()
    seed_data()


if __name__ == '__main__':
    app.run(debug=True)
