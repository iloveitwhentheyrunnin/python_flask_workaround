from flask import Flask, redirect, render_template, session, url_for, request
from flask_assets import Bundle, Environment
from flask_scss import Scss
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt 
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy


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

# a little function to retrieve tasks 
def get_tasks_from_database():
    user_identifier = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, user_id, task_desc, is_done FROM tbl_tasks WHERE is_done = false and user_id = %s", (user_identifier,))
    tasks_data = cur.fetchall()
    print(tasks_data)
    cur.close()
            
    tasks = []
    
    for task_data in tasks_data:
        task = Task(user_id=task_data[1], task_desc=task_data[2], is_done=task_data[3])
        tasks.append(task)
    
    return tasks

@app.route("/")
def home():
    if 'username' in session:
        tasks = get_tasks_from_database()
        return render_template('index.html', username=session['username'], tasks = tasks)
    else:
        return render_template('index.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        pwd = request.form['password']
        
        cur = mysql.connection.cursor()
        # a little binding to prevent from injections
        cur.execute(f"select username, password, id from tbl_users where username = %s",({username}))
        user = cur.fetchone()
        cur.close()

        #check the pass hash
        if user and check_password_hash(user[1], pwd):
            session['username'] = user[0]
            session['user_id'] = user[2]
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
        #same here! a great request safe
        cur.execute("INSERT INTO tbl_users (username, password, join_date) VALUES (%s, %s, %s)", (username, hashed_password, formatted_date))
        mysql.connection.commit()
        cur.close()
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Make it work with a class and a model just to flex a bit and try something different :p
class Task:
    def __init__(self, user_id, task_desc, is_done=False):
        self.user_id = user_id
        self.task_desc = task_desc
        self.is_done = is_done

    def write_in_db(self):
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO tbl_tasks (user_id, task_desc, is_done) VALUES (%s, %s, %s)",
                    (self.user_id, self.task_desc, self.is_done))
        mysql.connection.commit()
        cur.close()

@app.route('/create_task', methods=['POST'])
def create_task():
    if request.method == 'POST':
        user_id = session['user_id']
        task_desc = request.form.get('task_desc')
        # Check if user_id is valid 
        if not user_id or not task_desc:
            return redirect(url_for('home', error='Invalid input'))
        
        new_task = Task(user_id=user_id, task_desc=task_desc)

        new_task.write_in_db()
        
        return redirect(url_for('home', success='Task Added'))
    
if __name__ == '__main__':
    app.run(debug=True,  use_reloader=False) # avoid double compilation