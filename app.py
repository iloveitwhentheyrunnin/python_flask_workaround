from flask import Flask, abort, redirect, render_template, session, url_for, request
from flask_assets import Bundle, Environment
from flask_scss import Scss
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt 
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

app = Flask(__name__, static_url_path='/static', template_folder='templates')

app.secret_key = 'your-secret-key'

# Configuring connection to db
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'flask_users'

mysql = MySQL(app)

# Compiling JS
js = Bundle('home.js', 'page1.js', output='gen/main.js')

assets = Environment(app)
bcrypt = Bcrypt(app) 

assets.register('main_js', js)


# Middleware to manage admin access 
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in session and session['role'] == 'admin':
            return f(*args, **kwargs)
        else:
            abort(403)  # Forbidden
    return decorated_function

# Middleware to manage authenticated users access
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in session:
            return f(*args, **kwargs)
        else:
            abort(401)  # Unauthorized
    return decorated_function

# a little function to retrieve tasks 
def get_tasks_from_database():
    user_identifier = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, user_id, task_desc, is_done FROM tbl_tasks WHERE is_done = false and user_id = %s", (user_identifier,))
    tasks_data = cur.fetchall()
    cur.close()
            
    tasks = []
    
    for task_data in tasks_data:
        task = Task(id=task_data[0], user_id=task_data[1], task_desc=task_data[2], is_done=task_data[3])
        tasks.append(task)
    
    return tasks

# Getting all the users 
def get_users_from_database():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username, join_date, role FROM tbl_users")
    users_data = cur.fetchall()
    cur.close()
            
    users = []
    
    # just a little practice of a dict :)
    for user_data in users_data:
        user = {
            'id': user_data[0],
            'username': user_data[1],
            'join_date': user_data[2],
            'role': user_data[3],
        }
        users.append(user)

    return users

# Home Page 
@app.route("/")
def home():
    if 'username' in session:
        tasks = get_tasks_from_database()
        return render_template('index.html', username=session['username'], role=session['role'], tasks = tasks)
    else:
        return render_template('index.html')

# Connecting a registered account
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        pwd = request.form['password']
        
        cur = mysql.connection.cursor()
        # a little binding to prevent from injections
        cur.execute(f"select username, password, id, role from tbl_users where username = %s",({username}))
        user = cur.fetchone()
        cur.close()

        #check the pass hash
        if user and check_password_hash(user[1], pwd):
            session['username'] = user[0]
            session['user_id'] = user[2]
            session['role'] = user [3]
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid credentials.')
    
    return render_template('login.html')

# Disconnecting
@app.route("/logout")
def logout():
    session.clear()
    return redirect('/')

# Creating a user account
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
    def __init__(self, user_id, task_desc, is_done=False, id=None):
        self.user_id = user_id
        self.task_desc = task_desc
        self.is_done = is_done
        self.id = id

    def write_in_db(self):
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO tbl_tasks (user_id, task_desc, is_done) VALUES (%s, %s, %s)",
                    (self.user_id, self.task_desc, self.is_done))
        mysql.connection.commit()
        cur.close()

# Create a task
@app.route('/create_task', methods=['POST'])
@login_required
def create_task():
    if request.method == 'POST':
        user_id = session['user_id']
        task_desc = request.form.get('task_desc')
        # Check if user_id is valid 
        if not user_id or not task_desc:
            return redirect(url_for('home', error='Invalid input'))
        
        new_task = Task(user_id=user_id, task_desc=task_desc,id=None)

        new_task.write_in_db()
        
        return redirect(url_for('home', success='Task Added'))

# Editing a task
@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, task_desc, user_id FROM tbl_tasks WHERE id = %s", (task_id,))
    task_data = cur.fetchone()
    
    if not task_data:
        cur.close()
        return redirect(url_for('home'))

    # Check if the task belongs to the current user
    if task_data[2] != session['user_id']:
        cur.close()
        return redirect(url_for('home'))

    if request.method == 'POST':
        new_task_desc = request.form.get('new_task_desc')
        cur.execute("UPDATE tbl_tasks SET task_desc = %s WHERE id = %s", (new_task_desc, task_id))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('home'))

    cur.close()
    return render_template('edit_task.html', task=task_data)

# Delete a task
@app.route('/delete_task/<int:task_id>', methods=['GET'])
@login_required
def delete_task(task_id):
    cur = mysql.connection.cursor()

    # Check if the task exists and belongs to the current user
    cur.execute("SELECT user_id FROM tbl_tasks WHERE id = %s", (task_id,))
    task_owner_id = cur.fetchone()

    if not task_owner_id or task_owner_id[0] != session.get('user_id'):
        cur.close()
        return redirect(url_for('home'))

    cur.execute("DELETE FROM tbl_tasks WHERE id = %s", (task_id,))
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('home'))

# Access to admin dashboard
@app.route('/admin/dashboard')
@admin_required # my little middleware function
def admin_dashboard():
    users = get_users_from_database()
    return render_template('admin_dashboard.html', users=users)


if __name__ == '__main__':
    app.run(debug=True,  use_reloader=False) # avoid double compilation