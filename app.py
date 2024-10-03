from flask import Flask, render_template
import requests
import random

app = Flask(__name__)

@app.route('/')
def index():
    response = requests.get('https://api.github.com/repositories')
    repositories = response.json()

    random_repo = random.choice(repositories)
    repo_url = random_repo['html_url']
    
    return render_template('index.html', repo_url=repo_url)

if __name__ == '__main__':
    app.run(debug=False)
