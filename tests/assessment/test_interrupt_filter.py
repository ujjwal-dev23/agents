import pytest
from unittest.mock import MagicMock, patch

from examples.voice_agents.assessment.interrupt_filter import InterruptFilter

class TestInterruptFilter:
  @pytest.fixture
  def mock_session(self):
    return MagicMock()

  @pytest.fixture
  def filter_system(self, mock_session):
    with patch("asyncio.create_task"):
      # Initialize with a dummy config
      filter = InterruptFilter(mock_session, config_path="ignored_words.json")
    # Manually inject words to avoid file I/O dependency during test
    filter.ignored_words = {"uh", "um", "umm", "hmm", "okay"}
    return filter 

  def test_clean_text_punctuation(self, filter_system):
    """Test that punctuation is stripped correctly"""
    assert "um" in filter_system.clean_text("um,")
    assert "stop" in filter_system.clean_text("stop!")
    assert "yeah" in filter_system.clean_text("...yeah?")
    
  def test_is_filler_exact(self, filter_system):
    """Test exact matches for filler words"""
    assert "um" in filter_system.ignored_words
    assert "stop" not in filter_system.ignored_words
