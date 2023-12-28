# app.py

from flask import Flask, render_template, request, redirect, url_for, flash, session,request,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)

load_dotenv(dotenv_path='.env')

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

appConf={
    "client_id": os.getenv('CLIENT_ID'),
    "client_secret": os.getenv('CLIENT_SECRET'),
    "redirect_uri": "http://127.0.0.1:5000/callback",
    "metadata_url": "https://accounts.google.com/.well-known/openid-configuration"
}
oauth=OAuth(app)

myApp=oauth.register("retrocraft_hub",
               client_id=appConf["client_id"],
               client_secret=appConf["client_secret"],
               server_metadata_url=appConf["metadata_url"],
               client_kwargs={"scope": "email profile"}
               )

AUTHLIB_INSECURE_TRANSPORT=True

# Define models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    is_producer = db.Column(db.Boolean, default=False)
    profile_picture = db.Column(db.String(20), nullable=False, default='default.jpg')


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    pay_grade = db.Column(db.String(20), nullable=False)
    producer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    producer = db.relationship('User', backref='jobs', lazy=True)


# Flask-Login configuration
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/google_login')
def google_login():
     return oauth.retrocraft_hub.authorize_redirect(redirect_uri=url_for('callback', _external=True), scope=myApp.client_kwargs['scope'])

@app.route('/callback')
def callback():
    # Exchange the authorization code for an access token and a refresh token
    token = myApp.authorize_access_token()
    session['token'] = token

    # Fetch user information using the obtained access token
    user_info = myApp.get('https://www.googleapis.com/oauth2/v2/userinfo')

    # Access user's name and email
    user_name = user_info.json().get('name')
    user_email = user_info.json().get('email')

    # Do something with user_name and user_email, such as storing them in the session
    session['user_name'] = user_name
    session['user_email'] = user_email
    ''' user=User.query.filter_by(username=user_email).first()
    if user is None:
        user=User(username=user_email, password='password')
        db.session.add(user)
        db.session.commit()
    login_user(user) '''
    return redirect(url_for('welcome'))

@app.route('/welcome')
def welcome():
    return render_template('welcome.html',user_name=session['user_name'])


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Handle signup logic here
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Handle login logic here
        flash('Login successful!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/next', methods=['GET', 'POST'])
def next():
    if request.method == 'POST':
        body = request.json
        v=body["data"]
        print(v)
        

@app.route('/producer')
def producer():
    
    user_type="producer"
    session['user_type']=user_type
    
    
    return render_template('producer.html')

@app.route('/save_image', methods=['POST'])
def save_image():
    if request.method == 'POST':
        avatar = request.files['image']
        image_url = f'static/assets/img/{avatar.filename}'
        avatar.save(image_url)
        return jsonify({'image_url': image_url})

       

@app.route('/professional')
def professional():
    user_type="professional"
    session['user_type']=user_type
    
    
    return render_template('professional.html')

@app.route('/job/<int:job_id>')
def job(job_id):
    job = Job.query.get_or_404(job_id)
    return render_template('job.html', job=job)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
