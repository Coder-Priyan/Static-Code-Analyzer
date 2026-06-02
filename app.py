from flask import Flask, render_template, request
from lexer import tokenize
from parser import analyze as syntax_analyze
from semantic import analyze as semantic_analyze

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():
    tokens = []
    syntax_errors = []
    semantic_errors = []
    code = ""

    if request.method == "POST":
        code = request.form.get("code", "")

        # 🔥 STEP 1: Tokenize
        tokens = tokenize(code)

        # 🔥 STEP 2: Syntax Analysis
        syntax_errors = syntax_analyze(tokens)

        # 🔥 STEP 3: Semantic Analysis (always run)
        semantic_errors, _ = semantic_analyze(tokens)

    return render_template(
        "index.html",
        tokens=tokens,
        syntax_errors=syntax_errors,
        semantic_errors=semantic_errors,
        code=code
    )

if __name__ == "__main__":
    app.run(debug=True)