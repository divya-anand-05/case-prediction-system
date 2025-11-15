from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import subprocess
from datetime import datetime

app = Flask(__name__)


# DATABASE CONFIGURATION

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///history.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# DATABASE MODEL

class AnalysisHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    situation = db.Column(db.Text, nullable=False)
    positive = db.Column(db.Text)
    negative = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# Create DB table if not exists
with app.app_context():
    db.create_all()



@app.route('/')
def home():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
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
        negative=negative_final
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
def history():
   
    records = AnalysisHistory.query.order_by(AnalysisHistory.id.desc()).all()
    return render_template('history.html', history=records)


if __name__ == "__main__":
    app.run(debug=True)
