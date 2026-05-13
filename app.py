from flask import Flask, render_template, request, redirect, url_for, session
import requests
import random
import os
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key_for_dev')

# GitHub OAuth Configuration
GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')

# Configuration
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')  # System-wide token (optional)
CACHE_TIMEOUT = 1800  # 30 minutes

# Simple cache
cache = {
    'repositories': [],
    'last_updated': 0
}

def get_repositories():
    current_time = time.time()
    
    # If cache is valid, return it
    if cache['repositories'] and (current_time - cache['last_updated'] < CACHE_TIMEOUT):
        return cache['repositories']
    
    try:
        headers = {'User-Agent': 'RandomRepoApp/1.0'}
        
        # Priority: 1. Logged-in user token, 2. System-wide GITHUB_TOKEN
        token = session.get('access_token') or GITHUB_TOKEN
        if token:
            headers['Authorization'] = f'token {token}'
            
        random_since = random.randint(1, 100000000)
        
        response = requests.get(
            f'https://api.github.com/repositories?since={random_since}', 
            headers=headers, 
            timeout=10
        )
        
        if response.status_code == 200:
            repos = response.json()
            if repos:
                cache['repositories'] = repos
                cache['last_updated'] = current_time
                return cache['repositories']
        
        if cache['repositories']:
            return cache['repositories']
            
        response = requests.get('https://api.github.com/repositories', headers=headers, timeout=10)
        if response.status_code == 200:
            cache['repositories'] = response.json()
            cache['last_updated'] = current_time
            return cache['repositories']
            
        return None
    except Exception:
        return cache['repositories'] if cache['repositories'] else None

@app.route('/')
def index():
    repositories = get_repositories()
    
    user_info = None
    if 'access_token' in session:
        # Fetch user info if logged in
        headers = {'Authorization': f"token {session['access_token']}", 'User-Agent': 'RandomRepoApp/1.0'}
        user_res = requests.get('https://api.github.com/user', headers=headers)
        if user_res.status_code == 200:
            user_info = user_res.json()
    
    if not repositories:
        return "GitHub API rate limit reached. Please log in with GitHub to continue.", 503

    random_repo = random.choice(repositories)
    repo_url = random_repo['html_url']
    repo_name = random_repo['full_name']
    repo_description = random_repo.get('description', 'No description available.')
    
    return render_template('index.html', 
                         repo_url=repo_url, 
                         repo_name=repo_name, 
                         repo_description=repo_description,
                         user=user_info)

@app.route('/login')
def login():
    if not GITHUB_CLIENT_ID:
        return "GitHub OAuth is not configured. Please set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.", 500
    
    return redirect(f'https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo')

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "Authorization failed.", 400
    
    # Exchange code for access token
    response = requests.post(
        'https://github.com/login/oauth/access_token',
        data={
            'client_id': GITHUB_CLIENT_ID,
            'client_secret': GITHUB_CLIENT_SECRET,
            'code': code
        },
        headers={'Accept': 'application/json'}
    )
    
    if response.status_code == 200:
        session['access_token'] = response.json().get('access_token')
        return redirect(url_for('index'))
    
    return "Failed to get access token.", 500

@app.route('/logout')
def logout():
    session.pop('access_token', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=False)
