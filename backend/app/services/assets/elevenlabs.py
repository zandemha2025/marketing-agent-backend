"""
ElevenLabs Integration for Premium Voice Generation.

Generates broadcast-quality voiceovers for:
- Video ads
- Podcast ads
- Radio spots
- Social media videos
- Presentation narration
"""
import os
import uuid
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx
import logging

logger = logging.getLogger(__name__)

API_BASE = "https://api.elevenlabs.io/v1"


@dataclass
class VoiceProfile:
    """A voice profile for generation."""
    voice_id: str
    name: str
    description: str
    preview_url: Optional[str] = None
    labels: Dict[str, str] = None


@dataclass
class GeneratedAudio:
    """Result of voice generation."""
    filename: str
    filepath: str
    duration_seconds: float
    voice_id: str
    text: str
    model: str


# Curated voice presets for different brand tones
VOICE_PRESETS = {
    # Professional / Corporate
    "professional_male": {
        "description": "Confident, authoritative male voice for corporate content",
        "settings": {"stability": 0.75, "similarity_boost": 0.75}
    },
    "professional_female": {
        "description": "Polished, trustworthy female voice for business content",
        "settings": {"stability": 0.75, "similarity_boost": 0.75}
    },

    # Warm / Friendly
    "friendly_male": {
        "description": "Warm, approachable male voice for lifestyle brands",
        "settings": {"stability": 0.65, "similarity_boost": 0.80}
    },
    "friendly_female": {
        "description": "Warm, relatable female voice for consumer brands",
        "settings": {"stability": 0.65, "similarity_boost": 0.80}
    },

    # Energetic / Bold
    "energetic_male": {
        "description": "Dynamic, exciting male voice for action/sports brands",
        "settings": {"stability": 0.55, "similarity_boost": 0.85}
    },
    "energetic_female": {
        "description": "Vibrant, energetic female voice for youth brands",
        "settings": {"stability": 0.55, "similarity_boost": 0.85}
    },

    # Luxury / Sophisticated
    "luxury_male": {
        "description": "Refined, elegant male voice for premium brands",
        "settings": {"stability": 0.80, "similarity_boost": 0.70}
    },
    "luxury_female": {
        "description": "Sophisticated, elegant female voice for luxury content",
        "settings": {"stability": 0.80, "similarity_boost": 0.70}
    },

    # Conversational
    "conversational_male": {
        "description": "Natural, casual male voice for social content",
        "settings": {"stability": 0.50, "similarity_boost": 0.85}
    },
    "conversational_female": {
        "description": "Natural, casual female voice for social content",
        "settings": {"stability": 0.50, "similarity_boost": 0.85}
    },
}


class ElevenLabsService:
    """
    Premium voice generation service.

    Handles:
    - Voice selection based on brand tone
    - Script optimization for audio
    - High-quality audio generation
    - Multiple format outputs
    """

    def __init__(self, api_key: str, output_dir: str = "outputs"):
        self.api_key = api_key
        self.output_dir = output_dir
        self.client = httpx.AsyncClient(timeout=120.0)

        # Cache for available voices
        self._voices_cache: Optional[List[VoiceProfile]] = None

        os.makedirs(output_dir, exist_ok=True)

    async def get_available_voices(self, force_refresh: bool = False) -> List[VoiceProfile]:
        """
        Get list of available voices from ElevenLabs.

        Returns:
            List of VoiceProfile objects
        """
        if self._voices_cache and not force_refresh:
            return self._voices_cache

        headers = {"xi-api-key": self.api_key}

        response = await self.client.get(
            f"{API_BASE}/voices",
            headers=headers
        )

        if response.status_code != 200:
            logger.error(f"Failed to get voices: {response.status_code}")
            raise Exception(f"ElevenLabs API error: {response.status_code}")

        data = response.json()

        self._voices_cache = [
            VoiceProfile(
                voice_id=v["voice_id"],
                name=v["name"],
                description=v.get("description", ""),
                preview_url=v.get("preview_url"),
                labels=v.get("labels", {})
            )
            for v in data.get("voices", [])
        ]

        return self._voices_cache

    async def generate_voiceover(
        self,
        text: str,
        voice_id: Optional[str] = None,
        voice_preset: Optional[str] = None,
        brand_tone: Optional[str] = None,
        stability: float = 0.70,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        model: str = "eleven_multilingual_v2",
    ) -> GeneratedAudio:
        """
        Generate a premium voiceover.

        Args:
            text: The script to speak
            voice_id: Specific voice ID (if known)
            voice_preset: Preset name from VOICE_PRESETS
            brand_tone: Brand tone to auto-select voice (professional, friendly, etc.)
            stability: Voice stability (0-1, higher = more consistent)
            similarity_boost: Voice clarity (0-1, higher = clearer)
            style: Style exaggeration (0-1)
            model: ElevenLabs model to use

        Returns:
            GeneratedAudio with file info
        """
        # Determine voice settings
        if voice_preset and voice_preset in VOICE_PRESETS:
            preset = VOICE_PRESETS[voice_preset]
            stability = preset["settings"]["stability"]
            similarity_boost = preset["settings"]["similarity_boost"]

        # Auto-select voice based on brand tone if no voice specified
        if not voice_id:
            voice_id = await self._select_voice_for_tone(brand_tone or "professional")

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "text": text,
            "model_id": model,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style,
                "use_speaker_boost": True
            }
        }

        response = await self.client.post(
            f"{API_BASE}/text-to-speech/{voice_id}",
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            logger.error(f"Voice generation error: {response.status_code} - {response.text[:500]}")
            raise Exception(f"ElevenLabs API error: {response.status_code}")

        # Save audio
        filename = f"{uuid.uuid4().hex[:12]}.mp3"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.content)

        # Estimate duration (rough: ~150 words per minute)
        word_count = len(text.split())
        estimated_duration = (word_count / 150) * 60

        logger.info(f"Generated voiceover: {filename}")

        return GeneratedAudio(
            filename=filename,
            filepath=filepath,
            duration_seconds=estimated_duration,
            voice_id=voice_id,
            text=text,
            model=model
        )

    async def generate_for_video_ad(
        self,
        script: str,
        brand_tone: str = "professional",
        duration_target: Optional[float] = None,
    ) -> GeneratedAudio:
        """
        Generate voiceover optimized for video ads.

        Args:
            script: The ad script
            brand_tone: Brand tone for voice selection
            duration_target: Target duration in seconds (will adjust pacing)

        Returns:
            GeneratedAudio
        """
        # Optimize script for spoken delivery
        optimized_script = self._optimize_script_for_speech(script)

        # Select appropriate voice preset
        preset = self._get_preset_for_tone(brand_tone)

        return await self.generate_voiceover(
            text=optimized_script,
            voice_preset=preset,
            brand_tone=brand_tone
        )

    async def generate_for_social(
        self,
        script: str,
        platform: str = "instagram",
        brand_tone: str = "conversational",
    ) -> GeneratedAudio:
        """
        Generate voiceover optimized for social media.

        More casual, energetic delivery suited for social platforms.
        """
        # Social scripts should be more conversational
        preset = f"conversational_{'male' if 'male' in brand_tone else 'female'}"

        if brand_tone == "energetic":
            preset = f"energetic_{'male' if 'male' in brand_tone else 'female'}"

        return await self.generate_voiceover(
            text=script,
            voice_preset=preset,
            stability=0.55,  # More expressive
            similarity_boost=0.85
        )

    def _optimize_script_for_speech(self, script: str) -> str:
        """Optimize a script for natural spoken delivery."""
        # Add natural pauses
        script = script.replace(". ", "... ")  # Longer pause after sentences
        script = script.replace(", ", ", ")    # Brief pause at commas
        script = script.replace("!", "!.. ")   # Pause after exclamations

        # Remove things that don't translate to speech
        script = script.replace("™", "")
        script = script.replace("®", "")
        script = script.replace("©", "")

        # Expand common abbreviations
        script = script.replace("&", " and ")
        script = script.replace("%", " percent")

        return script.strip()

    def _get_preset_for_tone(self, brand_tone: str) -> str:
        """Get voice preset based on brand tone."""
        tone_mapping = {
            "professional": "professional_female",
            "corporate": "professional_male",
            "friendly": "friendly_female",
            "warm": "friendly_female",
            "approachable": "friendly_male",
            "energetic": "energetic_female",
            "bold": "energetic_male",
            "dynamic": "energetic_male",
            "luxury": "luxury_female",
            "premium": "luxury_female",
            "sophisticated": "luxury_male",
            "elegant": "luxury_female",
            "casual": "conversational_female",
            "conversational": "conversational_female",
            "natural": "conversational_male",
        }

        return tone_mapping.get(brand_tone.lower(), "professional_female")

    async def _select_voice_for_tone(self, brand_tone: str) -> str:
        """
        Auto-select a voice ID based on brand tone.

        Uses ElevenLabs' voice library to find best match.
        """
        voices = await self.get_available_voices()

        # Look for voices with matching labels
        tone_keywords = {
            "professional": ["professional", "corporate", "business", "news"],
            "friendly": ["friendly", "warm", "conversational", "casual"],
            "energetic": ["energetic", "dynamic", "young", "excited"],
            "luxury": ["sophisticated", "elegant", "mature", "refined"],
        }

        keywords = tone_keywords.get(brand_tone.lower(), ["professional"])

        # Score voices by label matches
        for voice in voices:
            labels = voice.labels or {}
            for keyword in keywords:
                if any(keyword in str(v).lower() for v in labels.values()):
                    return voice.voice_id

        # Fallback to first available voice
        if voices:
            return voices[0].voice_id

        raise Exception("No voices available")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
