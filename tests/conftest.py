from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import epc.api as api
from epc.models import BearerConfig, UEState
from main import app


@pytest.fixture
def fake_repo():
    ues = {}

    def list_ues():
        return iter(sorted(ues))

    def ue_exists(ue_id):
        return ue_id in ues

    def get_ue(ue_id):
        if not ue_exists(ue_id):
            raise ValueError("UE not found")
        return ues[ue_id].model_copy(deep=True)

    def save_ue(state):
        ues[state.ue_id] = state.model_copy(deep=True)

    def attach_ue(ue_id):
        if ue_exists(ue_id):
            raise ValueError("UE already attached")
        state = UEState(ue_id=ue_id)
        state.bearers[9] = BearerConfig(bearer_id=9)
        save_ue(state)

    def detach_ue(ue_id):
        if not ue_exists(ue_id):
            raise ValueError("UE not found")
        del ues[ue_id]

    def add_bearer(ue_id, bearer_id):
        state = get_ue(ue_id)
        if bearer_id in state.bearers:
            raise ValueError("Bearer already exists")
        state.bearers[bearer_id] = BearerConfig(bearer_id=bearer_id)
        save_ue(state)

    def update_bearer(ue_id, bearer):
        state = get_ue(ue_id)
        state.bearers[bearer.bearer_id] = bearer
        save_ue(state)

    def update_stats(ue_id, stats):
        state = get_ue(ue_id)
        state.stats[stats.bearer_id] = stats
        save_ue(state)

    def reset_all():
        ues.clear()

    def delete_bearer(ue_id, bearer_id):
        if bearer_id == 9:
            raise ValueError("Cannot remove default bearer")
        state = get_ue(ue_id)
        if bearer_id not in state.bearers:
            raise ValueError("Bearer not found")
        state.bearers.pop(bearer_id)
        state.stats.pop(bearer_id, None)
        save_ue(state)

    return SimpleNamespace(
        list_ues=list_ues,
        ue_exists=ue_exists,
        get_ue=get_ue,
        save_ue=save_ue,
        attach_ue=attach_ue,
        detach_ue=detach_ue,
        add_bearer=add_bearer,
        update_bearer=update_bearer,
        update_stats=update_stats,
        reset_all=reset_all,
        delete_bearer=delete_bearer,
    )


@pytest.fixture
def fake_traffic_manager():
    running = set()

    def start(ue_id, bearer):
        key = (ue_id, bearer.bearer_id)
        if key in running:
            raise ValueError("Traffic already running")
        if not bearer.target_bps or not bearer.protocol:
            raise ValueError("Bearer not configured for traffic")
        running.add(key)

    def stop(ue_id, bearer_id):
        running.discard((ue_id, bearer_id))

    def stop_all():
        running.clear()

    def is_running(ue_id, bearer_id):
        return (ue_id, bearer_id) in running

    return SimpleNamespace(
        start=start,
        stop=stop,
        stop_all=stop_all,
        is_running=is_running,
    )


@pytest.fixture
def client(fake_repo, fake_traffic_manager, monkeypatch):
    app.dependency_overrides[api.get_repo] = lambda: fake_repo
    monkeypatch.setattr(api, "get_traffic_manager", lambda repo: fake_traffic_manager)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
