from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chaseingreen")
def chaseingreen():
    return render_template("chaseingreen.html")


@app.route("/lottovate")
def lottovate():
    return render_template("lottovate.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True)