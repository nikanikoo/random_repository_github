from flask import Flask, render_template, request, redirect, url_for, session
import requests
import random
import os
import time
import datetime
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

def get_repositories():
    try:
        headers = {
            'User-Agent': 'RandomRepoApp/1.0',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Priority: 1. Logged-in user token, 2. System-wide GITHUB_TOKEN
        token = session.get('access_token') or GITHUB_TOKEN
        if token:
            headers['Authorization'] = f'token {token}'
            
        start_date = datetime.date(2008, 1, 1)
        end_date = datetime.date.today()
        time_between = end_date - start_date
        random_days = random.randrange(time_between.days)
        random_date = start_date + datetime.timedelta(days=random_days)
        
        random_page = random.randint(1, 5)
        
        sort_options = ['stars', 'forks', 'updated', '']
        random_sort = random.choice(sort_options)
        random_order = random.choice(['asc', 'desc'])
        search_query = f'stars:>=0+created:{random_date}'
        search_url = f'https://api.github.com/search/repositories?q={search_query}&per_page=100&page={random_page}'
        
        if random_sort:
            search_url += f'&sort={random_sort}&order={random_order}'
        
        response = requests.get(search_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('items', [])
            
        return None
    except Exception as e:
        print(f"Error fetching repositories: {e}")
        return None

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
    stars = random_repo.get('stargazers_count', 0)
    language = random_repo.get('language', 'Unknown')
    
    # Format dates for the UI
    updated_at = random_repo.get('updated_at', '')
    if updated_at:
        updated_at = updated_at.split('T')[0]
        
    created_at = random_repo.get('created_at', '')
    if created_at:
        created_at = created_at.split('T')[0]
    
    return render_template('index.html', 
                         repo_url=repo_url, 
                         repo_name=repo_name, 
                         repo_description=repo_description,
                         stars=stars,
                         language=language,
                         updated_at=updated_at,
                         created_at=created_at,
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
