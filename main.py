from flask import Flask, render_template, request, redirect, url_for, flash, session,request,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
from flask_socketio import SocketIO, emit,Namespace,join_room,leave_room


app = Flask(__name__)
socketio = SocketIO(app)

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
        pricing1 = db.Column(db.Integer, nullable=True)
        pricing2 = db.Column(db.Integer, nullable=True)
        pricing3 = db.Column(db.Integer, nullable=True)

    class Brief(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        project_title = db.Column(db.String(100),unique=True ,nullable=False)
        project_category = db.Column(db.String(100), nullable=False)
        project_description = db.Column(db.Text, nullable=False)
        project_budget = db.Column(db.Integer, nullable=False)
        budget_flexible = db.Column(db.String(10), nullable=False)
        project_timing = db.Column(db.String(100), nullable=False)
        producer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        producer = db.relationship('User', backref=db.backref('briefs', lazy=True))

    class Job(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        plan=db.Column(db.String(100), nullable=False)
        producer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        professional_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        producer = db.relationship('User', foreign_keys=[producer_id])
        professional = db.relationship('User', foreign_keys=[professional_id])
        
    class Brief_Professional(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        brief_id = db.Column(db.Integer, db.ForeignKey('brief.id'), nullable=False)
        professional_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        brief = db.relationship('Brief', backref=db.backref('brief_professionals', lazy=True))
        professional = db.relationship('User', backref=db.backref('brief_professionals', lazy=True))
        accepted=db.Column(db.Integer, default=False) #0 for pending 1 for not accepted, 2 for accepted
    
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
        
        if User.query.filter_by(username=user_email).first():
            user=User.query.filter_by(username=user_email).first()
            login_user(user)

            if user.v == 1 or user.v=="1":
                return redirect(url_for('producer_dashboard',user_id=user.id))
            elif user.v == 0 or user.v=="0":
                return redirect(url_for('professional_dashboard',user_id=user.id))
        return redirect(url_for('welcome', user_name=user_name ,user_email=user_email))

    @app.route('/welcome')
    def welcome():
        user_email = request.args.get('user_email', 'Default Email')
        user_name = request.args.get('user_name', 'Default Name')
        return render_template('welcome.html', user_name=user_name, user_email=user_email)
    
    @app.route('/user_type')
    def user_type():
        user_email = request.args.get('user_email', 'Default Email')
        return render_template('user_type.html', user_email=user_email)

    @app.route('/save_image', methods=['POST'])
    def save_image():
        if request.method == 'POST':
            user_email=request.args.get('user_email', 'Default Email')
            avatar = request.files['image']
            if not os.path.exists(f'static/user_data/{user_email}'):
                os.mkdir(f'static/user_data/{user_email}')
            image_url = f'static/user_data/{user_email}/{avatar.filename}'
            session['image_url'] = image_url
            avatar.save(image_url)
            current_user.profile_picture=image_url
            return jsonify({'user_email': user_email, 'image_url': image_url})


    @app.route("/login_successful",methods=['POST'])
    def login_successful():
        if request.method == 'POST':    
            v=request.args.get('v', 'Default Value')
            user_email=request.args.get('user_email', 'Default Email')
            display_name=request.form.get('username')
            password=request.form.get('password')
            user=User.query.filter_by(username=user_email).first()
            if (user):
                flash('Username already exists', 'danger')
                
            else:
                user=User(username=user_email,display_name=display_name,password=password,v=v,profile_picture=session.pop('image_url', None))
                session.pop('image_url', None)
                db.session.add(user)
                db.session.commit()
        
                
                flash('Account created successfully!', 'success')
                if v == 1 or v=="1":
                    login_user(user)
                    return redirect(url_for('producer_details',user_id=user.id))
                elif v == 0 or v=="0":
                    login_user(user)
                    return redirect(url_for('professional_details',user_id=user.id))
                
            
            
        pass
    
    #---Producer------------------------------------------------------------------------------------------------
    @app.route("/producer_details",methods=['GET','POST'])
    @login_required
    def producer_details():
        user_id=request.args.get('user_id', 'Default')
        user=User.query.filter_by(id=user_id).first()
        login_user(user)
        message=request.args.get('message', 'Default')
        if request.method == 'POST':
            current_user.phone_no=request.form.get('phoneNumber')
            current_user.purpose=request.form.get('purpose')
            current_user.team_size=request.form.get('teamSize')
            db.session.commit()
            return redirect(url_for('producer_dashboard',user_id=user_id))
        return render_template('producer_details.html',user_id=user_id)
    
    
    @socketio.on('join_room_event')
    def handle_join_room(data):
        user_id = data.get('user_id')
        join_room(user_id)  # Use join_room within a SocketIO event handler
        pass    
    
    
    @app.route('/producer_dashboard<int:user_id>')
    @login_required
    def producer_dashboard(user_id):
        message=request.args.get('message', 'Default')
        user=User.query.filter_by(id=user_id).first()
        login_user(user)
        professionals_list=User.query.filter_by(v=0).all()
        return render_template('producer_dashboard.html',professionals_list=professionals_list,current_user=current_user, user_id=user_id,message=message)
    
    
    @app.route('/brief_proposal', methods=['GET', 'POST'])
    @login_required
    def brief_proposal():
        user_id=request.args.get('user_id', 'Default')
        user=User.query.filter_by(id=user_id).first()
        login_user(user)
        if request.method == 'POST':
            project_title = request.form.get('project_title')
            project_category = request.form.get('project_category')
            project_description = request.form.get('project_description')
            project_budget = request.form.get('project_budget') 
            budget_flexible=request.form.get('budget_flexible')
            if not budget_flexible == "on":
                budget_flexible="budget not flexible"
            elif budget_flexible == "on":
                budget_flexible="budget flexible"
            project_timing=request.form.get('project_timing')
            brief = Brief(project_title=project_title, project_category=project_category, project_description=project_description, project_budget=project_budget, budget_flexible=budget_flexible, project_timing=project_timing, producer_id=current_user.id)
            db.session.add(brief)
            db.session.commit()
            message="Successfully created your brief, professionals will contact you soon"
            
            return redirect(url_for('producer_dashboard',user_id=user_id,message=message))
        return render_template('brief_proposal.html',user_id=user_id)    
    
    
    #---Professional------------------------------------------------------------------------------------------------

    @app.route("/professional_details",methods=['GET','POST'])
    @login_required
    def professional_details():
        user_id=request.args.get('user_id', 'Default')
        user=User.query.filter_by(id=user_id).first()
        login_user(user)
        if request.method == 'POST':
            current_user.experience=request.form.get('Experience')
            current_user.phone_no=request.form.get('phoneNumber')
            current_user.occupation=request.form.get('occupation')
            current_user.skills=request.form.get('skills')
            current_user.description=request.form.get('description')
            current_user.pricing1=request.form.get('Pricing1')
            current_user.pricing2=request.form.get('Pricing2')
            current_user.pricing3=request.form.get('Pricing3')
            db.session.commit()
            
            
            return redirect(url_for('professional_dashboard',user_id=user_id))
        return render_template('professional_details.html',user_id=user_id)


    @app.route('/professional_dashboard<int:user_id>')
    @login_required
    def professional_dashboard(user_id):
        user=User.query.filter_by(id=user_id).first()
        login_user(user)
        message=request.args.get('message', 'Default')
        briefs_list=Brief.query.all()
        producer_name=[]
        for brief in briefs_list:
            producer_name.append(User.query.filter_by(id=brief.producer_id).first().display_name)
            brief_professional=Brief_Professional.query.filter_by(brief_id=brief.id,professional_id=user_id).first()
            if brief_professional:
                briefs_list.remove(brief)
        return render_template('professional_dashboard.html',briefs_list=briefs_list,current_user=current_user,user_id=user_id,producer_name=producer_name,message=message)
        
    
    @app.route('/professional_pp_for_himself<int:user_id>')
    @login_required
    def professional_pp_for_himself(user_id):
        user=User.query.filter_by(id=user_id).first()
        login_user(user)
        professional=User.query.filter_by(id=user_id).first()
        return render_template('professional_profile_page_for_himself.html',current_user=current_user,user_id=user_id,professional=professional)
    
    
    @app.route('/apply_for_brief', methods=['GET', 'POST'])    
    @login_required
    def apply_for_brief():
        user_id=request.args.get('user_id', 'Default')
        user=User.query.filter_by(id=user_id).first()
        login_user(user)
        brief_id=request.args.get('brief_id', 'Default')
        
        brief_professional=Brief_Professional(brief_id=brief_id,professional_id=user_id,accepted=0)
        db.session.add(brief_professional)
        db.session.commit()
        
        producer_name=User.query.filter_by(id=Brief.query.filter_by(id=brief_id).first().producer_id).first().display_name
        
        message=f'Successfully applied for the brief, {producer_name} will contact you soon for further details.'
        producer_id=Brief.query.filter_by(id=brief_id).first().producer_id
        
        socketio.emit('application_notification', {'brief_id': brief_id, 'professional_id': user_id},room=producer_id)
        
        return redirect(url_for('professional_dashboard',user_id=user_id,message=message))
        
        
    @app.route('/professional_pp', methods=['GET', 'POST'])
    @login_required
    def professional_pp():
        if request.method == 'GET':
            user_id=request.args.get('user_id', 'Default')
            professional_id=request.args.get('professional_id', 'Default')
            professional=User.query.filter_by(id=professional_id).first()
            professional_jobs=Job.query.filter_by(professional_id=professional_id).all()
            producers=["None"]
            plans=["None"]
        
        ''' if professional_jobs:
            producers.pop(-1)
            plans.pop(-1)
            for job in professional_jobs:
                producer=User.query.filter_by(id=job.producer_id).first()
                producers.append(producer)
                plans.append(job.plan)
            result = dict(zip(producers, plans)) '''
            
       
        if request.method == 'POST':
            data = request.get_json()
            plan = data.get('plan', 'Default')
            user_id = data.get('user_id', 'Default')
            professional_id = data.get('professional_id', 'Default')
            job=Job(plan=plan,producer_id=user_id,professional_id=professional_id)
            professional_name=User.query.filter_by(id=professional_id).first().display_name
            db.session.add(job)
            db.session.commit()
            
            producer_name=User.query.filter_by(id=user_id).first().display_name
            message=f'Successfully booked with artist: {professional_name}'
            
            if plan==1 or plan=="1":
                plan="Basic"
            elif plan==2 or plan=="2":
                plan="Standard"
            else:
                plan="Premium"
                
            socketio.emit('booking_notification', {'plan': plan, 'producer_id': user_id ,'producer_name': producer_name},room=professional_id)

            return redirect(url_for('producer_dashboard',user_id=user_id,message=message))
        
        
        return render_template('professional_profile_page.html',current_user=current_user,professional=professional,user_id=user_id)    
    
    
    @app.route('/job/<int:job_id>')
    def job(job_id):
        #job = Job.query.get_or_404(job_id)
        return render_template('job.html', job=job)


    #---------------------------------------------------------------------------------------------------
      
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        leave_room(user.id)
        return redirect(url_for('index'))


    if __name__ == '__main__':
        socketio.run(app, debug=True)
