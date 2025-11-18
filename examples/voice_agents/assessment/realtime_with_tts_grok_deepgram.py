import asyncio
from dotenv import load_dotenv
import logging
import os

from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli, room_io
from livekit.agents.llm import function_tool
from livekit.plugins import deepgram, groq, silero
from .interrupt_filter import InterruptFilter
from livekit.agents.voice.agent_session import AgentStateChangedEvent, UserInputTranscribedEvent

load_dotenv()

logger = logging.getLogger("realtime-with-tts")
logger.setLevel(logging.INFO)


class WeatherAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="You are a helpful assistant.",
            # 1. Hearing (Deepgram STT)
            stt=deepgram.STT(),
            # 2. Thinking (Groq LLM - Llama 3)
            llm=groq.LLM(model="llama-3.1-8b-instant"),
            # 3. Speaking (Deepgram TTS)
            tts=deepgram.TTS(),
            # 4. Interruption Detection (Silero VAD)
            vad=silero.VAD.load(),
        )

    @function_tool
    async def get_weather(self, location: str):
        """Called when the user asks about the weather."""
        logger.info(f"getting weather for {location}")
        return f"The weather in {location} is sunny, and the temperature is 20 degrees Celsius."


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # Setup Logging
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Set DEBUG level logging to see our logic
    logging.getLogger("interrupt-filter").setLevel(logging.DEBUG)

    # Initialize session
    session = AgentSession(allow_interruptions=False, discard_audio_if_uninterruptible=False)
    filter = InterruptFilter(session, config_path="ignored_words.json")

    # Helper function to handle valid interruptions safely
    async def interrupt_and_reply(text: str):
        await session.interrupt(force=True)
        await session.generate_reply(user_input=text)

    # Define event listeners
    @session.on("agent_state_changed")
    def on_agent_state_changed(event: AgentStateChangedEvent):
        """Tracks if the agent is currently speaking or listening"""
        if event.new_state == "speaking":
            filter.agent_is_speaking = True
        elif event.new_state == "listening":
            filter.agent_is_speaking = False

    @session.on("user_input_transcribed")
    def on_transcription(event: UserInputTranscribedEvent):
        """Decides whether to ignore the user's speech or allow the interruption"""
        text_content = event.transcript

        # Scenario 1 : Agent is listening
        # Always register speech
        if not filter.agent_is_speaking:
            logger.info(f"Speech REGISTERED (agent quiet): '{text_content}'")
            asyncio.create_task(
                session.generate_reply(user_input=text_content)
            )  # Manual reply trigger since VAD is disabled
            return

        # Scenario 2 : Agent is speaking

        # Check 1 : is confidence low (e.g background noise)
        """
    if event.confidence < filter.confidence_threshold:
      filter.resume_agent_speech()
      return
    """

        # Check 2 : is it a filler word
        # remove any words found in our ignored_words list
        user_words = filter.clean_text(text_content)
        non_filler_words = [word for word in user_words if word not in filter.ignored_words]

        if not non_filler_words:
            # It was all filler. Ignore and continue speaking
            logger.debug(f"Interruption IGNORED (filler) : '{text_content}'")
        else:
            # Valid words remain, allow the interruption
            logger.warning(f"Interruption REGISTERED (valid): '{text_content}'")
            asyncio.create_task(interrupt_and_reply(text_content))  # Manually handle new input

    # Start the agent
    await session.start(
        agent=WeatherAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(text_output=True, audio_output=True),
    )

    session.generate_reply(
        instructions="say hello to the user and immediately start telling a long, 100-word story about the history of computers"
    )


if __name__ == "__main__":
    cli.run_app(server)
