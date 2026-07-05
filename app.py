from __future__ import annotations

import json
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from flask import Flask, jsonify, redirect, render_template, request, session, url_for


APP_NAME = "Local Table Order App"
TABLE_COUNT = 12
PORT = 5000

DEFAULT_SETTINGS: dict[str, Any] = {
    "accepting_orders": True,
    "app_display_name": "Local Table Order App",
    "app_icon": "🛒",
}

DEFAULT_PRODUCTS: list[dict[str, Any]] = [
    {
        "id": 1,
        "name": "商品A",
        "unit": "内容を入力してください",
        "price": 0,
        "max_quantity": 5,
        "category": "フード",
        "sort_order": 10,
        "recommended": False,
        "sold_out": False,
        "active": False,
    },
    {
        "id": 2,
        "name": "商品B",
        "unit": "内容を入力してください",
        "price": 0,
        "max_quantity": 5,
        "category": "ドリンク",
        "sort_order": 20,
        "recommended": False,
        "sold_out": False,
        "active": False,
    },
    {
        "id": 3,
        "name": "商品C",
        "unit": "内容を入力してください",
        "price": 0,
        "max_quantity": 5,
        "category": "その他",
        "sort_order": 30,
        "recommended": False,
        "sold_out": False,
        "active": False,
    },
]


def resource_path(relative_path: str) -> Path:
    """
    通常実行と PyInstaller 実行の両方で templates/static を見つけるための関数。

    - 通常実行: この app.py があるフォルダを基準にする
    - exe化後: PyInstaller が展開した _MEIPASS を基準にする
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")) / relative_path
    return Path(__file__).resolve().parent / relative_path


def writable_base_dir() -> Path:
    """
    JSONデータを書き込む場所を返す。

    exe化後は、exeと同じ階層の data フォルダを使う。
    ソース実行時は、プロジェクト直下の data フォルダを使う。
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = writable_base_dir()
DATA_DIR = BASE_DIR / "data"
PRODUCTS_FILE = DATA_DIR / "products.json"
ORDERS_FILE = DATA_DIR / "orders.json"
TABLE_SESSIONS_FILE = DATA_DIR / "table_sessions.json"
CARTS_FILE = DATA_DIR / "carts.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

DATA_LOCK = Lock()

app = Flask(
    __name__,
    template_folder=str(resource_path("templates")),
    static_folder=str(resource_path("static")),
)
app.secret_key = "local-table-order-app-local-only-secret-key"


# -----------------------------
# JSON helpers
# -----------------------------

def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return deepcopy(default)

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return deepcopy(default)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not PRODUCTS_FILE.exists():
        save_json(PRODUCTS_FILE, DEFAULT_PRODUCTS)
    if not ORDERS_FILE.exists():
        save_json(ORDERS_FILE, [])
    if not TABLE_SESSIONS_FILE.exists():
        save_json(TABLE_SESSIONS_FILE, {})
    if not CARTS_FILE.exists():
        save_json(CARTS_FILE, {})
    if not SETTINGS_FILE.exists():
        save_json(SETTINGS_FILE, DEFAULT_SETTINGS)


# -----------------------------
# Basic helpers
# -----------------------------

def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@app.template_filter("yen")
def yen(value: int | str | None) -> str:
    try:
        amount = int(value or 0)
    except (TypeError, ValueError):
        amount = 0
    return f"{amount:,}円"


def safe_int(value: Any, default: int = 0, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default

    if minimum is not None:
        number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def validate_table_no(table_no: int) -> bool:
    return 1 <= table_no <= TABLE_COUNT


def get_settings() -> dict[str, Any]:
    settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    merged = deepcopy(DEFAULT_SETTINGS)
    merged.update(settings)
    return merged


def save_settings(settings: dict[str, Any]) -> None:
    merged = deepcopy(DEFAULT_SETTINGS)
    merged.update(settings)
    save_json(SETTINGS_FILE, merged)


def get_app_config() -> dict[str, str]:
    """
    画面に表示するアプリ名とアイコンを返す。

    ここで扱うアイコンは、Windowsのexeアイコンではなく、
    注文画面・管理画面に表示する絵文字/文字アイコン。
    """
    settings = get_settings()
    display_name = str(settings.get("app_display_name", "")).strip() or "Local Table Order App"
    icon = str(settings.get("app_icon", "")).strip() or "🛒"

    # 長すぎる表示崩れを防ぐため、画面表示用は軽く制限する。
    return {
        "display_name": display_name[:40],
        "icon": icon[:8],
    }


@app.context_processor
def inject_app_config() -> dict[str, Any]:
    return {"app_config": get_app_config()}


def get_device_id() -> str:
    """
    ブラウザごとの識別IDを作る。

    同じテーブルを別端末が開かないようにするため、
    Flaskのsessionを使ってブラウザ単位のIDを保存する。
    """
    if "device_id" not in session:
        session["device_id"] = uuid4().hex
        session.modified = True
    return str(session["device_id"])


# -----------------------------
# Products
# -----------------------------

def normalize_product(product: dict[str, Any]) -> dict[str, Any]:
    """
    古い products.json に新しい項目がなくても動くように、商品データを補完する。
    """
    return {
        "id": safe_int(product.get("id"), 0, minimum=0),
        "name": str(product.get("name", "商品名未設定")).strip() or "商品名未設定",
        "unit": str(product.get("unit", "内容未設定")).strip() or "内容未設定",
        "price": safe_int(product.get("price"), 0, minimum=0),
        "max_quantity": safe_int(product.get("max_quantity"), 5, minimum=1, maximum=99),
        "category": str(product.get("category", "その他")).strip() or "その他",
        "sort_order": safe_int(product.get("sort_order"), 999),
        "recommended": bool(product.get("recommended", False)),
        "sold_out": bool(product.get("sold_out", False)),
        "active": bool(product.get("active", True)),
    }


def sort_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        products,
        key=lambda product: (
            str(product.get("category", "")),
            int(product.get("sort_order", 999)),
            int(product.get("id", 0)),
        ),
    )


def get_products(include_inactive: bool = False) -> list[dict[str, Any]]:
    products = load_json(PRODUCTS_FILE, DEFAULT_PRODUCTS)
    normalized_products = [normalize_product(product) for product in products]

    if not include_inactive:
        normalized_products = [product for product in normalized_products if product.get("active")]

    return sort_products(normalized_products)


def save_products(products: list[dict[str, Any]]) -> None:
    save_json(PRODUCTS_FILE, sort_products([normalize_product(product) for product in products]))


def find_product(product_id: int, include_inactive: bool = True) -> dict[str, Any] | None:
    return next(
        (product for product in get_products(include_inactive=include_inactive) if int(product["id"]) == int(product_id)),
        None,
    )


def next_product_id(products: list[dict[str, Any]]) -> int:
    return max([safe_int(product.get("id"), 0) for product in products], default=0) + 1


def group_products_by_category(products: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for product in products:
        grouped.setdefault(product.get("category", "その他"), []).append(product)
    return grouped


# -----------------------------
# Cart
# -----------------------------

def get_all_carts() -> dict[str, dict[str, int]]:
    carts = load_json(CARTS_FILE, {})
    if not isinstance(carts, dict):
        return {}
    return carts


def get_cart(table_no: int) -> dict[str, int]:
    carts = get_all_carts()
    raw_cart = carts.get(str(table_no), {})

    if not isinstance(raw_cart, dict):
        return {}

    return {str(product_id): safe_int(quantity, 0, minimum=0) for product_id, quantity in raw_cart.items()}


def set_cart(table_no: int, cart: dict[str, int]) -> None:
    carts = get_all_carts()
    carts[str(table_no)] = {str(product_id): safe_int(quantity, 0, minimum=0) for product_id, quantity in cart.items() if safe_int(quantity, 0) > 0}
    save_json(CARTS_FILE, carts)


def clear_cart(table_no: int) -> None:
    carts = get_all_carts()
    carts[str(table_no)] = {}
    save_json(CARTS_FILE, carts)


def clamp_quantity(quantity: int, max_quantity: int) -> int:
    return max(0, min(quantity, max_quantity))


def cart_to_items(table_no: int) -> list[dict[str, Any]]:
    cart = get_cart(table_no)
    items: list[dict[str, Any]] = []

    for product_id, quantity in cart.items():
        product = find_product(safe_int(product_id), include_inactive=True)

        if not product:
            continue
        if not product.get("active"):
            continue
        if product.get("sold_out"):
            continue

        safe_quantity = clamp_quantity(
            safe_int(quantity, 0),
            safe_int(product.get("max_quantity"), 5, minimum=1, maximum=99),
        )

        if safe_quantity <= 0:
            continue

        subtotal = safe_int(product.get("price"), 0, minimum=0) * safe_quantity
        items.append(
            {
                "product_id": safe_int(product.get("id"), 0),
                "name": product["name"],
                "unit": product["unit"],
                "price": safe_int(product.get("price"), 0, minimum=0),
                "quantity": safe_quantity,
                "subtotal": subtotal,
            }
        )

    return items


def items_total(items: list[dict[str, Any]]) -> int:
    return sum(safe_int(item.get("subtotal"), 0) for item in items)


def aggregate_table_items(current_items: list[dict[str, Any]], new_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aggregated: dict[int, dict[str, Any]] = {}

    for item in current_items + new_items:
        product_id = safe_int(item.get("product_id"), 0)
        if product_id not in aggregated:
            aggregated[product_id] = {
                "product_id": product_id,
                "name": item.get("name", "商品名未設定"),
                "unit": item.get("unit", ""),
                "price": safe_int(item.get("price"), 0),
                "quantity": 0,
                "subtotal": 0,
            }

        aggregated[product_id]["quantity"] += safe_int(item.get("quantity"), 0)
        aggregated[product_id]["subtotal"] = aggregated[product_id]["price"] * aggregated[product_id]["quantity"]

    return list(aggregated.values())


# -----------------------------
# Table sessions / lock
# -----------------------------

def default_table_session(table_no: int) -> dict[str, Any]:
    return {
        "table_no": table_no,
        "locked": False,
        "owner_device_id": None,
        "locked_at": None,
        "active": False,
        "items": [],
        "total": 0,
        "updated_at": None,
    }


def normalize_table_session(table_no: int, table_session: dict[str, Any] | None) -> dict[str, Any]:
    normalized = default_table_session(table_no)
    if table_session:
        normalized.update(table_session)

    # 古いバージョン互換。active=True だけ保存されていたデータは locked=True とみなす。
    if normalized.get("active") and not normalized.get("locked"):
        normalized["locked"] = True

    normalized["table_no"] = table_no
    normalized["items"] = normalized.get("items") if isinstance(normalized.get("items"), list) else []
    normalized["total"] = safe_int(normalized.get("total"), 0, minimum=0)
    normalized["active"] = bool(normalized.get("active"))
    normalized["locked"] = bool(normalized.get("locked"))
    return normalized


def get_table_session(table_no: int) -> dict[str, Any]:
    sessions = load_json(TABLE_SESSIONS_FILE, {})
    return normalize_table_session(table_no, sessions.get(str(table_no)))


def save_table_session(table_no: int, table_session: dict[str, Any]) -> None:
    sessions = load_json(TABLE_SESSIONS_FILE, {})
    sessions[str(table_no)] = normalize_table_session(table_no, table_session)
    save_json(TABLE_SESSIONS_FILE, sessions)


def is_table_locked_by_another_device(table_no: int) -> bool:
    table_session = get_table_session(table_no)

    if not table_session.get("locked"):
        return False

    owner_device_id = table_session.get("owner_device_id")
    if not owner_device_id:
        return False

    return owner_device_id != get_device_id()


def lock_table_for_current_device(table_no: int) -> bool:
    device_id = get_device_id()
    current_time = now_text()

    with DATA_LOCK:
        sessions = load_json(TABLE_SESSIONS_FILE, {})
        current = normalize_table_session(table_no, sessions.get(str(table_no)))
        current_owner = current.get("owner_device_id")

        if current.get("locked") and current_owner and current_owner != device_id:
            return False

        current["locked"] = True
        current["owner_device_id"] = current_owner or device_id
        current["locked_at"] = current.get("locked_at") or current_time
        current["updated_at"] = current.get("updated_at") or current_time
        sessions[str(table_no)] = current
        save_json(TABLE_SESSIONS_FILE, sessions)

    return True


def current_device_can_use_table(table_no: int) -> bool:
    if is_table_locked_by_another_device(table_no):
        return False
    return lock_table_for_current_device(table_no)


def table_has_unserved_orders(table_no: int) -> bool:
    orders = load_json(ORDERS_FILE, [])
    return any(
        safe_int(order.get("table_no"), 0) == table_no and order.get("status") != "served"
        for order in orders
    )


def table_unserved_count(table_no: int) -> int:
    orders = load_json(ORDERS_FILE, [])
    return sum(
        1
        for order in orders
        if safe_int(order.get("table_no"), 0) == table_no and order.get("status") != "served"
    )


def build_table_statuses() -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []

    for table_no in range(1, TABLE_COUNT + 1):
        table_session = get_table_session(table_no)
        unserved_count = table_unserved_count(table_no)

        if table_session.get("active"):
            label = "使用中"
            state_class = "in-use"
        elif table_session.get("locked"):
            label = "待機中"
            state_class = "standby"
        else:
            label = "未割当"
            state_class = "available"

        statuses.append(
            {
                "table_no": table_no,
                "locked": bool(table_session.get("locked")),
                "active": bool(table_session.get("active")),
                "label": label,
                "state_class": state_class,
                "total": safe_int(table_session.get("total"), 0),
                "unserved_count": unserved_count,
            }
        )

    return statuses


# -----------------------------
# Customer routes
# -----------------------------

@app.route("/")
def home():
    return render_template("index.html", table_count=TABLE_COUNT)


@app.route("/table/<int:table_no>")
def table_home(table_no: int):
    if not validate_table_no(table_no):
        return render_template("error.html", message="存在しないテーブル番号です。"), 404

    if not current_device_can_use_table(table_no):
        return render_template("table_locked.html", table_no=table_no), 423

    table_session = get_table_session(table_no)

    if table_session.get("active") and table_session.get("items"):
        return redirect(url_for("complete", table_no=table_no))

    return render_template("table_start.html", table_no=table_no)


@app.route("/table/<int:table_no>/menu")
def menu(table_no: int):
    if not validate_table_no(table_no):
        return render_template("error.html", message="存在しないテーブル番号です。"), 404

    if not current_device_can_use_table(table_no):
        return render_template("table_locked.html", table_no=table_no), 423

    settings = get_settings()
    products = get_products(include_inactive=False)
    grouped_products = group_products_by_category(products)
    cart = get_cart(table_no)
    cart_items = cart_to_items(table_no)
    cart_count = sum(item["quantity"] for item in cart_items)
    cart_total = items_total(cart_items)
    product_quantities = {safe_int(product_id): safe_int(quantity, 0) for product_id, quantity in cart.items()}

    return render_template(
        "menu.html",
        table_no=table_no,
        grouped_products=grouped_products,
        cart_count=cart_count,
        cart_total=cart_total,
        product_quantities=product_quantities,
        accepting_orders=settings["accepting_orders"],
    )


@app.post("/table/<int:table_no>/cart/change/<int:product_id>")
def change_cart_quantity(table_no: int, product_id: int):
    if not validate_table_no(table_no):
        return jsonify({"ok": False, "message": "存在しないテーブル番号です。"}), 404

    if not current_device_can_use_table(table_no):
        return jsonify({"ok": False, "message": "このテーブルは使用中です。"}), 423

    settings = get_settings()
    if not settings["accepting_orders"]:
        return jsonify({"ok": False, "message": "現在、注文受付を停止しています。"}), 400

    product = find_product(product_id, include_inactive=True)
    if not product or not product.get("active"):
        return jsonify({"ok": False, "message": "商品が見つかりません。"}), 404

    if product.get("sold_out"):
        return jsonify({"ok": False, "message": "この商品は売り切れです。"}), 400

    delta = safe_int(request.form.get("delta"), 0)
    max_quantity = safe_int(product.get("max_quantity"), 5, minimum=1, maximum=99)

    cart = get_cart(table_no)
    current_quantity = safe_int(cart.get(str(product_id)), 0)
    next_quantity = clamp_quantity(current_quantity + delta, max_quantity)

    if next_quantity <= 0:
        cart.pop(str(product_id), None)
    else:
        cart[str(product_id)] = next_quantity

    set_cart(table_no, cart)

    cart_items = cart_to_items(table_no)
    cart_count = sum(item["quantity"] for item in cart_items)
    cart_total = items_total(cart_items)
    subtotal = safe_int(product.get("price"), 0) * next_quantity

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(
            {
                "ok": True,
                "product_id": int(product_id),
                "quantity": next_quantity,
                "subtotal": subtotal,
                "subtotal_text": yen(subtotal),
                "cart_count": cart_count,
                "cart_total": cart_total,
                "cart_total_text": yen(cart_total),
                "max_quantity": max_quantity,
            }
        )

    return redirect(url_for("menu", table_no=table_no))


@app.route("/table/<int:table_no>/cart", methods=["GET", "POST"])
def cart(table_no: int):
    if not validate_table_no(table_no):
        return render_template("error.html", message="存在しないテーブル番号です。"), 404

    if not current_device_can_use_table(table_no):
        return render_template("table_locked.html", table_no=table_no), 423

    # 数量変更はメニュー画面で行う。POSTされてもメニューへ戻す。
    if request.method == "POST":
        return redirect(url_for("menu", table_no=table_no))

    items = cart_to_items(table_no)
    settings = get_settings()

    return render_template(
        "cart.html",
        table_no=table_no,
        items=items,
        total=items_total(items),
        accepting_orders=settings["accepting_orders"],
    )


@app.post("/table/<int:table_no>/order")
def submit_order(table_no: int):
    if not validate_table_no(table_no):
        return render_template("error.html", message="存在しないテーブル番号です。"), 404

    if not current_device_can_use_table(table_no):
        return render_template("table_locked.html", table_no=table_no), 423

    settings = get_settings()
    if not settings["accepting_orders"]:
        return render_template("error.html", message="現在、注文受付を停止しています。"), 400

    items = cart_to_items(table_no)
    if not items:
        return redirect(url_for("menu", table_no=table_no))

    created_at = now_text()
    total = items_total(items)

    with DATA_LOCK:
        orders = load_json(ORDERS_FILE, [])
        next_id = max([safe_int(order.get("id"), 0) for order in orders], default=0) + 1
        order = {
            "id": next_id,
            "table_no": table_no,
            "items": items,
            "total": total,
            "status": "cooking",
            "created_at": created_at,
            "updated_at": created_at,
        }
        orders.append(order)
        save_json(ORDERS_FILE, orders)

        sessions = load_json(TABLE_SESSIONS_FILE, {})
        current = normalize_table_session(table_no, sessions.get(str(table_no)))
        merged_items = aggregate_table_items(current.get("items", []), items)
        current["locked"] = True
        current["owner_device_id"] = current.get("owner_device_id") or get_device_id()
        current["locked_at"] = current.get("locked_at") or created_at
        current["active"] = True
        current["items"] = merged_items
        current["total"] = items_total(merged_items)
        current["updated_at"] = created_at
        sessions[str(table_no)] = current
        save_json(TABLE_SESSIONS_FILE, sessions)

    clear_cart(table_no)
    return redirect(url_for("complete", table_no=table_no))


@app.route("/table/<int:table_no>/complete")
def complete(table_no: int):
    if not validate_table_no(table_no):
        return render_template("error.html", message="存在しないテーブル番号です。"), 404

    if is_table_locked_by_another_device(table_no):
        return render_template("table_locked.html", table_no=table_no), 423

    table_session = get_table_session(table_no)

    if not table_session.get("active") or not table_session.get("items"):
        return redirect(url_for("table_home", table_no=table_no))

    return render_template("complete.html", table_no=table_no, table_session=table_session)


@app.get("/api/table/<int:table_no>/state")
def api_table_state(table_no: int):
    if not validate_table_no(table_no):
        return jsonify({"ok": False}), 404

    table_session = get_table_session(table_no)
    return jsonify(
        {
            "ok": True,
            "locked": bool(table_session.get("locked")),
            "active": bool(table_session.get("active")),
            "has_items": bool(table_session.get("items")),
            "total": safe_int(table_session.get("total"), 0),
        }
    )


# -----------------------------
# Admin routes
# -----------------------------

STATUS_LABELS = {
    "cooking": "調理中",
    "served": "提供済み",
}


@app.route("/admin")
def admin():
    orders = load_json(ORDERS_FILE, [])
    normalized_orders = sorted(
        orders,
        key=lambda order: (str(order.get("created_at", "")), safe_int(order.get("id"), 0)),
    )

    active_orders = [order for order in normalized_orders if order.get("status") != "served"]
    served_orders = [order for order in reversed(normalized_orders) if order.get("status") == "served"]

    force_entry = request.args.get("enter") == "1"
    skip_entry = request.args.get("skip_entry") == "1"

    return render_template(
        "admin.html",
        settings=get_settings(),
        active_orders=active_orders,
        served_orders=served_orders,
        table_statuses=build_table_statuses(),
        status_labels=STATUS_LABELS,
        show_admin_entry_overlay=force_entry or not skip_entry,
    )


@app.post("/admin/toggle-accepting")
def toggle_accepting():
    settings = get_settings()
    was_accepting = bool(settings.get("accepting_orders"))
    settings["accepting_orders"] = not was_accepting
    save_settings(settings)

    # 注文受付を再開したときだけ、通知音確認画面をもう一度出す。
    if not was_accepting and settings["accepting_orders"]:
        return redirect(url_for("admin", enter="1"))

    # 受付停止など、通常操作後の更新では確認画面を出さない。
    return redirect(url_for("admin", skip_entry="1"))


@app.post("/admin/order/<int:order_id>/status")
def update_order_status(order_id: int):
    next_status = request.form.get("status", "served")
    if next_status not in STATUS_LABELS:
        next_status = "served"

    orders = load_json(ORDERS_FILE, [])
    updated_at = now_text()

    for order in orders:
        if safe_int(order.get("id"), 0) == order_id:
            order["status"] = next_status
            order["updated_at"] = updated_at
            break

    save_json(ORDERS_FILE, orders)
    return redirect(url_for("admin", skip_entry="1"))


@app.post("/admin/table/<int:table_no>/available")
def mark_table_available(table_no: int):
    if not validate_table_no(table_no):
        return redirect(url_for("admin", skip_entry="1"))

    # 未提供が残っている場合は、使用可能に戻さない。
    if table_has_unserved_orders(table_no):
        return redirect(url_for("admin", skip_entry="1"))

    with DATA_LOCK:
        sessions = load_json(TABLE_SESSIONS_FILE, {})
        current = normalize_table_session(table_no, sessions.get(str(table_no)))

        # 端末ロックは残す。これにより、そのテーブル用タブレットだけが引き続き使える。
        current["active"] = False
        current["items"] = []
        current["total"] = 0
        current["updated_at"] = now_text()
        sessions[str(table_no)] = current
        save_json(TABLE_SESSIONS_FILE, sessions)

    clear_cart(table_no)
    return redirect(url_for("admin", skip_entry="1"))


@app.post("/admin/table/<int:table_no>/unlock")
def unlock_table(table_no: int):
    if not validate_table_no(table_no):
        return redirect(url_for("admin", skip_entry="1"))

    if table_has_unserved_orders(table_no):
        return redirect(url_for("admin", skip_entry="1"))

    with DATA_LOCK:
        sessions = load_json(TABLE_SESSIONS_FILE, {})
        sessions[str(table_no)] = default_table_session(table_no)
        sessions[str(table_no)]["updated_at"] = now_text()
        save_json(TABLE_SESSIONS_FILE, sessions)

    clear_cart(table_no)
    return redirect(url_for("admin", skip_entry="1"))


@app.get("/api/admin/active-order-count")
def api_active_order_count():
    orders = load_json(ORDERS_FILE, [])
    active_count = sum(1 for order in orders if order.get("status") != "served")
    latest_id = max([safe_int(order.get("id"), 0) for order in orders], default=0)
    return jsonify({"active_count": active_count, "latest_id": latest_id})


# -----------------------------
# App settings admin
# -----------------------------

@app.route("/admin/app-settings", methods=["GET", "POST"])
def app_settings_admin():
    settings = get_settings()

    if request.method == "POST":
        settings["app_display_name"] = request.form.get("app_display_name", "").strip() or "Local Table Order App"
        settings["app_icon"] = request.form.get("app_icon", "").strip() or "🛒"
        save_settings(settings)
        return redirect(url_for("app_settings_admin"))

    return render_template("app_settings.html", settings=settings)


# -----------------------------
# Product admin
# -----------------------------

@app.route("/admin/products")
def products_admin():
    if get_settings().get("accepting_orders"):
        return redirect(url_for("admin", skip_entry="1"))

    return render_template("products.html", products=get_products(include_inactive=True))


@app.post("/admin/products/<int:product_id>/update")
def update_product(product_id: int):
    if get_settings().get("accepting_orders"):
        return redirect(url_for("admin", skip_entry="1"))

    products = get_products(include_inactive=True)

    for product in products:
        if safe_int(product.get("id"), 0) == product_id:
            product["name"] = request.form.get("name", "").strip() or "商品名未設定"
            product["unit"] = request.form.get("unit", "").strip() or "内容未設定"
            product["price"] = safe_int(request.form.get("price"), 0, minimum=0)
            product["max_quantity"] = safe_int(request.form.get("max_quantity"), 5, minimum=1, maximum=99)
            product["category"] = request.form.get("category", "").strip() or "その他"
            product["sort_order"] = safe_int(request.form.get("sort_order"), 999)
            product["recommended"] = request.form.get("recommended") == "on"
            product["sold_out"] = request.form.get("sold_out") == "on"
            product["active"] = request.form.get("active") == "on"
            break

    save_products(products)
    return redirect(url_for("products_admin"))


@app.post("/admin/products/add")
def add_product():
    if get_settings().get("accepting_orders"):
        return redirect(url_for("admin", skip_entry="1"))

    products = get_products(include_inactive=True)
    new_product = {
        "id": next_product_id(products),
        "name": request.form.get("name", "").strip() or "商品名未設定",
        "unit": request.form.get("unit", "").strip() or "内容未設定",
        "price": safe_int(request.form.get("price"), 0, minimum=0),
        "max_quantity": safe_int(request.form.get("max_quantity"), 5, minimum=1, maximum=99),
        "category": request.form.get("category", "").strip() or "その他",
        "sort_order": safe_int(request.form.get("sort_order"), 999),
        "recommended": request.form.get("recommended") == "on",
        "sold_out": request.form.get("sold_out") == "on",
        "active": request.form.get("active") == "on",
    }
    products.append(new_product)
    save_products(products)
    return redirect(url_for("products_admin"))


@app.post("/admin/products/<int:product_id>/delete")
def delete_product(product_id: int):
    if get_settings().get("accepting_orders"):
        return redirect(url_for("admin", skip_entry="1"))

    products = [product for product in get_products(include_inactive=True) if safe_int(product.get("id"), 0) != product_id]
    save_products(products)
    return redirect(url_for("products_admin"))


# -----------------------------
# Reset helpers
# -----------------------------

@app.post("/admin/reset/orders")
def reset_orders():
    save_json(ORDERS_FILE, [])
    return redirect(url_for("admin", skip_entry="1"))


@app.post("/admin/reset/tables")
def reset_tables():
    save_json(TABLE_SESSIONS_FILE, {})
    save_json(CARTS_FILE, {})
    return redirect(url_for("admin", skip_entry="1"))


if __name__ == "__main__":
    ensure_data_files()
    app.run(host="0.0.0.0", port=PORT, debug=True, threaded=True)
