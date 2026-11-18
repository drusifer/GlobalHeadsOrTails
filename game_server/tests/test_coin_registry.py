"""Coin registry rules: a coin is exactly two tags (heads, tails); tags know nothing about coins."""

import pytest

from game_server.game_state_manager import CoinAssignmentError, SqliteGameStateManager

H = "04A1B2C3D4E5F6"
T = "04A1B2C3D4E5F7"
H2 = "04A1B2C3D4E5F8"
T2 = "04A1B2C3D4E5F9"


@pytest.fixture
def mgr(tmp_path):
    return SqliteGameStateManager(db_path=str(tmp_path / "app.db"))


def test_a_coin_has_one_heads_tag_and_one_tails_tag(mgr):
    mgr.set_coin(H, "SWIFT-FALCON", outcome="heads")
    mgr.set_coin(T, "SWIFT-FALCON", outcome="tails")
    assert mgr.get_side(H) == "heads" and mgr.get_side(T) == "tails"
    coin = mgr.get_coin_admin("SWIFT-FALCON")
    assert (coin["heads_uid"], coin["tails_uid"]) == (H, T)


def test_second_heads_tag_for_a_coin_is_refused_naming_coin_side_and_existing_uid(mgr):
    mgr.set_coin(H, "SWIFT-FALCON", outcome="heads")
    with pytest.raises(CoinAssignmentError) as e:
        mgr.set_coin(H2, "swift-falcon", outcome="heads")
    msg = str(e.value)
    assert "SWIFT-FALCON" in msg.upper() and "heads" in msg and H in msg
    assert mgr.get_coin(H2) is None


def test_a_tag_cannot_be_moved_onto_another_coin(mgr):
    mgr.set_coin(H, "SWIFT-FALCON", outcome="heads")
    with pytest.raises(CoinAssignmentError, match="already assigned to coin 'SWIFT-FALCON'"):
        mgr.set_coin(H, "IRON-OWL", outcome="heads")
    assert mgr.get_coin(H)["coin_name"] == "SWIFT-FALCON"


def test_both_sides_of_a_coin_cannot_be_the_same_tag(mgr):
    with pytest.raises(ValueError, match="cannot be the same"):
        mgr.create_coin("SWIFT-FALCON", H, H)


def test_reassigning_the_same_tag_to_the_same_side_is_a_no_op(mgr):
    mgr.set_coin(H, "SWIFT-FALCON", outcome="heads")
    mgr.set_coin(H, "SWIFT-FALCON", outcome="heads")
    assert mgr.get_side(H) == "heads"


def test_outcome_must_be_heads_tails_or_empty(mgr):
    with pytest.raises(CoinAssignmentError, match="heads or tails"):
        mgr.set_coin(H, "SWIFT-FALCON", outcome="sideways")


def test_unknown_tag_is_unassigned_not_heads_or_tails(mgr):
    assert mgr.get_side(H) == "unassigned"
    mgr.set_coin(H, "SWIFT-FALCON", outcome="heads")
    assert mgr.get_side(T) == "unassigned"


def test_tag_with_a_name_but_no_side_is_unassigned(mgr):
    mgr.set_coin(H, "SWIFT-FALCON")
    assert mgr.get_side(H) == "unassigned"


def test_import_from_key_csv_rows_carries_names_and_sides_over(mgr):
    rows = [(H, "SWIFT-FALCON", "heads"), (T, "SWIFT-FALCON", "tails"), (H2, "", "invalid"), (T2, "IRON-OWL", "")]
    report = mgr.import_coin_assignments(rows)
    assert report["imported"] == 2 and report["skipped"] == 2 and report["conflicts"] == []
    assert mgr.get_side(H) == "heads" and mgr.get_side(T) == "tails"
    # idempotent
    assert mgr.import_coin_assignments(rows)["conflicts"] == []


def test_import_reports_conflicts_instead_of_overwriting(mgr):
    mgr.set_coin(H, "SWIFT-FALCON", outcome="heads")
    report = mgr.import_coin_assignments([(H2, "SWIFT-FALCON", "heads")])
    assert len(report["conflicts"]) == 1 and H in report["conflicts"][0]
    assert mgr.get_coin(H2) is None


def test_startup_carries_key_csv_coin_data_into_the_registry(tmp_path):
    from game_server.app import create_app

    csv_path = tmp_path / "keys.csv"
    csv_path.write_text(
        "uid,picc_master_key,app_read_key,sdm_mac_key,outcome,coin_name,provisioned_date,status,notes,last_used_date\n"
        f"{H},{'0' * 32},{'0' * 32},{'1' * 32},heads,SWIFT-FALCON,2026-01-01,provisioned,,\n"
        f"{T},{'0' * 32},{'0' * 32},{'2' * 32},tails,SWIFT-FALCON,2026-01-01,provisioned,,\n"
    )
    app = create_app(key_csv_path=str(csv_path), db_path=str(tmp_path / "app.db"))
    gm = app.game_manager
    assert gm.get_side(H) == "heads" and gm.get_side(T) == "tails"
