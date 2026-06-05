import pytest
from unittest.mock import patch
from app.utils.delays import human_delay

@patch("time.sleep")
def test_human_delay_short(mock_sleep):
    human_delay(message_length=10, complexity="short")
    mock_sleep.assert_called_once()
    args, _ = mock_sleep.call_args
    # SHORT_MESSAGE_DELAY = (0.5, 1.5)
    # length_factor = 10 / 200 = 0.05
    # scaled_min = 0.5 * (1 + 0.05*0.5) = 0.5 * 1.025 = 0.5125
    # scaled_max = 1.5 * 1.025 = 1.5375
    assert 0.5 <= args[0] <= 1.6

@patch("time.sleep")
def test_human_delay_long(mock_sleep):
    human_delay(message_length=100, complexity="long")
    mock_sleep.assert_called_once()
    args, _ = mock_sleep.call_args
    # LONG_MESSAGE_DELAY = (2.0, 4.0)
    # length_factor = 100 / 200 = 0.5
    # scaled_min = 2.0 * (1 + 0.5*0.5) = 2.0 * 1.25 = 2.5
    # scaled_max = 4.0 * 1.25 = 5.0
    assert 2.0 <= args[0] <= 5.0
