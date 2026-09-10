from flask import Flask, redirect, render_template, url_for
from chat import init_chat

app = Flask(__name__)
init_chat(app)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chaseingreen")
def chaseingreen():
    return redirect(f"{url_for('home')}#products")


@app.route("/lottovate")
def lottovate():
    return redirect(f"{url_for('home')}#products")


@app.route("/contact")
def contact():
    return redirect(f"{url_for('home')}#contact")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


if __name__ == "__main__":
    app.run(debug=True)
