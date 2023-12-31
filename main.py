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


with app.app_context():
    app.config['SECRET_KEY'] = 'any-secret-key-you-choose'     
    # Define models
    class User(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(20), unique=True, nullable=False)#email
        display_name=db.Column(db.String(20), nullable=False)#display name
        password = db.Column(db.String(60), nullable=False)
        v= db.Column(db.Integer, default=False)
        profile_picture = db.Column(db.String, nullable=True)
        #for producer
        purpose = db.Column(db.String(20), nullable=True)
        team_size=db.Column(db.Integer, nullable=True)
        #common
        phone_no = db.Column(db.Integer, nullable=True)
        #for professional
        experience = db.Column(db.String(20), nullable=True)
        occupation = db.Column(db.String(100), nullable=True)
        skills = db.Column(db.String(255), nullable=True)
        description = db.Column(db.Text, nullable=True)

    class Job(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(100), nullable=False)
        description = db.Column(db.Text, nullable=False)
        pay_grade = db.Column(db.String(20), nullable=False)
        producer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        producer = db.relationship('User', backref='jobs', lazy=True)

    db.create_all()

    # Flask-Login configuration
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))


    app.config['SECRET_KEY'] = 'any-secret-key-you-choose'
    # Routes
    @app.route('/')
    def index():
        return render_template('index.html')


    @app.route('/login')
    def login():
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
        
        if User.query.filter_by(username=user_email).first():
            user=User.query.filter_by(username=user_email).first()
            login_user(user)
            if user.v == 1 or user.v=="1":
                return redirect(url_for('producer_dashboard'))
            elif user.v == 0 or user.v=="0":
                return redirect(url_for('professional_dashboard'))
        return redirect(url_for('welcome'))

    @app.route('/welcome')
    def welcome():
        return render_template('welcome.html',user_name=session['user_name'])
    
    @app.route('/user_type')
    def user_type():
        return render_template('user_type.html')

    @app.route('/save_image', methods=['POST'])
    def save_image():
        if request.method == 'POST': 
            avatar = request.files['image']
            user_email=session.get("user_email")
            if not os.path.exists(f'static/user_data/{user_email}'):
                os.mkdir(f'static/user_data/{user_email}')
            image_url = f'static/user_data/{user_email}/{avatar.filename}'
            session['image_url'] = image_url
            avatar.save(image_url)
            data = request.form  # Assuming data is sent as JSON
            v = data.get('v')
            session['user_type']=v
            return jsonify({'image_url': image_url})


    @app.route("/login_successful",methods=['POST'])
    def login_successful():
        if request.method == 'POST':
            username=session.get("user_email")
            display_name=request.form.get('username')
            password=request.form.get('password')
            v=session.get('user_type')
            user=User.query.filter_by(username=username).first()
            if (user):
                flash('Username already exists', 'danger')
                
            else:
                user=User(username=username,display_name=display_name,password=password,v=v,profile_picture=session.get('image_url'))
                db.session.add(user)
                db.session.commit()
                flash('Account created successfully!', 'success')
                if v == 1 or v=="1":
                    login_user(user)
                    return redirect(url_for('producer_details'))
                elif v == 0 or v=="0":
                    login_user(user)
                    return redirect(url_for('professional_details'))
            
        pass
    
    
    @app.route("/producer_details",methods=['GET','POST'])
    @login_required
    def producer_details():
        if request.method == 'POST':
            user=current_user
            user.phone_no=request.form.get('phoneNumber')
            user.purpose=request.form.get('purpose')
            user.team_size=request.form.get('teamSize')
            db.session.commit()
            return redirect(url_for('producer_dashboard'))
        return render_template('producer_details.html')
    
    @app.route("/professional_details",methods=['GET','POST'])
    @login_required
    def professional_details():
        if request.method == 'POST':
            user=current_user
            user.experience=request.form.get('Experience')
            user.phone_no=request.form.get('phoneNumber')
            user.occupation=request.form.get('occupation')
            user.skills=request.form.get('skills')
            user.description=request.form.get('description')
            db.session.commit()
            return redirect(url_for('professional_dashboard'))
        return render_template('professional_details.html')

    @app.route('/professional_dashboard')
    @login_required
    def professional_dashboard():
        return render_template('professional_dashboard.html')
    
    @app.route('/producer_dashboard')
    @login_required
    def producer_dashboard():
        return render_template('producer_dashboard.html')

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
