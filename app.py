from flask import Flask, render_template
from flask_assets import Bundle, Environment

app = Flask(__name__, static_url_path='/static')

js = Bundle('home.js', 'page1.js', output='gen/main.js')
assets = Environment(app)
assets.register('main_js', js)

@app.route("/")
def home():
    return render_template('index.html')