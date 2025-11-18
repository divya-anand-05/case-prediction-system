from flask import Flask, render_template, request,redirect,url_for,session,flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import subprocess
import os
from datetime import datetime

app = Flask(__name__)


# DATABASE CONFIGURATION

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///history.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
# DATABASE MODEL

class AnalysisHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    situation = db.Column(db.Text, nullable=False)
    positive = db.Column(db.Text)
    negative = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref='analyses')

# Create DB table if not exists
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = (request.form.get("password") or "").strip()

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        # check if username exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
            return redirect(url_for("register"))

        # check if email exists
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return redirect(url_for("register"))

        # Create and save new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)  
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = (request.form.get("username")or "").strip()
        password = request.form.get("password")
        remember = request.form.get("remember") == "on"

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash("Logged in successfully.", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("home"))
        else:
            flash("Invalid username or password.", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    situation = request.form['situation']

    prompt = f"""
    You are an intelligent AI system that predicts outcomes.
    Analyze the following situation and provide:
    - Positive possibilities (good outcomes)
    - Negative possibilities (bad outcomes)
    
    Situation: "{situation}"
    """

    # Run Ollama model
    command = ["ollama", "run", "llama3", prompt]
    result = subprocess.run(command, capture_output=True, text=True)
    ai_output = result.stdout.strip()

    positive_part = ""
    negative_part = ""
    current = None

    # Split AI result
    for line in ai_output.splitlines():
        lower = line.lower()
        if "positive" in lower:
            current = "pos"
            continue
        elif "negative" in lower:
            current = "neg"
            continue

        if current == "pos":
            positive_part += line + "\n"
        elif current == "neg":
            negative_part += line + "\n"

    positive_final = positive_part.strip()
    negative_final = negative_part.strip()


    # SAVE TO DATABASE

    entry = AnalysisHistory(
        situation=situation,
        positive=positive_final,
        negative=negative_final,
        user_id=current_user.id
    )
    db.session.add(entry)
    db.session.commit()

    return render_template(
        'result.html',
        situation=situation,
        positive=positive_final,
        negative=negative_final
    )


@app.route('/history')
@login_required
def history():
   
    records = AnalysisHistory.query.filter_by(user_id=current_user.id).order_by(AnalysisHistory.id.desc()).all()
    return render_template('history.html', history=records)


if __name__ == "__main__":
    app.run(debug=True)
