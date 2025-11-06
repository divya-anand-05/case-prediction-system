from flask import Flask, render_template, request
import subprocess
import json

app = Flask(__name__)

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

    # Run Ollama model locally
    command = ["ollama", "run", "llama3", prompt]
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    ai_output = result.stdout.strip()

    positive_part = ""
    negative_part = ""

    lines = ai_output.splitlines()
    current_section = None

    for line in lines:
        lower_line = line.lower()
        if "positive" in lower_line:
            current_section = "positive"
            continue
        elif "negative" in lower_line:
            current_section = "negative"
            continue

        if current_section == "positive":
            positive_part += line + "\n"
        elif current_section == "negative":
            negative_part += line + "\n"

    return render_template('result.html',
                           situation=situation,
                           positive=positive_part.strip(),
                           negative=negative_part.strip())

    return render_template('result.html', result=ai_output)

if __name__ == '__main__':
    app.run(debug=True)
