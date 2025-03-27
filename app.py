import os
import uuid
from werkzeug.utils import secure_filename
from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from supabase import create_client, Client
import json

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max upload size
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'apng'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# User model
class User(UserMixin):
    def __init__(self, id, email, avatar_url=None, password=None):
        self.id = id
        self.email = email
        self.avatar_url = avatar_url
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    try:
        # Instead of querying a users table, use the auth.getUser function
        # to get user info directly from Supabase Auth
        if 'access_token' in session:
            # Try to get user info using the access token
            user = supabase.auth.get_user(session['access_token']).user
            if user and user.id == user_id:
                # Get user metadata for avatar
                avatar_url = None
                try:
                    response = supabase.table('user_profiles').select('*').eq('user_id', user_id).execute()
                    if response.data and len(response.data) > 0:
                        avatar_url = response.data[0].get('avatar_url')
                except Exception as e:
                    print(f"Error fetching user profile: {str(e)}")
                
                return User(
                    id=user.id,
                    email=user.email,
                    avatar_url=avatar_url
                )
        return None
    except Exception as e:
        # If there's an error (like an expired token), return None
        print(f"Error loading user: {str(e)}")
        return None

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            # Register user with Supabase Auth
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if response.user:
                # Create user profile entry
                supabase.table('user_profiles').insert({
                    'user_id': response.user.id,
                    'email': email,
                    'avatar_url': None
                }).execute()
                
                flash('Registration successful! Please check your email to confirm your account.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Registration failed.', 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
        
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            # Authenticate with Supabase
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                # Get user avatar if exists
                avatar_url = None
                try:
                    profile_response = supabase.table('user_profiles').select('*').eq('user_id', response.user.id).execute()
                    if profile_response.data and len(profile_response.data) > 0:
                        avatar_url = profile_response.data[0].get('avatar_url')
                    else:
                        # Create profile if it doesn't exist
                        supabase.table('user_profiles').insert({
                            'user_id': response.user.id,
                            'email': email,
                            'avatar_url': None
                        }).execute()
                except Exception as e:
                    print(f"Error with user profile: {str(e)}")
                
                # Create a User object
                user = User(
                    id=response.user.id,
                    email=response.user.email,
                    avatar_url=avatar_url
                )
                
                # Log in the user
                login_user(user)
                
                # Store JWT in session for API calls
                session['access_token'] = response.session.access_token
                
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials.', 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    # Sign out from Supabase
    supabase.auth.sign_out()
    
    # Clear session
    session.pop('access_token', None)
    
    # Log out from Flask-Login
    logout_user()
    
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('dashboard', _anchor='settings-content'))
    
    file = request.files['avatar']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('dashboard', _anchor='settings-content'))
    
    if file and allowed_file(file.filename):
        try:
            # Generate a unique filename
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower()
            new_filename = f"{uuid.uuid4().hex}.{ext}"
            
            # Save locally temporarily
            local_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            file.save(local_path)
            
            # Upload to Supabase Storage
            with open(local_path, 'rb') as f:
                file_path = f"avatars/{current_user.id}/{new_filename}"
                supabase.storage.from_('user_files').upload(file_path, f)
            
            # Get public URL
            file_url = supabase.storage.from_('user_files').get_public_url(file_path)
            
            # Update user profile with avatar URL
            supabase.table('user_profiles').update({
                'avatar_url': file_url
            }).eq('user_id', current_user.id).execute()
            
            # Remove temporary local file
            os.remove(local_path)
            
            # Update current user object
            current_user.avatar_url = file_url
            
            flash('Avatar uploaded successfully!', 'success')
        except Exception as e:
            flash(f'Error uploading avatar: {str(e)}', 'danger')
    else:
        flash('Invalid file type. Please upload a PNG, JPG, GIF, or APNG file.', 'danger')
    
    return redirect(url_for('dashboard', _anchor='settings-content'))

if __name__ == '__main__':
    app.run(debug=True) 