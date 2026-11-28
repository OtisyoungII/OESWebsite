import os

from flask import Flask, redirect, render_template, url_for
from chat import init_chat
from product_intelligence import init_product_intelligence
from android_interest import init_android_interest
from public_destinations import AQUAFUNDED_WEBSITE, active_community_invites
from marketing_metrics import init_marketing_metrics

app = Flask(__name__)
init_chat(app)
init_product_intelligence(app)
init_android_interest(app)
init_marketing_metrics(app)

# Public website freshness and product endpoints live here so templates do not
# duplicate release-sensitive values.
app.config.update(
    SITE_STATUS_UPDATED="September 2026",
    OPENAI_ADS_PIXEL_ID=os.environ.get("OPENAI_ADS_PIXEL_ID", "").strip(),
    SPORTFOLIO_WEB_URL=os.environ.get(
        "SPORTFOLIO_WEB_URL",
        "https://sportfolio-api-ktd5.onrender.com/",
    ),
)


@app.context_processor
def inject_public_site_status():
    return {
        "site_status_updated": app.config["SITE_STATUS_UPDATED"],
        "openai_ads_pixel_id": app.config["OPENAI_ADS_PIXEL_ID"],
        "community_invites": active_community_invites(),
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
    return render_template("chaseingreen.html")


@app.get("/chaseingreen/getting-started")
def chaseingreen_getting_started():
    return render_template("chaseingreen_getting_started.html")


@app.get('/chaseingreen/onboarding')
def chaseingreen_onboarding():
    return render_template('chaseingreen_onboarding.html')


@app.get('/chaseingreen/onboarding/aquafunded')
def aquafunded_onboarding():
    return render_template('aquafunded_onboarding.html', affiliate_url=AQUAFUNDED_WEBSITE)


@app.route("/lottovate")
def lottovate():
    return product_detail('lottovate')


PRODUCT_PAGES = {
    'lottovate': ('Lottovate', 'Beta testing · Not accepting new testers',
                  'Explore Michigan Daily 3 and Daily 4 results, compare historical patterns and organize your picks. No number or outcome is guaranteed.',
                  'Check TestFlight availability', 'https://testflight.apple.com/join/CD35ByXj',
                  'testflight_link_activated'),
    'sportfolio': ('Sportfolio', 'Baseball field testing',
                  'Keep teams, rosters, scoring and player records together. Baseball is the first sport in field testing.',
                  'Try the web field test', None, 'web_app_link_activated'),
    'drinks-with-friendz': ('Drinks With Friendz', 'Available on the App Store · Client work',
                          'An iPhone app developed by OES for the Drinks With Friendz client brand. Discover nearby venues and explore them on a map.',
                          'Download on the App Store', 'https://apps.apple.com/us/app/drinks-with-friendz/id6803617345',
                          'external_product_link_activated'),
    'scout': ('OES Scout', 'In development',
              'Scout is an OES project for supervised software operations and repository analysis.',
              None, None, None),
    'rush-and-risk': ('Rush & Risk', 'Public availability unconfirmed',
                      'Contact OES for confirmed product information.', None, None, None),
    'eyeball': ('Eyeball', 'Available on the OES website',
                'Eyeball is the public OES assistant. Ask about our technology or say hello. Do not share private information.',
                'Meet Eyeball', '/#eyeball', None),
}


@app.get('/products')
def products():
    return render_template('product_portfolio.html', products=PRODUCT_PAGES)


@app.get('/products/<slug>')
def product_detail(slug):
    if slug == 'chaseingreen':
        return redirect(url_for('chaseingreen'))
    if slug not in PRODUCT_PAGES:
        return '', 404
    product = PRODUCT_PAGES[slug]
    destination = app.config['SPORTFOLIO_WEB_URL'] if slug == 'sportfolio' else product[4]
    if slug == 'sportfolio' and not destination.startswith('https://'):
        destination = None
    return render_template('product_detail.html', slug=slug, product=product, destination=destination)


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
