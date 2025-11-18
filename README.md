# LiveKit Voice Interruption Handling Assessment

This repository contains the implementation for the **LiveKit Voice Interruption Handling Challenge**. The goal was to extend a real-time conversational AI agent to intelligently distinguish between meaningful user interruptions (commands, questions) and irrelevant filler sounds ("umm", "uh", "hmm"), ensuring a seamless and natural dialogue flow.

## What Changed

To achieve intelligent interruption handling without modifying the core LiveKit VAD algorithm, the following changes were implemented:

1.  **Custom `InterruptFilter` Class (`interrupt_filter.py`):**

      * A dedicated class was created to manage the state of the agent (speaking vs. listening) and filter incoming transcriptions.
      * It loads and monitors a configuration file (`ignored_words.json`) to maintain a dynamic list of filler words.
      * It includes logic to clean transcriptions (removing punctuation) and check against the ignored words list.

2.  **Modified Agent Entrypoint (`realtime_with_tts_grok_deepgram.py`):**

      * **Disabled Default Interruption:** The `AgentSession` is initialized with `allow_interruptions=False`. This prevents the standard VAD from automatically stopping the agent when sound is detected.
      * **Event-Driven Logic:** Implemented a custom handler for `user_input_transcribed` events.
      * **Logic Flow:**
          * If the agent is **listening**, all speech is registered.
          * If the agent is **speaking**, the transcript is filtered. If the transcript contains *only* filler words, it is ignored, and the agent continues speaking. If it contains valid words (e.g., "Stop", "Wait"), `session.generate_reply()` is triggered manually.

3.  **Dynamic Configuration (`ignored_words.json`):**

      * A JSON configuration file was introduced to define ignored words per language.
      * The `InterruptFilter` includes a background task that watches this file for changes and reloads the list at runtime without restarting the agent.

## What Works

The following features have been verified through manual and automated testing:

  * **Smart Interruption Filtering:**
      * **Scenario:** User says "um", "uh", "hmm" while the agent is speaking.
      * **Result:** The agent ignores the input and continues its sentence without pausing.
  * **Valid Interruption Handling:**
      * **Scenario:** User says "Wait a second" or "Stop" while the agent is speaking.
      * **Result:** The agent immediately stops speaking and processes the user's request.
  * **Mixed Input Handling:**
      * **Scenario:** User says "Um, stop".
      * **Result:** The system detects "stop" as a valid word and triggers an interruption.
  * **Quiet State Sensitivity:**
      * **Scenario:** User says "Um" while the agent is silent.
      * **Result:** The system registers this as user speech (valid for turn-taking).
  * **Dynamic Configuration Updates:**
      * **Feature:** Adding a new word (e.g., "like") to `ignored_words.json` takes effect immediately (within the poll interval) without restarting the server.

## Known Issues

  * **ASR Latency:** The logic relies on final transcription events. Extremely short commands might have a slight delay compared to raw VAD audio detection, though in practice this is negligible for conversational pacing.
  * **Confidence Threshold:** The logic for ignoring interruptions based on low ASR confidence is currently drafted but disabled in the final entrypoint code to prioritize responsiveness for clearer speech.

## Environment Details

  * **Python Version:** 3.9+
  * **Core Dependencies:**
      * `livekit-agents`
      * `livekit-plugins-deepgram` (STT/TTS)
      * `livekit-plugins-groq` (LLM)
      * `livekit-plugins-silero` (VAD)
      * `python-dotenv`
  * **Configuration:**
      * Ensure `ignored_words.json` is present in the working directory.
      * Ensure a valid `.env` file is set up with `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `DEEPGRAM_API_KEY`, and `GROQ_API_KEY`.

*Note :- Can also be used with other agents/models, grok and deepgram were chosen for ease of testing due to more generous free tier limits*

## Steps to Test

### 1\. Automated Tests

Unit tests have been written to verify the filtering logic in isolation.

Run the tests using `pytest`:

```bash
pytest tests/assessment/
```

### 2\. Manual Verification

To run the agent and test interactively:

1.  **Start the Agent:**
    ```bash
    python -m examples.voice_agents.assessment.realtime_with_tts_grok_deepgram start
    ```
2.  **Connect:** Join the room using the LiveKit Playground or a client frontend.
3.  **Test Scenarios:**
      * **Filler Test:** Wait for the agent to start its story. Say "Um" or "Uh" clearly. Verify the agent **does not** stop.
      * **Interruption Test:** Wait for the agent to speak. Say "Wait, stop". Verify the agent **stops** immediately and replies.
      * **Runtime Update:** While the agent is running, edit `ignored_words.json` and add a new word (e.g., "bananas"). Save the file. Speak "bananas" while the agent talks and verify it is now ignored.
