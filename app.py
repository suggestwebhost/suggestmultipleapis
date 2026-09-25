import os
import requests
from flask import Flask, render_template_string, request
from flask_caching import Cache

app = Flask(__name__)

# Configure local RAM cache so calling 6 APIs doesn't make the page slow
app.config.from_mapping({"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 600})
cache = Cache(app)

# 1. API Configuration Credentials
TINYFISH_API_KEY = os.environ.get("TINYFISH_API_KEY", "your_free_tinyfish_key")
TINYFISH_URL = "https://tinyfish.ai"

# We use open, completely free, no-key public API testbeds for other features
CURRENCY_API_URL = "https://er-api.com" 
WEATHER_API_URL = "https://open-meteo.com" # London Coordinates

@app.route('/')
@cache.cached(timeout=600, query_string=True) # Caches the final blended result for 10 minutes
def storefront_dashboard():
    user_currency = request.args.get('currency', 'GBP')
    
    # ─── API SERVICE 1: Fetching Clothing Items (TinyFish) ───
    products = []
    try:
        tf_res = requests.post(TINYFISH_URL, json={"url": "https://scrapeme.live", "format": "json"}, headers={"X-API-Key": TINYFISH_API_KEY}, timeout=4)
        if tf_res.status_code == 200:
            products = tf_res.json().get("products", [])
    except Exception:
        # Fallback if external API down
        products = [{"title": "Classic Cotton Jacket", "price_gbp": 45.0, "image": "https://unsplash.com"}]

    # ─── API SERVICE 2: Live Currency Rates ───
    exchange_rate = 1.0
    try:
        curr_res = requests.get(CURRENCY_API_URL, timeout=3).json()
        exchange_rate = curr_res.get("rates", {}).get(user_currency, 1.0)
    except Exception:
        pass

    # ─── API SERVICE 3: Live Weather (To adjust shipping warnings) ───
    weather_alert = "Standard Delivery"
    try:
        weather_res = requests.get(WEATHER_API_URL, timeout=3).json()
        temp = weather_res.get("current_weather", {}).get("temperature", 20)
        if temp < 0:
            weather_alert = "❄️ Delay Warning: Heavy snow at transit hub."
    except Exception:
        pass

    # ─── DATA AGGREGATION & CONVERSION ───
    final_products = []
    for p in products:
        # If fallback format standardizes price
        raw_price = p.get('price_gbp', 30.0) if 'price_gbp' in p else float(p.get('price', '£30').replace('£', ''))
        
        # Live calculation using data pulled from API 2
        converted_price = round(raw_price * exchange_rate, 2)
        
        final_products.append({
            "title": p['title'],
            "image": p['image'],
            "display_price": f"{user_currency} {converted_price}"
        })

    # One single unified HTML output layout rendered back to client
    html_ui = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Single-Hub Dynamic Store</title>
        <script src="https://jsdelivr.net"></script>
    </head>
    <body class="bg-slate-50 p-8 text-slate-800">
        <div class="max-w-6xl mx-auto">
            <!-- Banner combining Weather API & Currency Controls -->
            <div class="bg-white p-6 rounded-xl border border-slate-200 mb-8 flex justify-between items-center shadow-xs">
                <div>
                    <h1 class="text-2xl font-bold text-blue-600">🐟 Integrated Hub Dashboard</h1>
                    <p class="text-sm text-slate-500 mt-1">Status: <span class="text-amber-600 font-medium">{{ alert }}</span></p>
                </div>
                <form method="GET" action="/">
                    <select name="currency" onchange="this.form.submit()" class="bg-slate-100 border p-2 rounded-lg font-medium text-sm">
                        <option value="GBP" {% if curr == 'GBP' %}selected{% endif %}>GBP (£)</option>
                        <option value="USD" {% if curr == 'USD' %}selected{% endif %}>USD ($)</option>
                        <option value="EUR" {% if curr == 'EUR' %}selected{% endif %}>EUR (€)</option>
                    </select>
                </form>
            </div>

            <!-- Products Layout Grid -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                {% for product in items %}
                <div class="bg-white border rounded-xl overflow-hidden p-4 shadow-2xs">
                    <img src="{{ product.image }}" class="w-full aspect-square object-cover bg-slate-100 rounded-lg mb-4">
                    <h3 class="font-bold text-slate-900 line-clamp-1 mb-1">{{ product.title }}</h3>
                    <p class="text-blue-600 font-semibold text-sm">{{ product.display_price }}</p>
                </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_ui, items=final_products, curr=user_currency, alert=weather_alert)

if __name__ == '__main__':
    app.run(port=5000, debug=True)
