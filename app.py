from flask import Flask, render_template, session, url_for, request
from flask_assets import Bundle, Environment
from flask_scss import Scss
from flask_mysqldb import MySQL

app = Flask(__name__, static_url_path='/static', template_folder='templates')

app.secret_key = 'your-secret-key'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'flask_users'

mysql = MySQL(app)

js = Bundle('home.js', 'page1.js', output='gen/main.js')

assets = Environment(app)

assets.register('main_js', js)

@app.route("/")
def home():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    else:
        return render_template('index.html')
    
if __name__ == '__main__':
    app.run(debug=True,  use_reloader=False) #avoid double compilation