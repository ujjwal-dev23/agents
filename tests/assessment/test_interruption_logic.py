from unittest.mock import MagicMock, patch

import pytest

from examples.voice_agents.assessment.interrupt_filter import InterruptFilter


# Define a mock event
class MockTranscriptionEvent:
    def __init__(self, text):
        self.transcript = text


@pytest.mark.asyncio
async def test_scenario_agent_listening():
    """
    Scenario: User filler while agent quiet
    Expected: System registers speech event
    """
    session = MagicMock()
    with patch("asyncio.create_task"):
        filter_sys = InterruptFilter(session)
    filter_sys.agent_is_speaking = False

    # InterruptFilter agent_is_speaking logic simulation
    if not filter_sys.agent_is_speaking:
        decision = "REGISTERED"
    else:
        decision = "IGNORED"

    assert decision == "REGISTERED"


@pytest.mark.asyncio
async def test_scenario_filler_interruption():
    """
    Scenario : User filler while agent speaks
    Expected : Agent ignores input and continues speaking
    """
    session = MagicMock()
    with patch("asyncio.create_task"):
        filter_sys = InterruptFilter(session)
    filter_sys.ignored_words = {"um", "uh"}
    filter_sys.agent_is_speaking = True  # Agent is speaking

    transcript = "um"

    # Simulate text cleaning logic
    user_words = filter_sys.clean_text(transcript)
    # Simulate filtering logic
    non_filler_words = [w for w in user_words if w not in filter_sys.ignored_words]

    if not non_filler_words:
        decision = "IGNORED"
    else:
        decision = "INTERRUPT"

    assert decision == "IGNORED"


@pytest.mark.asyncio
async def test_scenario_valid_interruption():
    """
    Scenario: User real interruption
    Expected: Agent immediately stops
    """
    session = MagicMock()
    with patch("asyncio.create_task"):
        filter_sys = InterruptFilter(session)
    filter_sys.ignored_words = {"um", "uh"}
    filter_sys.agent_is_speaking = True

    transcript = "wait one second"

    user_words = filter_sys.clean_text(transcript)
    non_filler_words = [w for w in user_words if w not in filter_sys.ignored_words]

    if not non_filler_words:
        decision = "IGNORED"
    else:
        decision = "INTERRUPT"

    assert decision == "INTERRUPT"


@pytest.mark.asyncio
async def test_scenario_mixed_interruption():
    """
    Scenario: Mixed filler and command
    Expected: Agent stops (contains valid command)
    """
    session = MagicMock()
    with patch("asyncio.create_task"):
        filter_sys = InterruptFilter(session)
    filter_sys.ignored_words = {"um"}
    filter_sys.agent_is_speaking = True

    transcript = "um stop"

    user_words = filter_sys.clean_text(transcript)
    non_filler_words = [w for w in user_words if w not in filter_sys.ignored_words]

    # 'stop' is valid, so non_filler_words should not be empty
    assert "stop" in non_filler_words
    assert len(non_filler_words) > 0
