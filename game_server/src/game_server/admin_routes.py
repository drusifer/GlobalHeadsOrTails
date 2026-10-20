"""Admin blueprint providing security and endpoints for coin management."""

import logging
import os
from functools import wraps
from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

log = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__)


def require_admin_token(f):
    """Decorator guarding admin endpoints with ADMIN_TOKEN verification.

    Checks:
    1. X-Admin-Token request header
    2. Bearer Authorization header
    3. admin_token cookie
    4. token query parameter
    If ADMIN_TOKEN is unset in environment, permits dev-mode access with debug logging.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        configured_token = os.getenv("ADMIN_TOKEN", "").strip()
        if not configured_token:
            log.debug("[ADMIN AUTH] No ADMIN_TOKEN configured in environment; allowing access (dev mode)")
            return f(*args, **kwargs)

        provided_token = (
            request.headers.get("X-Admin-Token")
            or request.cookies.get("admin_token")
            or request.args.get("token")
            or ""
        ).strip()

        if not provided_token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                provided_token = auth_header[7:].strip()

        if not provided_token or provided_token != configured_token:
            log.warning(
                "[ADMIN AUTH] Unauthorized access attempt to %s from %s",
                request.path,
                request.remote_addr,
            )
            is_json_request = (
                request.path.startswith("/api/")
                or request.is_json
                or "application/json" in request.headers.get("Accept", "")
            )
            if is_json_request:
                return jsonify({"error": "Unauthorized: invalid or missing admin token"}), 401
            return render_template(
                "admin_coins.html",
                error="Unauthorized: Please provide a valid admin token (e.g. ?token=...)",
                coins=[],
                summary={"total_coins": 0, "complete_coins": 0, "incomplete_coins": 0, "total_flips": 0},
            ), 401

        return f(*args, **kwargs)

    return decorated_function


TWELVE_CLANS = [
    "Ronin",
    "Iron",
    "Mystic",
    "Solar",
    "Lunar",
    "Shadow",
    "Thunder",
    "Ocean",
    "Forest",
    "Ember",
    "Frost",
    "Wind",
]


# --- Web Interface Routes ---

@admin_bp.route("/admin", methods=["GET"])
def web_admin_redirect():
    """Redirects /admin to /admin/coins preserving token query param."""
    token = request.args.get("token")
    if token:
        return redirect(url_for("admin.web_coins", token=token))
    return redirect(url_for("admin.web_coins"))


@admin_bp.route("/admin/coins", methods=["GET"])
@require_admin_token
def web_coins():
    """Renders the coin administration dashboard."""
    coins = current_app.game_manager.list_coins_admin()
    summary = {
        "total_coins": len(coins),
        "complete_coins": sum(1 for c in coins if c["is_complete"]),
        "incomplete_coins": sum(1 for c in coins if not c["is_complete"]),
        "total_flips": sum(c.get("total_flips", 0) for c in coins),
    }
    return render_template(
        "admin_coins.html",
        coins=coins,
        summary=summary,
        clans=TWELVE_CLANS,
        token=request.args.get("token", ""),
    )


@admin_bp.route("/admin/coins/create", methods=["POST"])
@require_admin_token
def web_create_coin():
    """Web form submission handler to register a new coin."""
    coin_name = request.form.get("coin_name", "").strip()
    heads_uid = request.form.get("heads_uid", "").strip()
    tails_uid = request.form.get("tails_uid", "").strip()
    clan = request.form.get("clan", "").strip()
    rarity = request.form.get("rarity", "common").strip()
    token = request.args.get("token", "")

    try:
        current_app.game_manager.create_coin(
            coin_name=coin_name,
            heads_uid=heads_uid,
            tails_uid=tails_uid,
            clan=clan,
            rarity=rarity,
        )
        flash(f"Coin '{coin_name}' created successfully!", "success")
    except ValueError as exc:
        flash(f"Error creating coin: {exc}", "error")

    redirect_url = url_for("admin.web_coins", token=token) if token else url_for("admin.web_coins")
    return redirect(redirect_url)


@admin_bp.route("/admin/coins/<coin_name>/update", methods=["POST"])
@require_admin_token
def web_update_coin(coin_name: str):
    """Web form submission handler to update an existing coin."""
    new_coin_name = request.form.get("new_coin_name", coin_name).strip()
    heads_uid = request.form.get("heads_uid", "").strip()
    tails_uid = request.form.get("tails_uid", "").strip()
    clan = request.form.get("clan", "").strip()
    rarity = request.form.get("rarity", "common").strip()
    token = request.args.get("token", "")

    try:
        current_app.game_manager.update_coin(
            old_coin_name=coin_name,
            new_coin_name=new_coin_name,
            heads_uid=heads_uid,
            tails_uid=tails_uid,
            clan=clan,
            rarity=rarity,
        )
        flash(f"Coin '{new_coin_name}' updated successfully!", "success")
    except ValueError as exc:
        flash(f"Error updating coin: {exc}", "error")

    redirect_url = url_for("admin.web_coins", token=token) if token else url_for("admin.web_coins")
    return redirect(redirect_url)


@admin_bp.route("/admin/coins/<coin_name>/delete", methods=["POST"])
@require_admin_token
def web_delete_coin(coin_name: str):
    """Web form submission handler to delete a coin."""
    token = request.args.get("token", "")
    deleted = current_app.game_manager.delete_coin(coin_name)
    if deleted:
        flash(f"Coin '{coin_name}' deleted successfully.", "info")
    else:
        flash(f"Coin '{coin_name}' not found.", "error")

    redirect_url = url_for("admin.web_coins", token=token) if token else url_for("admin.web_coins")
    return redirect(redirect_url)


# --- REST API Endpoints ---

@admin_bp.route("/api/admin/coins", methods=["GET"])
@require_admin_token
def api_list_coins():
    """Lists all paired coin definitions and statistics."""
    coins = current_app.game_manager.list_coins_admin()
    return jsonify({"coins": coins, "total": len(coins)}), 200


@admin_bp.route("/api/admin/coins/<coin_name>", methods=["GET"])
@require_admin_token
def api_get_coin(coin_name: str):
    """Retrieves single coin details."""
    coin = current_app.game_manager.get_coin_admin(coin_name)
    if not coin:
        return jsonify({"error": f"Coin '{coin_name}' not found"}), 404
    return jsonify({"coin": coin}), 200


@admin_bp.route("/api/admin/coins", methods=["POST"])
@require_admin_token
def api_create_coin():
    """Creates a new coin with heads and tails face UIDs."""
    payload = request.get_json(silent=True) or request.form.to_dict()
    coin_name = (payload.get("coin_name") or "").strip()
    heads_uid = (payload.get("heads_uid") or "").strip()
    tails_uid = (payload.get("tails_uid") or "").strip()
    clan = (payload.get("clan") or "").strip()
    rarity = (payload.get("rarity") or "common").strip()

    if not coin_name or not heads_uid or not tails_uid:
        return jsonify({"error": "coin_name, heads_uid, and tails_uid are required"}), 400

    try:
        coin = current_app.game_manager.create_coin(
            coin_name=coin_name,
            heads_uid=heads_uid,
            tails_uid=tails_uid,
            clan=clan,
            rarity=rarity,
        )
        log.info("[ADMIN] Created new coin: %s (H:%s, T:%s)", coin_name, heads_uid, tails_uid)
        return jsonify({"status": "created", "coin": coin}), 201
    except ValueError as exc:
        msg = str(exc)
        status_code = 409 if "already exists" in msg or "already assigned" in msg else 400
        return jsonify({"error": msg}), status_code


@admin_bp.route("/api/admin/coins/<coin_name>", methods=["PUT"])
@require_admin_token
def api_update_coin(coin_name: str):
    """Updates an existing coin definition."""
    payload = request.get_json(silent=True) or request.form.to_dict()
    new_coin_name = (payload.get("new_coin_name") or payload.get("coin_name") or coin_name).strip()
    heads_uid = (payload.get("heads_uid") or "").strip()
    tails_uid = (payload.get("tails_uid") or "").strip()
    clan = (payload.get("clan") or "").strip()
    rarity = (payload.get("rarity") or "common").strip()

    if not heads_uid or not tails_uid:
        return jsonify({"error": "heads_uid and tails_uid are required"}), 400

    try:
        updated = current_app.game_manager.update_coin(
            old_coin_name=coin_name,
            new_coin_name=new_coin_name,
            heads_uid=heads_uid,
            tails_uid=tails_uid,
            clan=clan,
            rarity=rarity,
        )
        log.info("[ADMIN] Updated coin %s -> %s", coin_name, new_coin_name)
        return jsonify({"status": "updated", "coin": updated}), 200
    except ValueError as exc:
        msg = str(exc)
        status_code = 404 if "not found" in msg.lower() else (409 if "already exists" in msg or "already assigned" in msg else 400)
        return jsonify({"error": msg}), status_code


@admin_bp.route("/api/admin/coins/<coin_name>", methods=["DELETE"])
@require_admin_token
def api_delete_coin(coin_name: str):
    """Deletes coin identity records."""
    deleted = current_app.game_manager.delete_coin(coin_name)
    if not deleted:
        return jsonify({"error": f"Coin '{coin_name}' not found"}), 404
    log.info("[ADMIN] Deleted coin: %s", coin_name)
    return jsonify({"status": "deleted", "coin_name": coin_name}), 200


def register_admin_routes(app) -> None:
    """Registers the admin blueprint on the Flask app."""
    app.register_blueprint(admin_bp)
