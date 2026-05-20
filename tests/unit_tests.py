import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from epc.api import get_ues_stats





# @pytest.fixture
# def mock_repo():
#     repo = MagicMock()
#     # Przykładowe dane mockowe
#     repo.ue_exists.return_value = True
#     repo.list_ues.return_value = [1, 2]
#     mock_ue_state = MagicMock()
#     mock_ue_state.stats = {
#         1: MagicMock(start_ts=1000, last_update_ts=1010, bytes_tx=8000, bytes_rx=8000),  # Duration=10s, BPS=6400
#         2: MagicMock(start_ts=1000, last_update_ts=1010, bytes_tx=4000, bytes_rx=4000),
#     }
#     repo.get_ue.return_value = mock_ue_state
#     return repo
#
#
# @pytest.fixture
# def mock_tm():
#     tm = MagicMock()
#     tm.is_running.return_value = True  # Załóż, że ruch jest aktywny
#     return tm
#
#
# # Testy jednostkowe
# @patch('epc.api.get_traffic_manager')
# def test_get_ues_stats_all_ues(mock_get_tm, mock_repo, mock_tm):
#     mock_get_tm.return_value = mock_tm
#     # Mock time.time() dla przewidywalności
#     with patch('time.time', return_value=1010):
#         response = get_ues_stats(mock_repo, ue_id=None, include_details=False)
#
#     assert response.scope == "all"
#     assert response.ue_count == 2
#     assert response.bearer_count == 4  # 2 UE * 2 bearer'y
#     assert response.total_tx_bps == 12800  # 6400 + 3200 (obliczone z bytes_tx * 8 / duration)
#     assert response.total_rx_bps == 12800
#     assert response.details is None
#
#
# @patch('epc.api.get_traffic_manager')
# def test_get_ues_stats_single_ue(mock_get_tm, mock_repo, mock_tm):
#     mock_get_tm.return_value = mock_tm
#     with patch('time.time', return_value=1010):
#         response = get_ues_stats(mock_repo, ue_id=1, include_details=True)
#
#     assert response.scope == "ue:1"
#     assert response.ue_count == 1
#     assert response.bearer_count == 2
#     assert response.details == {"1": {"1": 6400, "2": 3200}}
#
#
# @patch('epc.api.get_traffic_manager')
# def test_get_ues_stats_ue_not_found(mock_get_tm, mock_repo, mock_tm):
#     mock_repo.ue_exists.return_value = False
#     mock_get_tm.return_value = mock_tm
#     with pytest.raises(HTTPException) as exc_info:
#         get_ues_stats(mock_repo, ue_id=999, include_details=False)
#     assert exc_info.value.status_code == 400
#     assert "UE not found" in exc_info.value.detail
#
#
# @patch('epc.api.get_traffic_manager')
# def test_get_ues_stats_no_duration(mock_get_tm, mock_repo, mock_tm):
#     mock_get_tm.return_value = mock_tm
#     # Symuluj brak start_ts (duration=0)
#     mock_repo.get_ue.return_value.stats[1].start_ts = None
#     with patch('time.time', return_value=1010):
#         response = get_ues_stats(mock_repo, ue_id=1, include_details=False)
#
#     assert response.total_tx_bps == 3200
#     assert response.total_rx_bps == 3200
