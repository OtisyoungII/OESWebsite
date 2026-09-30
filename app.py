import os

from flask import Flask, redirect, render_template, url_for
from chat import init_chat

app = Flask(__name__)
init_chat(app)

# Public website freshness and product endpoints live here so templates do not
# duplicate release-sensitive values.
app.config.update(
    SITE_STATUS_UPDATED="September 2026",
    SPORTFOLIO_WEB_URL=os.environ.get(
        "SPORTFOLIO_WEB_URL",
        "https://sportfolio-api-ktd5.onrender.com/",
    ),
)


@app.context_processor
def inject_public_site_status():
    return {
        "site_status_updated": app.config["SITE_STATUS_UPDATED"],
    }


@app.get('/healthz')
def healthz():
    """Website liveness only. Never consult optional AI dependencies."""
    return {'status': 'ok'}, 200, {'Cache-Control': 'no-store'}


@app.route("/")
def home():
    return render_template(
        "index.html",
        sportfolio_web_url=app.config["SPORTFOLIO_WEB_URL"],
    )


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


@app.route("/drinks-with-friendz/privacy")
def drinks_with_friendz_privacy():
    return render_template("drinks_with_friendz_privacy.html")


if __name__ == "__main__":
    app.run(host=os.environ.get('HOST', '127.0.0.1'), port=int(os.environ.get('PORT', '5000')),
            debug=os.environ.get('OES_DEV_DEBUG', 'true').lower() == 'true')
