"""
Voice Generator - ElevenLabs integration for Kata Engine.

Generates realistic AI voices for synthetic influencers:
- Natural speech synthesis
- Multiple voice styles
- Emotion and tone control
- Script-to-speech conversion
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum
import asyncio
import uuid
from pathlib import Path
import httpx

logger = logging.getLogger(__name__)


class VoiceStyle(str, Enum):
    """Voice personality styles."""
    FRIENDLY = "friendly"           # Warm, approachable
    PROFESSIONAL = "professional"   # Clear, authoritative
    ENERGETIC = "energetic"         # Excited, upbeat
    CALM = "calm"                   # Soothing, relaxed
    CONVERSATIONAL = "conversational"  # Natural, casual
    PROMOTIONAL = "promotional"     # Enthusiastic, sales-y


@dataclass
class VoiceResult:
    """Result from voice generation."""
    success: bool
    audio_path: str
    duration_seconds: float
    voice_id: str

    # Audio characteristics
    sample_rate: int = 44100
    format: str = "mp3"

    # Cost tracking
    characters_used: int = 0

    error: Optional[str] = None


class VoiceGenerator:
    """
    Generate realistic AI voices using ElevenLabs.

    Features:
    - High-quality speech synthesis
    - Multiple voice options (50+ voices)
    - Voice cloning capability
    - Emotion and style control
    - Multi-language support
    """

    # Pre-selected voice IDs for different styles
    # These are actual ElevenLabs voice IDs
    VOICE_PRESETS = {
        # Female voices
        ("friendly", "female"): "21m00Tcm4TlvDq8ikWAM",      # Rachel - warm, friendly
        ("professional", "female"): "EXAVITQu4vr4xnSDxMaL",  # Bella - clear, professional
        ("energetic", "female"): "jBpfuIE2acCO8z3wKNLl",     # Gigi - youthful, upbeat
        ("calm", "female"): "MF3mGyEYCl7XYWbV9V6O",         # Elli - gentle, soothing
        ("conversational", "female"): "XrExE9yKIg1WjnnlVkGX", # Matilda - natural, warm

        # Male voices
        ("friendly", "male"): "VR6AewLTigWG4xSOukaG",        # Arnold - warm, engaging
        ("professional", "male"): "pNInz6obpgDQGcFmaJgB",    # Adam - clear, authoritative
        ("energetic", "male"): "yoZ06aMxZJJ28mfd3POQ",       # Sam - enthusiastic
        ("calm", "male"): "TxGEqnHWrfWFTfGW9XjX",           # Josh - relaxed, natural
        ("conversational", "male"): "IKne3meq5aSn9XLyUdCD",  # Charlie - casual, friendly
    }

    def __init__(
        self,
        elevenlabs_api_key: str = None,
        output_dir: str = "outputs/kata/voices",
        default_model: str = "eleven_multilingual_v2",
    ):
        self.api_key = elevenlabs_api_key
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.default_model = default_model

        self.base_url = "https://api.elevenlabs.io/v1"

    async def generate_speech(
        self,
        text: str,
        voice_style: str = "friendly",
        gender: str = "female",
        voice_id: str = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True,
    ) -> VoiceResult:
        """
        Generate speech from text.

        Args:
            text: The script/text to speak
            voice_style: friendly, professional, energetic, etc.
            gender: male or female
            voice_id: Specific ElevenLabs voice ID (overrides style/gender)
            stability: Voice stability (0-1, higher = more consistent)
            similarity_boost: Voice similarity (0-1, higher = more like original)
            style: Style exaggeration (0-1, higher = more expressive)
            use_speaker_boost: Enhance voice clarity

        Returns:
            VoiceResult with audio file path
        """
        logger.info(f"Generating speech: {len(text)} chars, {voice_style}/{gender}")
        output_path = self.output_dir / f"voice_{uuid.uuid4().hex[:8]}.mp3"

        # Get voice ID
        if voice_id is None:
            voice_id = self._get_voice_id(voice_style, gender)

        try:
            if self.api_key:
                # Real ElevenLabs API call
                audio_data = await self._call_elevenlabs(
                    text=text,
                    voice_id=voice_id,
                    stability=stability,
                    similarity_boost=similarity_boost,
                    style=style,
                    use_speaker_boost=use_speaker_boost,
                )

                # Save audio file
                with open(output_path, "wb") as f:
                    f.write(audio_data)

                # Calculate duration (approximate)
                duration = len(text) / 15  # ~15 chars per second average

            else:
                # Mock mode: generate placeholder audio
                logger.warning(
                    "Voice generation running in MOCK mode. "
                    "Set ELEVENLABS_API_KEY for real voice synthesis."
                )
                duration = await self._generate_placeholder_audio(
                    text=text,
                    output_path=output_path,
                    voice_style=voice_style,
                    gender=gender,
                )

            return VoiceResult(
                success=True,
                audio_path=str(output_path),
                duration_seconds=duration,
                voice_id=voice_id,
                characters_used=len(text),
            )

        except Exception as e:
            logger.error(f"Voice generation failed: {e}")
            return VoiceResult(
                success=False,
                audio_path="",
                duration_seconds=0.0,
                voice_id=voice_id,
                error=str(e),
            )

    async def _call_elevenlabs(
        self,
        text: str,
        voice_id: str,
        stability: float,
        similarity_boost: float,
        style: float,
        use_speaker_boost: bool,
    ) -> bytes:
        """Make actual API call to ElevenLabs."""
        url = f"{self.base_url}/text-to-speech/{voice_id}"

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }

        payload = {
            "text": text,
            "model_id": self.default_model,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style,
                "use_speaker_boost": use_speaker_boost,
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            return response.content

    async def list_voices(self) -> List[Dict[str, Any]]:
        """List available ElevenLabs voices."""
        if not self.api_key:
            # Return preset info
            return [
                {"voice_id": vid, "style": style, "gender": gender}
                for (style, gender), vid in self.VOICE_PRESETS.items()
            ]

        try:
            url = f"{self.base_url}/voices"
            headers = {"xi-api-key": self.api_key}

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data.get("voices", [])

        except Exception as e:
            logger.error(f"Failed to list voices: {e}")
            return []

    async def clone_voice(
        self,
        name: str,
        audio_files: List[str],
        description: str = "",
    ) -> Optional[str]:
        """
        Clone a voice from audio samples.

        This allows creating custom brand voices.

        Args:
            name: Name for the cloned voice
            audio_files: List of audio file paths (samples)
            description: Description of the voice

        Returns:
            Voice ID of the cloned voice
        """
        if not self.api_key:
            logger.warning("No API key - cannot clone voice")
            return None

        try:
            url = f"{self.base_url}/voices/add"
            headers = {"xi-api-key": self.api_key}

            # Prepare multipart form data
            files = []
            for audio_path in audio_files:
                files.append(("files", open(audio_path, "rb")))

            data = {
                "name": name,
                "description": description,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=120.0,
                )
                response.raise_for_status()
                result = response.json()
                return result.get("voice_id")

        except Exception as e:
            logger.error(f"Voice cloning failed: {e}")
            return None

    async def get_usage(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        if not self.api_key:
            return {"error": "No API key"}

        try:
            url = f"{self.base_url}/user/subscription"
            headers = {"xi-api-key": self.api_key}

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Failed to get usage: {e}")
            return {"error": str(e)}

    def _get_voice_id(self, style: str, gender: str) -> str:
        """Get voice ID for style/gender combination."""
        key = (style.lower(), gender.lower())

        if key in self.VOICE_PRESETS:
            return self.VOICE_PRESETS[key]

        # Fallback to friendly voice
        fallback_key = ("friendly", gender.lower())
        if fallback_key in self.VOICE_PRESETS:
            return self.VOICE_PRESETS[fallback_key]

        # Ultimate fallback
        return self.VOICE_PRESETS[("friendly", "female")]

    def estimate_duration(self, text: str) -> float:
        """Estimate speech duration for text."""
        # Average speaking rate is ~150 words per minute
        # Or roughly 12-15 characters per second
        words = len(text.split())
        return (words / 150) * 60  # Return seconds

    def estimate_cost(self, text: str) -> float:
        """Estimate cost for generating speech."""
        # ElevenLabs pricing is per character
        # Starter: $0.30/1000 chars
        # Creator: $0.24/1000 chars
        chars = len(text)
        return (chars / 1000) * 0.24
    
    async def _generate_placeholder_audio(
        self,
        text: str,
        output_path: Path,
        voice_style: str = "friendly",
        gender: str = "female",
    ) -> float:
        """Generate placeholder audio for mock mode.
        
        Creates a silent audio file with the estimated duration,
        or uses ffmpeg to generate a tone if available.
        
        Returns:
            Estimated duration in seconds
        """
        import shutil
        
        # Calculate estimated duration
        words = len(text.split())
        duration = (words / 150) * 60  # ~150 words per minute
        duration = max(duration, 1.0)  # Minimum 1 second
        
        # Try to generate audio with ffmpeg
        if shutil.which("ffmpeg"):
            try:
                import subprocess
                
                # Generate a silent audio file with the correct duration
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", f"anullsrc=r=44100:cl=stereo",
                    "-t", str(duration),
                    "-c:a", "libmp3lame",
                    "-q:a", "4",
                    str(output_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.info(f"Generated placeholder audio: {output_path} ({duration:.1f}s)")
                    return duration
            except Exception as e:
                logger.warning(f"FFmpeg audio generation failed: {e}")
        
        # Fallback: create an empty file
        logger.warning("Creating minimal placeholder audio file")
        output_path.touch()
        return duration
