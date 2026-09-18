"""
Dummy E-commerce Backend API — FLASK version
============================================
Cholao:  python -m dummy_api.main
     ba: flask --app dummy_api.main run --port 8001 --debug

⚠️ Endpoint gulo, URL gulo ebong JSON response format HUBAHU age jemon chhilo temoni
   rakha hoyeche. Tai `app/api_client.py` ebong `app/tools.py` e EK LINE O bodlate hobe na.

FastAPI -> Flask e ki ki bodlalo:
  1. @app.get("/x")            -> @app.get("/x")            (Flask 2.0+ e eta ache, same)
  2. def f(query: str = None)  -> request.args.get("query") (auto type-cast nei, nije korte hoy)
  3. HTTPException(404, "...")  -> raise ApiError("...", 404) + errorhandler
  4. Pydantic body model        -> request.get_json() + nijer validation
  5. return dict                -> return jsonify(dict)
"""

from datetime import datetime, timedelta

from flask import Flask, jsonify, request

from dummy_api.data import (
    ORDERS,
    POLICIES,
    PRODUCTS,
    RETURN_COUNTER,
    RETURN_WINDOW_DAYS,
    RETURNABLE_STATUS,
    RETURNS,
    USERS,
    VALID_RETURN_REASONS,
)

app = Flask(__name__)
app.json.sort_keys = False          # response e key er order thik rakhe
app.json.ensure_ascii = False       # Bangla text thik moto ashe


# ============================ ERROR HANDLING ============================
class ApiError(Exception):
    """FastAPI er HTTPException er poriborte."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@app.errorhandler(ApiError)
def handle_api_error(e: ApiError):
    # `detail` key tai rakha holo -- api_client.py ei key tai pore
    return jsonify({"detail": e.message}), e.status_code


@app.errorhandler(404)
def handle_404(_):
    return jsonify({"detail": "Endpoint not found"}), 404


@app.errorhandler(Exception)
def handle_unexpected(e):
    return jsonify({"detail": f"Internal error: {e}"}), 500


# ============================ QUERY PARAM HELPERS ============================
# FastAPI automatic type-cast korto, Flask e eta nije korte hoy.
def q_str(name, default=None):
    v = request.args.get(name)
    return default if v is None or v.strip() == "" else v.strip()


def q_float(name, default=None):
    v = q_str(name)
    if v is None:
        return default
    try:
        return float(v)
    except ValueError:
        raise ApiError(f"'{name}' must be a number, got '{v}'", 422)


def q_int(name, default=None):
    v = q_str(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        raise ApiError(f"'{name}' must be an integer, got '{v}'", 422)


def q_bool(name, default=False):
    v = q_str(name)
    if v is None:
        return default
    return v.lower() in {"1", "true", "yes", "y"}


# ============================ HEALTH ============================
@app.get("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})


# ============================ PRODUCTS ============================
@app.get("/products")
def search_products():
    query = q_str("query")
    category = q_str("category")
    brand = q_str("brand")
    min_price = q_float("min_price")
    max_price = q_float("max_price")
    in_stock_only = q_bool("in_stock_only", False)
    sort_by = q_str("sort_by", "relevance")
    limit = q_int("limit", 5)

    if sort_by not in {"relevance", "price_asc", "price_desc", "rating"}:
        raise ApiError("sort_by must be one of: relevance, price_asc, price_desc, rating", 422)

    results = PRODUCTS

    if query:
        terms = [t for t in query.lower().replace(",", " ").split() if t]

        def score(p):
            blob = " ".join(
                [p["name"], p["category"], p["sub_category"], p["brand"], p["description"], " ".join(p["tags"])]
            ).lower()
            return sum(1 for t in terms if t in blob)

        results = [p for p in results if score(p) > 0]
        results = sorted(results, key=score, reverse=True)

    if category:
        results = [p for p in results if p["category"].lower() == category.lower()]
    if brand:
        results = [p for p in results if p["brand"].lower() == brand.lower()]
    if min_price is not None:
        results = [p for p in results if p["price"] >= min_price]
    if max_price is not None:
        results = [p for p in results if p["price"] <= max_price]
    if in_stock_only:
        results = [p for p in results if p["stock"] > 0]

    if sort_by == "price_asc":
        results = sorted(results, key=lambda p: p["price"])
    elif sort_by == "price_desc":
        results = sorted(results, key=lambda p: p["price"], reverse=True)
    elif sort_by == "rating":
        results = sorted(results, key=lambda p: p["rating"], reverse=True)

    return jsonify({"count": len(results[:limit]), "results": results[:limit]})


def _find_product(product_id: str):
    for p in PRODUCTS:
        if p["id"].upper() == product_id.upper():
            return p
    raise ApiError(f"Product {product_id} not found", 404)


@app.get("/products/<product_id>")
def get_product(product_id):
    return jsonify(_find_product(product_id))


@app.get("/stock/<product_id>")
def check_stock(product_id):
    p = _find_product(product_id)
    return jsonify({
        "product_id": p["id"],
        "name": p["name"],
        "stock": p["stock"],
        "in_stock": p["stock"] > 0,
        "restock_eta_days": None if p["stock"] > 0 else 5,
    })


# ============================ ORDERS ============================
@app.get("/orders/<order_id>")
def get_order(order_id):
    order = ORDERS.get(order_id.upper())
    if not order:
        raise ApiError(f"Order {order_id} not found", 404)
    return jsonify(order)


@app.get("/users/<user_id>/orders")
def list_user_orders(user_id):
    limit = q_int("limit", 5)
    orders = [o for o in ORDERS.values() if o["user_id"] == user_id.upper()]
    orders = sorted(orders, key=lambda o: o["placed_on"], reverse=True)
    if not orders:
        raise ApiError(f"No orders found for user {user_id}", 404)
    return jsonify({"user_id": user_id.upper(), "count": len(orders[:limit]), "orders": orders[:limit]})


# ============================ RETURNS ============================
@app.post("/returns")
def create_return():
    body = request.get_json(silent=True) or {}

    # FastAPI er Pydantic model er poriborte manual validation
    order_id = body.get("order_id")
    product_id = body.get("product_id")
    reason = body.get("reason")
    comment = body.get("comment")
    qty = body.get("qty", 1)

    if not order_id or not product_id or not reason:
        raise ApiError("order_id, product_id and reason are required", 422)
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        raise ApiError("qty must be an integer", 422)

    order = ORDERS.get(str(order_id).upper())
    if not order:
        raise ApiError(f"Order {order_id} not found", 404)

    if reason not in VALID_RETURN_REASONS:
        raise ApiError(f"Invalid reason. Allowed: {', '.join(VALID_RETURN_REASONS)}", 400)

    if order["status"] not in RETURNABLE_STATUS:
        raise ApiError(
            f"Order status is '{order['status']}'. Only delivered orders are returnable.", 409
        )

    item = next((i for i in order["items"] if i["product_id"].upper() == str(product_id).upper()), None)
    if not item:
        raise ApiError(f"Product {product_id} is not part of order {order_id}", 404)

    delivered_on = datetime.strptime(order["delivered_on"], "%Y-%m-%d")
    days_since = (datetime.utcnow() - delivered_on).days
    if days_since > RETURN_WINDOW_DAYS:
        raise ApiError(
            f"Return window expired. Delivered {days_since} days ago, limit is {RETURN_WINDOW_DAYS} days.",
            409,
        )

    RETURN_COUNTER["n"] += 1
    rma_id = f"RMA-{RETURN_COUNTER['n']}"
    rma = {
        "rma_id": rma_id,
        "order_id": order["order_id"],
        "product_id": item["product_id"],
        "product_name": item["name"],
        "qty": qty,
        "reason": reason,
        "comment": comment,
        "status": "approved_pending_pickup",
        "refund_amount": item["price"] * qty,
        "currency": order["currency"],
        "refund_method": order["payment_method"],
        "pickup_scheduled_on": (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d"),
        "created_at": datetime.utcnow().strftime("%Y-%m-%d"),
        "courier_charge_borne_by": "company" if reason in {"damaged", "defective", "wrong_item"} else "customer",
    }
    RETURNS[rma_id] = rma
    return jsonify(rma), 201


# ⚠️ Route order guruttopurno: '/returns/eligibility/<id>' ke '/returns/<rma_id>' er
#    AGE declare kora hoyeche jate 'eligibility' ke rma_id hisebe na dhore.
@app.get("/returns/eligibility/<order_id>")
def return_eligibility(order_id):
    order = ORDERS.get(order_id.upper())
    if not order:
        raise ApiError(f"Order {order_id} not found", 404)

    if order["status"] not in RETURNABLE_STATUS:
        return jsonify({
            "order_id": order["order_id"],
            "eligible": False,
            "reason": f"Order status is '{order['status']}', not delivered.",
            "items": [],
        })

    delivered_on = datetime.strptime(order["delivered_on"], "%Y-%m-%d")
    days_since = (datetime.utcnow() - delivered_on).days
    eligible = days_since <= RETURN_WINDOW_DAYS
    return jsonify({
        "order_id": order["order_id"],
        "eligible": eligible,
        "days_since_delivery": days_since,
        "window_days": RETURN_WINDOW_DAYS,
        "reason": None if eligible else "Return window expired",
        "items": order["items"] if eligible else [],
        "valid_reasons": VALID_RETURN_REASONS,
    })


@app.get("/returns/<rma_id>")
def get_return(rma_id):
    rma = RETURNS.get(rma_id.upper())
    if not rma:
        raise ApiError(f"Return {rma_id} not found", 404)
    return jsonify(rma)


# ============================ RECOMMENDATIONS ============================
@app.get("/recommendations")
def recommend():
    user_id = q_str("user_id")
    product_id = q_str("product_id")
    budget_max = q_float("budget_max")
    limit = q_int("limit", 4)

    pool = [p for p in PRODUCTS if p["stock"] > 0]
    seed_tags, seed_categories, exclude = set(), set(), set()

    if product_id:
        base = next((p for p in PRODUCTS if p["id"].upper() == product_id.upper()), None)
        if base:
            seed_tags |= set(base["tags"])
            seed_categories.add(base["category"])
            exclude.add(base["id"])

    if user_id:
        user = USERS.get(user_id.upper())
        if user:
            seed_categories |= set(user["preferred_categories"])
            for pid in user["recently_viewed"]:
                rp = next((p for p in PRODUCTS if p["id"] == pid), None)
                if rp:
                    seed_tags |= set(rp["tags"])
                    exclude.add(rp["id"])

    if budget_max is not None:
        pool = [p for p in pool if p["price"] <= budget_max]

    def score(p):
        s = 2.0 * len(seed_tags & set(p["tags"]))
        s += 1.5 if p["category"] in seed_categories else 0
        s += p["rating"]
        return s

    ranked = sorted([p for p in pool if p["id"] not in exclude], key=score, reverse=True)
    return jsonify({
        "basis": {"user_id": user_id, "product_id": product_id, "budget_max": budget_max},
        "count": len(ranked[:limit]),
        "results": ranked[:limit],
    })


# ============================ USER / POLICY ============================
@app.get("/users/<user_id>")
def get_user(user_id):
    user = USERS.get(user_id.upper())
    if not user:
        raise ApiError(f"User {user_id} not found", 404)
    return jsonify(user)


@app.get("/policy/<topic>")
def get_policy(topic):
    text = POLICIES.get(topic.lower())
    if not text:
        raise ApiError(f"No policy for '{topic}'. Available: {', '.join(POLICIES.keys())}", 404)
    return jsonify({"topic": topic.lower(), "policy": text})


# ============================ ROUTE LIST (Swagger er poriborte) ============================
@app.get("/")
def index():
    """FastAPI te /docs chhilo. Flask e nei, tai ekta simple route list dilam."""
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        methods = sorted(m for m in rule.methods if m not in {"HEAD", "OPTIONS"})
        routes.append({"path": str(rule), "methods": methods})
    return jsonify({"service": "Dummy E-commerce API (Flask)", "routes": sorted(routes, key=lambda r: r["path"])})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=True, threaded=True)
