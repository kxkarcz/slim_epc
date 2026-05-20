import pytest
from pydantic import ValidationError
 
from epc.models import (
    BearerConfig,
    ThroughputStats,
    UEState,
    AttachUERequest,
    AddBearerRequest,
    StartTrafficRequest,
    AttachResponse,
    BearerAddResponse,
    BearerDeleteResponse,
    TrafficStartResponse,
    TrafficStatsResponse,
    TrafficStopResponse,
    UEDisplayResponse,
    UEListResponse,
    AggregatedStatsResponse,
    StatusResponse,  
    DetachResponse
)

# --- BearerConfig ---

@pytest.mark.parametrize("bid", [1, 5, 9])
def test_bearer_config_accepts_valid_bearer_id(bid):
    model = BearerConfig(bearer_id=bid)
    assert model.bearer_id == bid
 
 
@pytest.mark.parametrize("bid", [0, 10, -1])
def test_bearer_config_rejects_invalid_bearer_id(bid):
    with pytest.raises(ValidationError):
        BearerConfig(bearer_id=bid)
 
 
@pytest.mark.parametrize("proto", ["tcp", "udp"])
def test_bearer_config_accepts_valid_protocol(proto):
    model = BearerConfig(bearer_id=1, protocol=proto)
    assert model.protocol == proto
 
 
@pytest.mark.parametrize("proto", ["TCP", "UDP", "http", ""])
def test_bearer_config_rejects_invalid_protocol(proto):
    with pytest.raises(ValidationError):
        BearerConfig(bearer_id=1, protocol=proto)
 
 
def test_bearer_config_defaults():
    model = BearerConfig(bearer_id=1)
    assert model.protocol is None
    assert model.target_bps is None
    assert model.active is False

# --- ThroughputStats ---

def test_throughput_stats_invalid_types():
    with pytest.raises(ValidationError):
        ThroughputStats(bearer_id="invalid", ue_id=10)
    with pytest.raises(ValidationError):
        ThroughputStats(bearer_id=1, ue_id="invalid")

def test_throughput_stats_zero_bytes():
    model = ThroughputStats(bearer_id=1, ue_id=10, bytes_tx=0, bytes_rx=0)
    assert model.bytes_tx == 0
    assert model.bytes_rx == 0

def test_throughput_stats_defaults():
    model = ThroughputStats(bearer_id=1, ue_id=10)
    assert model.bytes_tx == 0
    assert model.bytes_rx == 0
    assert model.start_ts is None
    assert model.last_update_ts is None
 
def test_throughput_stats_requires_ue_id():
    with pytest.raises(ValidationError):
        ThroughputStats(bearer_id=1)
 
def test_throughput_stats_requires_bearer_id():
    with pytest.raises(ValidationError):
        ThroughputStats(ue_id=1)

# --- UEState ---
 
@pytest.mark.parametrize("uid", [1, 34, 100])
def test_ue_state_accepts_valid_ue_id(uid):
    model = UEState(ue_id=uid)
    assert model.ue_id == uid
 
 
@pytest.mark.parametrize("uid", [0, 101, -1])
def test_ue_state_rejects_invalid_ue_id(uid):
    with pytest.raises(ValidationError):
        UEState(ue_id=uid)
 
 
def test_ue_state_bearers_none_becomes_empty_dict():
    model = UEState(ue_id=1, bearers=None)
    assert model.bearers == {}
 
 
def test_ue_state_stats_none_becomes_empty_dict():
    model = UEState(ue_id=1, stats=None)
    assert model.stats == {}
 
 
def test_ue_state_defaults_to_empty_dicts():
    model = UEState(ue_id=1)
    assert model.bearers == {}
    assert model.stats == {}
 
 
# --- AttachUERequest ---
 
@pytest.mark.parametrize("uid", [1, 11, 76, 100])
def test_attach_request_accepts_valid_range(uid):
    model = AttachUERequest(ue_id=uid)
    assert model.ue_id == uid
 
 
@pytest.mark.parametrize("uid", [0, 101])
def test_attach_request_rejects_out_of_range(uid):
    with pytest.raises(ValidationError):
        AttachUERequest(ue_id=uid)
 
 
# --- AddBearerRequest ---
 
@pytest.mark.parametrize("bid", [1, 5, 9])
def test_add_bearer_request_accepts_valid_range(bid):
    model = AddBearerRequest(bearer_id=bid)
    assert model.bearer_id == bid
 
 
@pytest.mark.parametrize("bid", [0, 10])
def test_add_bearer_request_rejects_out_of_range(bid):
    with pytest.raises(ValidationError):
        AddBearerRequest(bearer_id=bid)
 
 
# --- StartTrafficRequest ---
 
@pytest.mark.parametrize("proto", ["tcp", "udp"])
def test_start_traffic_accepts_valid_protocol(proto):
    model = StartTrafficRequest(protocol=proto, Mbps=1.0)
    assert model.protocol == proto
 
 
@pytest.mark.parametrize("proto", ["TCP", "UDP", "http", ""])
def test_start_traffic_rejects_invalid_protocol(proto):
    with pytest.raises(ValidationError):
        StartTrafficRequest(protocol=proto, Mbps=1.0)
 
 
def test_start_traffic_requires_exactly_one_throughput_field():
    with pytest.raises(ValidationError, match="exactly one"):
        StartTrafficRequest(protocol="tcp")
 
 
def test_start_traffic_rejects_all_throughput_fields():
    with pytest.raises(ValidationError, match="exactly one"):
        StartTrafficRequest(protocol="tcp", Mbps=1.0, kbps=1000.0, bps=1_000_000)
 
 
def test_start_traffic_target_bps_from_mbps():
    model = StartTrafficRequest(protocol="tcp", Mbps=10.0)
    assert model.target_bps() == 10_000_000
 
 
def test_start_traffic_target_bps_from_kbps():
    model = StartTrafficRequest(protocol="tcp", kbps=500.0)
    assert model.target_bps() == 500_000
 
 
def test_start_traffic_target_bps_from_bps():
    model = StartTrafficRequest(protocol="tcp", bps=12345.0)
    assert model.target_bps() == 12345
 
 
# --- AttachResponse ---
 
def test_attach_response_fields():
    model = AttachResponse(status="ok", ue_id=5)
    assert model.status == "ok"
    assert model.ue_id == 5
 
# --- BearerResponses ---

def test_bearer_add_response_fields():
    model = BearerAddResponse(status="ok", ue_id=3, bearer_id=2)
    assert model.bearer_id == 2

def test_bearer_delete_response_fields():
    model = BearerDeleteResponse(status="deleted", ue_id=1, bearer_id=1)
    assert model.status == "deleted"
 
# --- TrafficResponses ---

def test_traffic_start_response_fields():
    model = TrafficStartResponse(status="started", ue_id=1, bearer_id=3, target_bps=5_000_000)
    assert model.target_bps == 5_000_000
 
 
def test_traffic_stop_response_fields():
    model = TrafficStopResponse(status="stopped", ue_id=2, bearer_id=1)
    assert model.ue_id == 2
 
 
def test_traffic_stats_response_optional_fields_default_to_none():
    model = TrafficStatsResponse(ue_id=1, bearer_id=1, tx_bps=0, rx_bps=0, duration=0.0)
    assert model.protocol is None
    assert model.target_bps is None
 
 
def test_traffic_stats_response_requires_duration():
    with pytest.raises(ValidationError):
        TrafficStatsResponse(ue_id=1, bearer_id=1, tx_bps=0, rx_bps=0)
 
# --- UEResponses ---

def test_ue_display_response_inherits_ue_state_validation():
    with pytest.raises(ValidationError):
        UEDisplayResponse(ue_id=0)
 
 
def test_ue_list_response_accepts_empty_list():
    model = UEListResponse(ues=[])
    assert model.ues == []
 
 
def test_ue_list_response_with_items():
    model = UEListResponse(ues=[1, 2, 3])
    assert model.ues == [1, 2, 3]
 
# --- AggregateStatsResponses ---

def test_aggregated_stats_details_defaults_to_none():
    model = AggregatedStatsResponse(
        scope="all", ue_count=2, bearer_count=4, total_tx_bps=1000, total_rx_bps=2000
    )
    assert model.details is None
 
 
def test_aggregated_stats_accepts_details():
    details = {"ue:1": {"bearer:1": 500}}
    model = AggregatedStatsResponse(
        scope="ue:1", ue_count=1, bearer_count=1,
        total_tx_bps=500, total_rx_bps=500, details=details,
    )
    assert model.details == details

# --- StatusResponse ---

def test_status_response_fields():
    model = StatusResponse(status="success")
    assert model.status == "success"

# --- DetachResponse ---

def test_detach_response_fields():
    model = DetachResponse(status="detached", ue_id=42)
    assert model.status == "detached"
    assert model.ue_id == 42

def test_detach_response_requires_ue_id():
    with pytest.raises(ValidationError):
        DetachResponse(status="detached")
