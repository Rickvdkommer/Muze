"""
Audio transcriber for Muze using Google Gemini 2.0 Flash.
Handles downloading and transcribing voice messages from WhatsApp via Twilio.
"""

import logging
import os
import requests
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class AudioTranscriber:
    def __init__(self, gemini_client):
        """
        Initialize audio transcriber with Gemini client.

        Args:
            gemini_client: Initialized Google GenAI client
        """
        self.client = gemini_client
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    def download_audio(self, media_url: str) -> tuple[bytes, str]:
        """
        Download audio file from Twilio MediaUrl.

        Args:
            media_url: URL to the audio file from Twilio

        Returns:
            Tuple of (audio_bytes, content_type)
        """
        try:
            # Download with Twilio credentials (basic auth)
            response = requests.get(
                media_url,
                auth=(self.twilio_account_sid, self.twilio_auth_token),
                timeout=30
            )
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', 'audio/ogg')
            audio_bytes = response.content

            logger.info(f"Downloaded audio: {len(audio_bytes)} bytes, type: {content_type}")
            return audio_bytes, content_type

        except Exception as e:
            logger.error(f"Failed to download audio from {media_url}: {str(e)}")
            raise

    def transcribe_audio(self, audio_bytes: bytes, mime_type: str) -> str:
        """
        Transcribe audio using Gemini 2.0 Flash.

        Args:
            audio_bytes: Raw audio file bytes
            mime_type: MIME type of the audio (e.g., 'audio/ogg', 'audio/mpeg')

        Returns:
            Transcribed text
        """
        try:
            # Create audio part
            audio_part = types.Part.from_bytes(
                data=audio_bytes,
                mime_type=mime_type
            )

            # Transcribe with Gemini
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=[
                    "Transcribe this voice message accurately. Return only the transcribed text, no explanations or metadata.",
                    audio_part
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Low temperature for accuracy
                    max_output_tokens=2000,  # Allow for long voice messages
                )
            )

            transcription = response.text.strip()
            logger.info(f"✅ Audio transcribed: {len(transcription)} characters")

            return transcription

        except Exception as e:
            logger.error(f"Failed to transcribe audio: {str(e)}")
            raise

    def process_voice_message(self, media_url: str, media_content_type: str = None) -> str:
        """
        Complete pipeline: download and transcribe a voice message.

        Args:
            media_url: URL to the audio file from Twilio
            media_content_type: Optional MIME type hint

        Returns:
            Transcribed text
        """
        try:
            # Download audio
            audio_bytes, content_type = self.download_audio(media_url)

            # Use provided content type if available, otherwise use detected
            mime_type = media_content_type or content_type

            # Transcribe
            transcription = self.transcribe_audio(audio_bytes, mime_type)

            return transcription

        except Exception as e:
            logger.error(f"Failed to process voice message: {str(e)}")
            return f"[Voice message transcription failed: {str(e)}]"
