from datetime import timedelta
from flask import Flask, abort, render_template, request, redirect, url_for,session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email
import requests
from flask_migrate import Migrate
from sqlalchemy import inspect
from flask_session import Session
import pandas as pd

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app,db)




@app.context_processor
def inject_user():
    print("Current user:", current_user)
    return dict(user=current_user)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'





app.config['SESSION_COOKIE_SECURE'] = False  # True אם האתר רץ על HTTPS בלבד
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = "Lax"  # התאמה לאבטחה
app.config['SESSION_COOKIE_NAME'] = 'flask_session'


app.config['REMEMBER_COOKIE_NAME'] = 'remember_token'
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)  # תוקף של 7 ימים לקוקי
app.config['SESSION_PROTECTION'] = 'strong'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'



class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')



class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


# מודל המשתמש
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="user")  # תיקון השימוש באותיות גדולות


class SiteStats(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    visits = db.Column(db.Integer,default = 0) # counter of visits








@app.route('/')
def home():
    weather_data = None
    error = None
    location = "Tel Aviv"  # מיקום ברירת מחדל
    stats = SiteStats.query.first()

    if stats:
        stats.visits += 1 # add visit
        db.session.commit() # commit change to sitestats db

    print(f"Current user: {current_user}")
    print(f"Is user authenticated: {current_user.is_authenticated}")

    try:
        api_key = 'bd077ed5bf504e238ad72643250201'
        weather_url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={location}&aqi=no"
        response = requests.get(weather_url)
        if response.status_code == 200:
            data = response.json()
            weather_data = {
                "condition": data['current']['condition']['text'],
                "icon": data['current']['condition']['icon'],
                "temp": data['current']['temp_c'],
                "feels_like": data['current']['feelslike_c']
            }
        else:
            error = "Unable to fetch weather data."
    except Exception as e:
        error = f"An error occurred: {e}"

    return render_template('home.html', weather_data=weather_data, error=error , user = current_user)
 

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            print(f"User found: {user.username}")
            login_user(user, remember=True)
            print(f"After login_user: current_user = {current_user}, authenticated = {current_user.is_authenticated}")
            return redirect(url_for('home'))
        else:
            print("Invalid login attempt.")
            return render_template("login.html", form=form, error="Invalid email or password.")
    return render_template('login.html', form=form)

@login_manager.user_loader
def load_user(user_id):
    print(f"Loading user with ID: {user_id}")
    return User.query.get(int(user_id))



@app.after_request
def log_cookies(response):
    print(f"Cookies sent in response: {response.headers.get('Set-Cookie')}")
    print(f"Cookies received in request: {request.cookies}")
    return response




@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()  # יצירת אובייקט הטופס
    if form.validate_on_submit():  # בדיקת תקינות הטופס
        email = form.email.data
        username = form.username.data
        password = form.password.data

        # בדוק אם האימייל כבר קיים
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template("register.html", form=form, error="Email already registered.")
        
        # הוספת משתמש חדש
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template("register.html", form=form)  # העברת הטופס ל-HTML






def get_clothing_recommendation(temp):
    """ המלצות לבוש על סמך הטמפרטורה """
    if temp < 10:
        return "Wear a coat and scarf."
    elif temp < 20:
        return "Consider wearing a sweater."
    else:
        return "T-shirt and shorts are fine."

@app.route('/weather', methods=['GET', 'POST'])
def weather_page():
    weather_data = None
    location = None
    error = None
    alert = None
    clothing_recommendation = None

    if request.method == 'POST':
        location = request.form.get('location')
        api_key = 'bd077ed5bf504e238ad72643250201'
        weather_url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={location}&days=1&alerts=yes"

        try:
            response = requests.get(weather_url)
            if response.status_code == 200:
                data = response.json()

                # נתוני מזג האוויר
                weather_data = {
                    "condition": data['current']['condition']['text'],
                    "icon": data['current']['condition']['icon'],
                    "temp": data['current']['temp_c'],
                    "feels_like": data['current']['feelslike_c'],
                    "humidity": data['current']['humidity'],
                }

                # התראות מזג האוויר
                if data['alerts']['alert']:
                    alert = data['alerts']['alert'][0]['headline']

                # המלצות לבוש
                clothing_recommendation = get_clothing_recommendation(weather_data["temp"])
            else:
                error = f"Failed to fetch weather data for {location}."
        except Exception as e:
            error = f"An error occurred: {e}"

    return render_template(
        'weather.html',
        weather_data=weather_data,
        location=location,
        error=error,
        alert=alert,
        clothing_recommendation=clothing_recommendation
    )

@app.route('/admin', methods=['GET'])
@login_required
def admin_panel():
    if current_user.role != "admin":  # בדיקת תפקיד המשתמש
        abort(403)  # שגיאה אם המשתמש אינו אדמין

    if User.__table__.exists(db.engine):
        users = User.query.all()  # כל המשתמשים
        stats = SiteStats.query.first()  # סטטיסטיקות האתר
    return render_template('admin.html', users=users, stats=stats)

# התנתקות
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


Migrate = Migrate(app,db)

Session(app)


with app.app_context():
    db.create_all()  # ודא שהטבלאות נוצרות
    inspector = inspect(db.engine)
    print("Tables in the database:", inspector.get_table_names())



    
if __name__ == '__main__':
    app.run(debug=True)