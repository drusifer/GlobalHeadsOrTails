"""Opt-in counter consumption on POST /api/v1/validate ("consume": true)."""

import threading
from types import SimpleNamespace

import pytest

from tag_validator.api.app import create_app
from tag_validator.crypto.cmac_engine import calculate_sdm_cmac
from tag_validator.models import TagSecret
from tag_validator.store.base import CounterStoreError
from tag_validator.store.k3s_store import K3sSecretStore
from tag_validator.store.memory_store import MemorySecretStore

from .test_api import TEST_K3, TEST_UID, WsgiTestClient


@pytest.fixture
def client() -> WsgiTestClient:
    store = MemorySecretStore()
    store.save_key(TagSecret(uid=TEST_UID, k3=TEST_K3))
    return WsgiTestClient(create_app(store=store))


def tap(ctr: int, **extra):
    return {"uid": TEST_UID, "counter": ctr, "cmac": calculate_sdm_cmac(TEST_UID, ctr, TEST_K3), **extra}


def test_healthz_advertises_what_this_validator_can_do(client):
    status, body = client.get("/healthz")
    assert status == 200 and body["features"] == ["consume"]
    assert client.get("/health")[1]["features"] == ["consume"]


def test_without_the_flag_nothing_is_recorded_and_the_same_counter_stays_valid(client):
    for _ in range(3):
        status, body = client.post("/api/v1/validate", tap(7))
        assert (status, body["valid"]) == (200, True)
        assert "consumed" not in body


def test_get_never_consumes(client):
    query = f"uid={TEST_UID}&counter=7&cmac={calculate_sdm_cmac(TEST_UID, 7, TEST_K3)}"
    for _ in range(3):
        assert client.get("/api/v1/validate", query_string=query)[1]["valid"] is True
    assert client.post("/api/v1/validate", tap(7, consume=True))[1]["consumed"] is True


def test_consume_true_accepts_a_fresh_counter_and_says_so(client):
    status, body = client.post("/api/v1/validate", tap(5, consume=True))
    assert status == 200 and body["valid"] is True and body["consumed"] is True


def test_the_same_counter_twice_is_a_replay(client):
    assert client.post("/api/v1/validate", tap(5, consume=True))[1]["valid"] is True
    status, body = client.post("/api/v1/validate", tap(5, consume=True))
    assert status == 200
    assert body["valid"] is False and body["reason"] == "replayed" and body["consumed"] is False


def test_an_older_counter_is_a_replay_and_a_newer_one_is_fine(client):
    assert client.post("/api/v1/validate", tap(9, consume=True))[1]["valid"] is True
    assert client.post("/api/v1/validate", tap(8, consume=True))[1]["reason"] == "replayed"
    assert client.post("/api/v1/validate", tap(10, consume=True))[1]["valid"] is True


def test_a_wrong_cmac_never_burns_the_counter(client):
    bad = tap(5, consume=True)
    bad["cmac"] = "0000000000000000"
    status, body = client.post("/api/v1/validate", bad)
    assert body["valid"] is False and body.get("reason") != "replayed" and "consumed" not in body
    assert client.post("/api/v1/validate", tap(5, consume=True))[1]["valid"] is True


@pytest.mark.parametrize("flag", ["true", 1, "yes", None, [True]])
def test_only_a_real_boolean_true_consumes(client, flag):
    client.post("/api/v1/validate", tap(5, consume=flag))
    # nothing was recorded, so a real consume of the same counter still works
    assert client.post("/api/v1/validate", tap(5, consume=True))[1]["valid"] is True


def test_counters_are_per_tag(client):
    other = "04AABBCCDDEEFF"
    client.app.store.save_key(TagSecret(uid=other, k3=TEST_K3))
    assert client.post("/api/v1/validate", tap(5, consume=True))[1]["valid"] is True
    body = {"uid": other, "counter": 5, "cmac": calculate_sdm_cmac(other, 5, TEST_K3), "consume": True}
    assert client.post("/api/v1/validate", body)[1]["valid"] is True


def test_parallel_taps_of_one_counter_win_exactly_once():
    store = MemorySecretStore()
    wins = []
    barrier = threading.Barrier(8)

    def go():
        barrier.wait()
        wins.append(store.consume_counter(TEST_UID, 3))

    threads = [threading.Thread(target=go) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert wins.count(True) == 1


def test_a_store_failure_is_503_and_says_so_not_valid(client, monkeypatch):
    def boom(uid, counter):
        raise CounterStoreError("down")

    monkeypatch.setattr(client.app.store, "consume_counter", boom)
    status, body = client.post("/api/v1/validate", tap(5, consume=True))
    assert status == 503 and body["valid"] is False


# --- the k3s adapter, against a fake Kubernetes API -------------------------------------------

class FakeApiException(Exception):
    def __init__(self, status):
        self.status = status


class FakeV1:
    """Just enough CoreV1Api: secrets with resource versions and 409 on stale replace."""

    def __init__(self):
        self.items = {}
        self.conflicts = 0  # inject this many 409s before a replace succeeds

    def read_namespaced_secret(self, name, namespace):
        if name not in self.items:
            raise FakeApiException(404)
        return self.items[name]

    def create_namespaced_secret(self, namespace, body):
        if body.metadata.name in self.items:
            raise FakeApiException(409)
        body.metadata.resource_version = "1"
        self.items[body.metadata.name] = body

    def replace_namespaced_secret(self, name, namespace, body):
        current = self.items[name]
        if self.conflicts or body.metadata.resource_version != current.metadata.resource_version:
            self.conflicts = max(0, self.conflicts - 1)
            raise FakeApiException(409)
        body.metadata.resource_version = str(int(current.metadata.resource_version) + 1)
        self.items[name] = body


@pytest.fixture
def k3s(monkeypatch):
    from tag_validator.store import k3s_store

    monkeypatch.setattr(k3s_store, "ApiException", FakeApiException)
    monkeypatch.setattr(k3s_store, "K8S_AVAILABLE", True)
    monkeypatch.setattr(
        k3s_store,
        "k8s_client",
        SimpleNamespace(
            V1Secret=lambda **kw: SimpleNamespace(**kw),
            V1ObjectMeta=lambda **kw: SimpleNamespace(**{"resource_version": None, **kw}),
        ),
    )
    store = K3sSecretStore.__new__(K3sSecretStore)
    store.namespace, store._initialized, store._v1 = "tag-secrets", True, FakeV1()
    return store


def test_k3s_counter_lives_in_its_own_secret_and_never_touches_the_key(k3s):
    assert k3s.consume_counter(TEST_UID, 4) is True
    assert list(k3s._v1.items) == [f"tag-ctr-{TEST_UID.lower()}"]
    assert k3s.consume_counter(TEST_UID, 4) is False
    assert k3s.consume_counter(TEST_UID, 3) is False
    assert k3s.consume_counter(TEST_UID, 5) is True


def test_k3s_retries_a_lost_race_and_then_sees_the_replay(k3s):
    assert k3s.consume_counter(TEST_UID, 4) is True
    k3s._v1.conflicts = 1
    assert k3s.consume_counter(TEST_UID, 5) is True
    assert k3s.consume_counter(TEST_UID, 5) is False


def test_k3s_gives_up_loudly_if_it_cannot_settle(k3s):
    assert k3s.consume_counter(TEST_UID, 4) is True
    k3s._v1.conflicts = 99
    with pytest.raises(CounterStoreError):
        k3s.consume_counter(TEST_UID, 5)


def test_k3s_not_initialised_is_a_store_error(k3s):
    k3s._initialized = False
    with pytest.raises(CounterStoreError):
        k3s.consume_counter(TEST_UID, 1)


def test_k3s_two_creators_racing_only_one_wins(k3s):
    first = k3s._v1.create_namespaced_secret
    calls = []

    def racy_create(namespace, body):
        if not calls:  # someone else creates it between our read and our create
            calls.append(1)
            first(namespace, SimpleNamespace(metadata=body.metadata, data={"last": _b64("9")}))
        return first(namespace, body)

    k3s._v1.create_namespaced_secret = racy_create
    assert k3s.consume_counter(TEST_UID, 4) is False  # 4 <= 9 once it re-reads


def _b64(text):
    import base64

    return base64.b64encode(text.encode()).decode()
