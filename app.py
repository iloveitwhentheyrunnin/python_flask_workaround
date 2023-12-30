from flask import Flask, redirect, render_template, session, url_for, request
from flask_assets import Bundle, Environment
from flask_scss import Scss
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt 
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


app = Flask(__name__, static_url_path='/static', template_folder='templates')

app.secret_key = 'your-secret-key'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'flask_users'

mysql = MySQL(app)

js = Bundle('home.js', 'page1.js', output='gen/main.js')

assets = Environment(app)
bcrypt = Bcrypt(app) 

assets.register('main_js', js)

@app.route("/")
def home():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    else:
        return render_template('index.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        pwd = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute(f"select username, password from tbl_users where username = '{username}'")
        user = cur.fetchone()
        cur.close()

        #check the pass hash
        if user and check_password_hash(user[1], pwd):
            session['username'] = user[0]
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid credentials.')
    
    return render_template('login.html')

@app.route("/logout")
def logout():
    session.clear()
    return redirect('/')

@app.route("/register", methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        pwd = request.form['password']
        
        # Hash the password
        hashed_password = generate_password_hash(pwd, method='pbkdf2:sha256')
        
        # Set Registering Date
        now = datetime.now()
        formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')

        cur = mysql.connection.cursor()
        cur.execute(f"insert into tbl_users (username, password, join_date) values ('{username}', '{hashed_password}', '{formatted_date}')")
        mysql.connection.commit()
        cur.close()
        
        return redirect(url_for('login'))
    
    return render_template('register.html')
        
if __name__ == '__main__':
    app.run(debug=True,  use_reloader=False) # avoid double compilation