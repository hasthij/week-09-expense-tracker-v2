import os
import sqlite3
from dotenv import load_dotenv
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "my secret")  # for session

# Google OAuth Setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

db = sqlite3.connect("expenses.db", check_same_thread=False)
db.row_factory = sqlite3.Row

db.execute("""
CREATE TABLE IF NOT EXISTS tbl_members (
m_id INTEGER PRIMARY KEY AUTOINCREMENT,  
name TEXT NOT NULL UNIQUE,
password TEXT NOT NULL)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS tbl_expenses (
    e_id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    amount INTEGER NOT NULL CHECK (amount >= 0),
    m_id INTEGER NOT NULL REFERENCES tbl_members(m_id))
    """)

def add_user(name, password):
    hashed_pw = generate_password_hash(password)
    db.execute("INSERT INTO tbl_members (m_id, name, password) VALUES (?, ?, ?)", (None, name, hashed_pw))
    db.commit()


@app.route('/')
def home():
    if "user_id" in session:
        totals = db.execute("""
            SELECT tbl_members.name, COALESCE(SUM(tbl_expenses.amount), 0) AS total
            FROM tbl_members
            LEFT JOIN tbl_expenses ON tbl_members.m_id = tbl_expenses.m_id
            GROUP BY tbl_members.name
        """).fetchall()
        return render_template("dashboard.html", totals=totals)
    else:                   
        return "You are not logged in. <a href='/login'>Log in</a>"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":                
        name = request.form["username"]
        pw = request.form["password"]
        user = db.execute(
            "SELECT * FROM tbl_members WHERE name = ?", (name,)
        ).fetchone()

        if user and check_password_hash(user["password"], pw):
            session["user_id"] = user["m_id"]   
            return redirect("/")
        return "Wrong username or password. <a href='/login'>Try again</a>"
    return render_template("login.html")

@app.route('/login/google')
def login_google():
    redirect_uri = url_for('auth_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/callback')
def auth_callback():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    name = user_info.get('name') or user_info.get('email')

    user = db.execute("SELECT * FROM tbl_members WHERE name = ?", (name,)).fetchone()
    if not user:
        add_user(name, "google_sso")
        user = db.execute("SELECT * FROM tbl_members WHERE name = ?", (name,)).fetchone()

    session["user_id"] = user["m_id"]
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":                # the form was submitted
        name = request.form["username"]
        pw = request.form["password"]
        add_user(name, pw)
        return redirect("/login")
    return render_template("register.html")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()                             # take thesession ticket away
    return redirect("/")

@app.route('/expenses')
def expenses():
    members = db.execute("SELECT * FROM tbl_members").fetchall()
    return render_template('expenses.html', members=members)


@app.route('/addMember', methods=['POST'])
def addMember():
    add_user(request.form['name'], "1234")
    return redirect('/expenses')


@app.route('/addExpense', methods=['POST'])
def addExpense():
    db.execute(
        "INSERT INTO tbl_expenses (description, amount, m_id) VALUES (?, ?, ?)",
        (request.form['description'], request.form['amount'], request.form['m_id']))
    db.commit()
    return redirect('/expenses')


if __name__ == '__main__':
    port = int(os.environ.get("PORT") or os.environ.get("SERVER_PORT") or 14740)
    app.run(host="0.0.0.0", port=port)