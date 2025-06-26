from flask import Flask, render_template, request , jsonify, flash
from math import floor
import os
from flask import Flask, request, flash, render_template, url_for, session, send_file, make_response
import random, string, io
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
import re
import dns.resolver
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import time
import re
from datetime import datetime, timedelta
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ['SECURITY_KEY']
input_data=[]
budget=0
final_list=[]
remaining_budget=0

# MySQL Configuration
app.config['MYSQL_HOST'] = os.environ['MYSQL_HOST']
app.config['MYSQL_USER'] = os.environ['MYSQL_USER']
app.config['MYSQL_PASSWORD'] = os.environ['MYSQL_PASS']
app.config['MYSQL_DB'] = os.environ['MYSQL_DB']
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id, email,f_name,l_name,username):
        self.id = id
        self.email = email
        self.name = f_name+" "+l_name
        self.username = username


# Email Configuration for verification
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ['APP_EMAIL']
app.config['MAIL_PASSWORD'] = os.environ['APP_PASS']
mail = Mail(app)

# Checking if the email is valid or not
def is_email_valid(email):
    # 1. Format check
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if not re.match(pattern, email):
        return (False, "Invalid email format")

    # 2. Check if domain exists (MX record check)
    domain = email.split('@')[1]
    try:
        records = dns.resolver.resolve(domain, 'MX')
        if not records:
            return (False, "Email domain does not exist")
    except Exception:
        return (False, "Email domain not reachable")

    # 3. Check if email already exists in DB
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()

    if user:
        return (False, "Email already registered")

    return (True, "Email is valid and available")


serializer = URLSafeTimedSerializer(app.secret_key)

def check_password_strength(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least 1 lowercase letter"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least 1 uppercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least 1 number"
    
    if not re.search(r'[!@#$%^&*()\-_=+{}\[\]:;"\'<>,.?/~`]', password):
        return False, "Password must contain at least 1 special character"

    return True, "Password is valid"


@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        f_name = request.form['f_name']
        l_name = request.form['l_name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_pass = request.form['confirm_pass']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s OR username = %s", (email, username))
        existing = cursor.fetchone()
        
        email_valid, email_msg = is_email_valid(email)
        if not (email_valid):
            flash(email_msg, "warning")
            return render_template("registration.html")

        pass_valid, pass_msg=check_password_strength(password)
        if not pass_valid:
            flash(pass_msg,"warning")
            return render_template("registration.html")

        if(password!=confirm_pass):
            flash("Password do not match confirm password","warning")
            return render_template("reg.html")
                 
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Insert new user
        cursor.execute(
            "INSERT INTO users (F_NAME, L_NAME, EMAIL, USERNAME, PASSWORD) VALUES (%s, %s, %s, %s, %s)",
            (f_name, l_name, email, username, hashed_password)
        )
        mysql.connection.commit()
        cursor.close()

        return render_template("login.html")

@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, email, f_name, l_name, username FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    return User(user["id"], user["email"],user["f_name"], user["l_name"],user["username"]) if user else None
     
def is_user_blocked(email):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT failed_attempts, is_blocked, blocked_until FROM users WHERE email=%s", (email,))
    result = cursor.fetchone()
    cursor.close()

    if result:
        failed_attempts = result['failed_attempts']
        is_blocked = result['is_blocked']
        block_until = result['blocked_until']

        if is_blocked and block_until:
            if datetime.utcnow() < block_until:
                return True, block_until
            else:
                # Unblock the user
                cursor = mysql.connection.cursor()
                cursor.execute("UPDATE users SET is_blocked=FALSE, failed_attempts=0 WHERE email=%s", (email,))
                mysql.connection.commit()
                cursor.close()
                return False, None
    return False, None

def record_failed_attempt(email):
    # Invalid login: increment failed attempts
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT failed_attempts FROM users WHERE email=%s", (email,))
    result = cursor.fetchone()
    if result:
        attempts = result["failed_attempts"] + 1
        if attempts >= 10:
            block_time = datetime.utcnow() + timedelta(hours=24)
            cursor.execute("UPDATE users SET failed_attempts=%s, is_blocked=TRUE, blocked_until=%s WHERE email=%s",
                            (attempts, block_time, email))
        else:
            cursor.execute("UPDATE users SET failed_attempts=%s WHERE email=%s", (attempts, email))
        mysql.connection.commit()
    cursor.close()


app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)

@app.route('/login', methods=['GET', 'POST'])
def login():
       
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password'] 
        remember = request.form.get('remember') == 'on'  # Get "Remember Me" checkbox

        # Check if user is blocked due to failed login attempts
        is_blocked, block_time = is_user_blocked(email)
        if is_blocked:
            flash(f"Too many failed attempts. Try again after {block_time.strftime('%Y-%m-%d %H:%M:%S')} UTC.", "danger")
            return render_template("login.html")

        
        # Fetch user from DB
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, email, password FROM users WHERE email=%s", (email,))
        user_data = cursor.fetchone()
        cursor.close()

        if user_data and bcrypt.check_password_hash(user_data["password"], password):
            # Log the user in with "remember me" option
            login_user(User(user_data["id"], user_data["email"]), remember=remember)

            # Set session permanent and store pending login data
            session.permanent = True
            session['pending_user_id'] = user_data["id"]
            session['pending_email'] = user_data["email"]  

            input_data=[]
            budget=0
            final_list=[]
            remaining_budget=0
            return render_template('index.html')          
        else:
            # Record failed attempt
            record_failed_attempt(email)
            flash("Invalid credentials!", "danger")

    return render_template("login.html")


@app.route('/reset_pass',methods=['GET','POST'])
def reset_pass():
    if request.method == 'POST':

        email = request.form['email']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if not user:
            flash("Email not registered.", "danger")
            return render_template('reset.html')

        # Generate token
        token = serializer.dumps(email, salt='password-reset')
        link = url_for('reset_password', token=token, _external=True)

        # Send email
        msg = Message("Reset Your Password", sender=os.environ['APP_EMAIL'], recipients=[email])
        msg.body = f"Click this link to reset your password: {link}\nNote: valid for 15 minutes."
        mail.send(msg)

        flash("Reset link sent to your email.", "info")
        return render_template("reset.html")

    return render_template("reset.html")  

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        # Decode the email from token (valid for 15 mins)
        email = serializer.loads(token, salt='password-reset', max_age=900)
    except:
        flash("Invalid or expired reset link.", "danger")
        return render_template('reset.html')

    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form['confirm_pass']

        pass_valid, pass_msg=check_password_strength(new_password)
        if not pass_valid:
            flash(pass_msg,"warning")
            return render_template("reset_pass.html")

        if(new_password!=confirm_password):
            flash("Password do not match confirm password","warning")
            return render_template("reset_pass.html")

        # ✅ Hash password
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')

        # ✅ Update in MySQL
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE users SET password=%s WHERE email=%s", (hashed_password, email))
        mysql.connection.commit()
        cursor.close()

        flash("Your password has been reset. Please login.", "success")
        return render_template('login.html')

    return render_template('reset_pass.html')  # Password form

@app.route('/logout')
@login_required
def logout():
    logout_user()  # 🔑 This ends the session
    flash("Logged out successfully.", "info")
    return render_template("try_opt.html")

@app.route('/')
def home():
    global input_data, budget, final_list,remaining_budget
    print(current_user.is_authenticated)
    if current_user.is_authenticated:
        input_data=[]
        budget=0
        final_list=[]
        remaining_budget=0
        return render_template('index.html')
    return render_template("try_opt.html")

@app.route('/login_page')
def login_page():
    global input_data, budget, final_list,remaining_budget
    print(current_user.is_authenticated)
    if current_user.is_authenticated:
        input_data=[]
        budget=0
        final_list=[]
        remaining_budget=0
        return render_template('index.html')
    return render_template('login.html')

@app.route('/reg_page')
def reg_page():
    return render_template('registration.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/history')
@login_required
def history():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT id, timestamp, budget, spent, savings
        FROM history
        WHERE user_id = %s
        ORDER BY timestamp DESC
    """, (current_user.id,))
    history = cursor.fetchall()
    return render_template('history.html', history=history)

@app.route('/replay/<int:history_id>')
@login_required
def replay(history_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT original_list, optimized_list, budget, spent, savings
        FROM history
        WHERE id = %s AND user_id = %s
    """, (history_id, current_user.id))
    data = cursor.fetchone()

    statistics = {
    "spent": data['spent'],
    "savings": data['savings']
    }
    if not data:
        return "Not Found", 404

    return render_template('index.html',
                           original_list=json.loads(data['original_list']),
                           optimized_list=json.loads(data['optimized_list']),
                           budget=data['budget'],
                           spent=data['spent'],
                           savings=data['savings'],
                           statistics=statistics,
                           from_history=True)


def optimizer():
    global final_list,remaining_budget,input_data
    
    items = input_data.copy()
    items.sort(key=lambda x: x["priority"])

    # Total cost of everything
    total_cost = sum(item["qty"] * item["price"] for item in items)
    print("Total cost of the input list:", total_cost)

    remaining_budget = budget
    final_list=[]

    if total_cost <= budget:
        for item in items:
            item_copy = item.copy()
            item_copy["status"] = "Full"
            final_list.append(item_copy)
        remaining_budget-=total_cost
    else:
        for item in items:
            item_copy = item.copy()
            cost = item["qty"] * item["price"]
            if cost <= remaining_budget:
                item_copy["status"] = "Full"
                final_list.append(item_copy)
                remaining_budget -= cost
            else:
                affordable_qty = min(item["qty"], floor(remaining_budget / item["price"]))
                if affordable_qty > 0:
                    item_copy["qty"] = affordable_qty
                    item_copy["status"] = "Partial"
                    remaining_budget -= affordable_qty * item["price"]
                    final_list.append(item_copy)
                else:
                    item_copy["status"] = "Skipped"
                    item_copy["qty"] = 0
                    final_list.append(item_copy)

                # ✅ Final Output
                print("\nFinal Optimized List:")
                for item in final_list:
                    print(item)

    print("\nStatistics:")
    print("-- Total Spent:", budget - remaining_budget)
    print("-- Savings:",  floor(remaining_budget * 100)/100)

    # Skipped items
    skipped_items = [item["item"] for item in final_list if item["status"] == "Skipped"]
    print("-- Items Skipped:")
    if skipped_items:
        for name in skipped_items:
            print("---->", name)
    else:
        print("----> None")


@app.route('/add_item', methods=['POST'])
def add_item():
    data = request.get_json()
    input_data.append(data)
    print("Received:", data)  
    flash("Item received")
    return jsonify({"received_data": data})

@app.route('/remove_item', methods=['POST'])
def remove_item():
    data = request.get_json()
    item_to_remove = data.get('item')

    global input_data
    input_data = [item for item in input_data if item['item'] != item_to_remove]
    flash("Item removed")
    return jsonify({"updated_data": input_data})

@app.route('/submit', methods=['POST'])
def submit():
    global budget,input_data,final_list
    budget = request.get_json()
    budget=budget['budget']
    optimizer()
    stats = {
        "spent": round(budget - remaining_budget, 2),
        "savings": round(remaining_budget, 2),
        "skipped": [item["item"] for item in final_list if item["status"] == "Skipped"]
    }

     # ✅ Save history only if user is logged in
    if current_user.is_authenticated:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO history (user_id, timestamp, original_list, optimized_list, budget, savings, spent)
            VALUES (%s, %s, %s, %s,%s,%s,%s)
        """, (
            current_user.id,
            datetime.now(),
            json.dumps(input_data),
            json.dumps(final_list),
            budget,
            round(budget - remaining_budget, 2),
            round(remaining_budget, 2)
        ))
        mysql.connection.commit()

    flash("Final optimization complete")
    return jsonify({
        "Final_list": final_list,
        "Statistics": stats
    })


if (__name__ == "__main__"):
    app.run(debug=True)
