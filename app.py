import sqlite3
from flask import Flask, render_template, request,session,redirect
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "my secret"  # for session

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
            return render_template("dashboard.html")
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
    session.clear()                             # take the ticket away
    return redirect("/")

@app.route('/expenses')
def expenses():
    members = db.execute("SELECT * FROM tbl_members").fetchall()
    return render_template('expenses.html', members=members)


@app.route('/addMember', methods=['POST'])
def addMember():
    db.execute("INSERT INTO tbl_members (name) VALUES (?)", (request.form['name'],))
    db.commit()
    return expenses()


@app.route('/addExpense', methods=['POST'])
def addExpense():
    db.execute(
        "INSERT INTO tbl_expenses (description, amount, m_id) VALUES (?, ?, ?)",
        (request.form['description'], request.form['amount'], request.form['m_id']))
    db.commit()
    return expenses()


if __name__ == '__main__':
    app.run(debug=True)