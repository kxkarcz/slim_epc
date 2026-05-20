import pytest
from epc.db import EPCRepository
from epc.models import BearerConfig, ThroughputStats


@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / "test_epc.db"
    return EPCRepository(db_path=str(db_file))


def test_repository_ue_exists(repo):
    assert repo.ue_exists(9) is False
    repo.attach_ue(9)
    assert repo.ue_exists(9) is True

def test_attach_existing_raises(repo):
    repo.attach_ue(9)
    with pytest.raises(ValueError, match="UE already attached"):
        repo.attach_ue(9)

def test_list(repo):
    repo.attach_ue(5)
    repo.attach_ue(2)
    assert list(repo.list_ues()) == [2, 5]

def test_detach_ue(repo):
    assert repo.ue_exists(9) is False
    repo.attach_ue(9)
    assert repo.ue_exists(9) is True
    repo.detach_ue(9)
    assert repo.ue_exists(9) is False

def test_detach_ue_not_found(repo):
    with pytest.raises(ValueError, match="UE not found"):
        repo.detach_ue(9)

def test_save_ue(repo):
    repo.attach_ue(1)
    state = repo.get_ue(1)
    assert state.ue_id == 1
    state.bearers[1] = BearerConfig(bearer_id=1, protocol="tcp", active=True)
    repo.save_ue(state)
    loaded = repo.get_ue(1)
    assert loaded.ue_id == 1
    assert 1 in loaded.bearers
    assert loaded.bearers[1].protocol == "tcp"
    assert loaded.bearers[1].active is True

def test_get_ue_not_found(repo):
    with pytest.raises(ValueError, match="UE not found"):
        repo.get_ue(1)

def test_add_bearer(repo):
    repo.attach_ue(9)
    repo.add_bearer(9, 1)
    s = repo.get_ue(9)
    assert 1 in s.bearers

def test_add_bearer_exists(repo):
    repo.attach_ue(9)
    repo.add_bearer(9, 1)
    with pytest.raises(ValueError, match="Bearer already exists"):
        repo.add_bearer(9, 1)

def test_update_bearer(repo):
    repo.attach_ue(9)
    repo.add_bearer(9, 1)
    state = repo.get_ue(9)
    state.bearers[1].active = True
    repo.update_bearer(9, BearerConfig(bearer_id=1, protocol="udp", active=False))
    loaded = repo.get_ue(9)
    assert loaded.bearers[1].protocol == "udp"
    assert loaded.bearers[1].active is False

@pytest.mark.parametrize("initial,update,expected_tx", [
    (100, 300, 300),
    (0, 50, 50),
    (10, 10, 10)
])
def test_update_stats_overwrite(repo, initial, update, expected_tx):
    repo.attach_ue(3)
    repo.update_stats(3, ThroughputStats(bearer_id=9, ue_id=3, bytes_tx=initial, bytes_rx=0))
    repo.update_stats(3, ThroughputStats(bearer_id=9, ue_id=3, bytes_tx=update, bytes_rx=0))
    assert repo.get_ue(3).stats[9].bytes_tx == expected_tx

def test_reset_all(repo):
    repo.attach_ue(1)
    repo.attach_ue(2)
    assert list(repo.list_ues()) == [1, 2]
    repo.reset_all()
    assert list(repo.list_ues()) == []

def test_delete_bearer(repo):
    repo.attach_ue(4)
    repo.add_bearer(4, 1)
    s = repo.get_ue(4)
    assert 1 in s.bearers
    repo.delete_bearer(4, 1)
    s2 = repo.get_ue(4)
    assert 1 not in s2.bearers

def test_delete_bearer_no_exists(repo):
    repo.attach_ue(4)
    with pytest.raises(ValueError, match="Bearer not found"):
        repo.delete_bearer(4, 1)

def test_delete_default_bearer(repo):
    repo.attach_ue(4)
    with pytest.raises(ValueError, match="Cannot remove default bearer"):
        repo.delete_bearer(4,9)




