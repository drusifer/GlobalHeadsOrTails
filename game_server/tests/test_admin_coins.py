"""Tests for game_server coin administration database methods and API."""

import pytest
import sqlite3
from pathlib import Path
from game_server.game_state_manager import (
    SqliteGameStateManager,
    validate_coin_name,
    validate_uid,
)


@pytest.fixture
def temp_db(tmp_path: Path):
    db_path = str(tmp_path / "test_app.db")
    mgr = SqliteGameStateManager(db_path=db_path)
    return mgr


def test_validation_helpers():
    # Valid UIDs
    assert validate_uid("04A1B2C3D4E5F6") == "04A1B2C3D4E5F6"
    assert validate_uid("04a1b2c3d4e5f6") == "04A1B2C3D4E5F6"
    assert validate_uid("  04A1B2C3D4E5F6  ") == "04A1B2C3D4E5F6"

    # Invalid UIDs
    with pytest.raises(ValueError, match="14 hex characters"):
        validate_uid("04A1B2")
    with pytest.raises(ValueError, match="14 hex characters"):
        validate_uid("04A1B2C3D4E5F678")
    with pytest.raises(ValueError, match="hexadecimal"):
        validate_uid("04A1B2C3D4E5ZZ")

    # Valid coin names
    assert validate_coin_name("TWIN-STARS") == "TWIN-STARS"
    assert validate_coin_name("Bronze Eagle") == "Bronze Eagle"
    assert validate_coin_name("  SILVER_FOX  ") == "SILVER_FOX"

    # Invalid coin names
    with pytest.raises(ValueError, match="empty"):
        validate_coin_name("   ")
    with pytest.raises(ValueError, match="exceed"):
        validate_coin_name("A" * 65)


def test_create_coin_and_list_admin(temp_db: SqliteGameStateManager):
    coin = temp_db.create_coin(
        coin_name="TWIN-STARS",
        heads_uid="04112233445566",
        tails_uid="04778899AABBCC",
        clan="Ronin",
        rarity="rare",
    )
    assert coin["coin_name"] == "TWIN-STARS"
    assert coin["heads_uid"] == "04112233445566"
    assert coin["tails_uid"] == "04778899AABBCC"
    assert coin["clan"] == "Ronin"
    assert coin["rarity"] == "rare"
    assert coin["is_complete"] is True

    # List admin coins
    admin_list = temp_db.list_coins_admin()
    assert len(admin_list) == 1
    assert admin_list[0]["coin_name"] == "TWIN-STARS"
    assert admin_list[0]["heads_uid"] == "04112233445566"
    assert admin_list[0]["tails_uid"] == "04778899AABBCC"
    assert admin_list[0]["is_complete"] is True
    assert admin_list[0]["total_flips"] == 0


def test_create_coin_validation_errors(temp_db: SqliteGameStateManager):
    temp_db.create_coin(
        coin_name="COIN-ONE",
        heads_uid="04111111111111",
        tails_uid="04222222222222",
    )

    # Duplicate coin name
    with pytest.raises(ValueError, match="already exists"):
        temp_db.create_coin(
            coin_name="COIN-ONE",
            heads_uid="04333333333333",
            tails_uid="04444444444444",
        )

    # Same UID for heads and tails
    with pytest.raises(ValueError, match="cannot be the same"):
        temp_db.create_coin(
            coin_name="COIN-TWO",
            heads_uid="04555555555555",
            tails_uid="04555555555555",
        )

    # Reusing existing UID assigned to another coin
    with pytest.raises(ValueError, match="already assigned"):
        temp_db.create_coin(
            coin_name="COIN-THREE",
            heads_uid="04111111111111",
            tails_uid="04666666666666",
        )


def test_update_coin(temp_db: SqliteGameStateManager):
    temp_db.create_coin(
        coin_name="MY-COIN",
        heads_uid="04AAAAAAAAAAAA",
        tails_uid="04BBBBBBBBBBBB",
        clan="Shadow",
        rarity="common",
    )

    # Update metadata and swap tails UID
    updated = temp_db.update_coin(
        old_coin_name="MY-COIN",
        new_coin_name="RENAMED-COIN",
        heads_uid="04AAAAAAAAAAAA",
        tails_uid="04CCCCCCCCCCCC",
        clan="Iron",
        rarity="legendary",
    )
    assert updated["coin_name"] == "RENAMED-COIN"
    assert updated["tails_uid"] == "04CCCCCCCCCCCC"
    assert updated["clan"] == "Iron"
    assert updated["rarity"] == "legendary"

    # Verify old name is gone and new name is listed
    coins = temp_db.list_coins_admin()
    assert len(coins) == 1
    assert coins[0]["coin_name"] == "RENAMED-COIN"
    assert coins[0]["tails_uid"] == "04CCCCCCCCCCCC"


def test_delete_coin(temp_db: SqliteGameStateManager):
    temp_db.create_coin(
        coin_name="DOOMED-COIN",
        heads_uid="04D1D1D1D1D1D1",
        tails_uid="04D2D2D2D2D2D2",
    )
    assert len(temp_db.list_coins_admin()) == 1

    deleted = temp_db.delete_coin("DOOMED-COIN")
    assert deleted is True
    assert len(temp_db.list_coins_admin()) == 0

    # Non-existent delete returns False
    assert temp_db.delete_coin("NON-EXISTENT") is False


def test_list_coins_admin_with_flip_stats(temp_db: SqliteGameStateManager):
    temp_db.create_coin(
        coin_name="LUCKY-PENNY",
        heads_uid="04EEEEEEEEEEEE",
        tails_uid="04FFFFFFFFFFFF",
    )

    # Insert some scan logs
    with temp_db._get_conn() as conn:
        conn.execute(
            "INSERT INTO scan_logs (uid, counter, outcome, coin_name) VALUES (?, ?, ?, ?)",
            ("04EEEEEEEEEEEE", 1, "heads", "LUCKY-PENNY"),
        )
        conn.execute(
            "INSERT INTO scan_logs (uid, counter, outcome, coin_name) VALUES (?, ?, ?, ?)",
            ("04EEEEEEEEEEEE", 2, "heads", "LUCKY-PENNY"),
        )
        conn.execute(
            "INSERT INTO scan_logs (uid, counter, outcome, coin_name) VALUES (?, ?, ?, ?)",
            ("04FFFFFFFFFFFF", 1, "tails", "LUCKY-PENNY"),
        )
        conn.commit()

    coins = temp_db.list_coins_admin()
    assert len(coins) == 1
    c = coins[0]
    assert c["total_flips"] == 3
    assert c["heads_flips"] == 2
    assert c["tails_flips"] == 1


# --- Flask Client API Tests ---

@pytest.fixture
def test_app(tmp_path: Path, monkeypatch):
    from game_server.app import create_app
    csv_file = tmp_path / "tag_keys.csv"
    csv_file.write_text("uid,key,asset_tag,outcome,coin_name\n", encoding="utf-8")
    db_file = tmp_path / "app.db"

    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    app = create_app(
        key_csv_path=str(csv_file),
        db_path=str(db_file),
    )
    app.config["TESTING"] = True
    return app


def test_api_admin_coins_crud_flow(test_app):
    client = test_app.test_client()

    # 1. List initially empty
    resp = client.get("/api/admin/coins")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["coins"] == []
    assert data["total"] == 0

    # 2. Create coin
    payload = {
        "coin_name": "PHOENIX-COIN",
        "heads_uid": "04123456789ABC",
        "tails_uid": "04FEDCBA987654",
        "clan": "Mystic",
        "rarity": "epic",
    }
    resp = client.post("/api/admin/coins", json=payload)
    assert resp.status_code == 201
    created = resp.get_json()["coin"]
    assert created["coin_name"] == "PHOENIX-COIN"
    assert created["heads_uid"] == "04123456789ABC"
    assert created["tails_uid"] == "04FEDCBA987654"
    assert created["is_complete"] is True

    # 3. Get single coin
    resp = client.get("/api/admin/coins/PHOENIX-COIN")
    assert resp.status_code == 200
    coin_data = resp.get_json()["coin"]
    assert coin_data["coin_name"] == "PHOENIX-COIN"

    # 4. Update coin
    update_payload = {
        "new_coin_name": "PHOENIX-PRIME",
        "heads_uid": "04123456789ABC",
        "tails_uid": "04AABBCCDDEEFF",
        "clan": "Solar",
        "rarity": "legendary",
    }
    resp = client.put("/api/admin/coins/PHOENIX-COIN", json=update_payload)
    assert resp.status_code == 200
    updated = resp.get_json()["coin"]
    assert updated["coin_name"] == "PHOENIX-PRIME"
    assert updated["tails_uid"] == "04AABBCCDDEEFF"
    assert updated["rarity"] == "legendary"

    # 5. Delete coin
    resp = client.delete("/api/admin/coins/PHOENIX-PRIME")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "deleted"

    # 6. Verify deleted (404)
    resp = client.get("/api/admin/coins/PHOENIX-PRIME")
    assert resp.status_code == 404


def test_api_admin_security_token(test_app, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "super-secret-123")
    client = test_app.test_client()

    # Unauthorized: no token provided
    resp = client.get("/api/admin/coins")
    assert resp.status_code == 401
    assert "Unauthorized" in resp.get_json()["error"]

    # Unauthorized: wrong token
    resp = client.get("/api/admin/coins", headers={"X-Admin-Token": "wrong-token"})
    assert resp.status_code == 401

    # Authorized: via X-Admin-Token header
    resp = client.get("/api/admin/coins", headers={"X-Admin-Token": "super-secret-123"})
    assert resp.status_code == 200

    # Authorized: via query parameter ?token=
    resp = client.get("/api/admin/coins?token=super-secret-123")
    assert resp.status_code == 200

    # Authorized: via Bearer header
    resp = client.get("/api/admin/coins", headers={"Authorization": "Bearer super-secret-123"})
    assert resp.status_code == 200


def test_web_admin_flow(test_app):
    client = test_app.test_client()

    # 1. /admin redirects to /admin/coins
    resp = client.get("/admin")
    assert resp.status_code == 302
    assert "/admin/coins" in resp.headers["Location"]

    # 2. Render /admin/coins
    resp = client.get("/admin/coins")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Coin Registry &amp; Administration" in html or "Coin Registry & Administration" in html
    assert "Register New Coin" in html

    # 3. Create coin via web form POST
    form_data = {
        "coin_name": "GOLDEN-HAWK",
        "heads_uid": "04112233445566",
        "tails_uid": "04778899AABBCC",
        "clan": "Solar",
        "rarity": "rare",
    }
    resp = client.post("/admin/coins/create", data=form_data, follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "GOLDEN-HAWK" in html
    assert "Solar" in html
    assert "Paired" in html

    # 4. Update coin via web form POST
    update_data = {
        "new_coin_name": "GOLDEN-EAGLE",
        "heads_uid": "04112233445566",
        "tails_uid": "04778899AABBCC",
        "clan": "Thunder",
        "rarity": "epic",
    }
    resp = client.post("/admin/coins/GOLDEN-HAWK/update", data=update_data, follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "GOLDEN-EAGLE" in html
    assert "Thunder" in html

    # 5. Delete coin via web form POST
    resp = client.post("/admin/coins/GOLDEN-EAGLE/delete", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "deleted successfully" in html


