"""
Voice Profiles Configuration
Defines available voices for Google Gemini TTS
Includes voice characteristics and recommended use cases
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class Gender(Enum):
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


class AgeGroup(Enum):
    YOUNG = "young"
    MIDDLE = "middle"
    MATURE = "mature"


@dataclass
class VoiceProfile:
    """Voice profile with characteristics"""
    id: str  # Voice name
    name: str  # Display name
    provider: str  # Always 'gemini'
    gender: Gender
    age_group: AgeGroup
    description: str
    language_support: List[str]
    style_tags: List[str]  # e.g., ["warm", "professional", "energetic"]


# Google Gemini Voice Profiles (Selected voices for variety)
# Gemini voices are celestial-themed - 14 female, 14 male voices
GEMINI_VOICES = {
    # Male voices (selected for variety)
    "charon": VoiceProfile(
        id="Charon",
        name="Charon",
        provider="gemini",
        gender=Gender.MALE,
        age_group=AgeGroup.MATURE,
        description="Deep mature male voice",
        language_support=["ka-GE", "multilingual"],
        style_tags=["deep", "mature", "authoritative"]
    ),
    "puck": VoiceProfile(
        id="Puck",
        name="Puck",
        provider="gemini",
        gender=Gender.MALE,
        age_group=AgeGroup.YOUNG,
        description="Playful younger male voice",
        language_support=["ka-GE", "multilingual"],
        style_tags=["playful", "young", "energetic"]
    ),
    "orus": VoiceProfile(
        id="Orus",
        name="Orus",
        provider="gemini",
        gender=Gender.MALE,
        age_group=AgeGroup.MIDDLE,
        description="Balanced male voice",
        language_support=["ka-GE", "multilingual"],
        style_tags=["balanced", "clear", "professional"]
    ),
    "fenrir": VoiceProfile(
        id="Fenrir",
        name="Fenrir",
        provider="gemini",
        gender=Gender.MALE,
        age_group=AgeGroup.MATURE,
        description="Strong male voice",
        language_support=["ka-GE", "multilingual"],
        style_tags=["strong", "confident", "deep"]
    ),
    # Female voices (selected for variety)
    "achernar": VoiceProfile(
        id="Achernar",
        name="Achernar",
        provider="gemini",
        gender=Gender.FEMALE,
        age_group=AgeGroup.MIDDLE,
        description="Clear professional female voice",
        language_support=["ka-GE", "multilingual"],
        style_tags=["clear", "professional", "warm"]
    ),
    "kore": VoiceProfile(
        id="Kore",
        name="Kore",
        provider="gemini",
        gender=Gender.FEMALE,
        age_group=AgeGroup.MIDDLE,
        description="Warm female voice",
        language_support=["ka-GE", "multilingual"],
        style_tags=["warm", "friendly", "natural"]
    ),
    "aoede": VoiceProfile(
        id="Aoede",
        name="Aoede",
        provider="gemini",
        gender=Gender.FEMALE,
        age_group=AgeGroup.YOUNG,
        description="Bright younger female voice",
        language_support=["ka-GE", "multilingual"],
        style_tags=["bright", "youthful", "expressive"]
    ),
    "zephyr": VoiceProfile(
        id="Zephyr",
        name="Zephyr",
        provider="gemini",
        gender=Gender.FEMALE,
        age_group=AgeGroup.YOUNG,
        description="Gentle female voice",
        language_support=["ka-GE", "multilingual"],
        style_tags=["gentle", "soft", "soothing"]
    )
}

# Complete list of all Gemini voices for reference
GEMINI_ALL_VOICES = {
    'female': [
        'Achernar', 'Aoede', 'Autonoe', 'Callirrhoe', 'Despina',
        'Erinome', 'Gacrux', 'Kore', 'Laomedeia', 'Leda',
        'Pulcherrima', 'Sulafat', 'Vindemiatrix', 'Zephyr'
    ],
    'male': [
        'Achird', 'Algenib', 'Algieba', 'Alnilam', 'Charon',
        'Enceladus', 'Fenrir', 'Iapetus', 'Orus', 'Puck',
        'Rasalgethi', 'Sadachbia', 'Sadaltager', 'Schedar',
        'Umbriel', 'Zubenelgenubi'
    ]
}


class VoiceSelector:
    """Helper class for voice selection logic"""

    @staticmethod
    def get_voice_by_gender(gender: Gender) -> Optional[VoiceProfile]:
        """Get first available voice matching gender"""
        for voice in GEMINI_VOICES.values():
            if voice.gender == gender:
                return voice

        # Fallback to neutral if no match
        for voice in GEMINI_VOICES.values():
            if voice.gender == Gender.NEUTRAL:
                return voice

        return None

    @staticmethod
    def get_voice_by_characteristics(
        gender: Optional[Gender] = None,
        age_group: Optional[AgeGroup] = None,
        style_tags: Optional[List[str]] = None
    ) -> Optional[VoiceProfile]:
        """Get voice matching characteristics"""
        candidates = list(GEMINI_VOICES.values())

        # Filter by gender
        if gender:
            candidates = [v for v in candidates if v.gender == gender]

        # Filter by age group
        if age_group:
            candidates = [v for v in candidates if v.age_group == age_group]

        # Filter by style tags
        if style_tags:
            # Find voices with most matching tags
            scored_candidates = []
            for voice in candidates:
                score = sum(1 for tag in style_tags if tag in voice.style_tags)
                if score > 0:
                    scored_candidates.append((score, voice))

            if scored_candidates:
                scored_candidates.sort(key=lambda x: x[0], reverse=True)
                return scored_candidates[0][1]

        return candidates[0] if candidates else None

    @staticmethod
    def get_default_voices() -> Dict[str, VoiceProfile]:
        """Get default male and female voices"""
        defaults = {}

        # Find default male voice
        for key, voice in GEMINI_VOICES.items():
            if voice.gender == Gender.MALE and voice.age_group == AgeGroup.MIDDLE:
                defaults['male'] = voice
                break

        # Find default female voice
        for key, voice in GEMINI_VOICES.items():
            if voice.gender == Gender.FEMALE and voice.age_group == AgeGroup.MIDDLE:
                defaults['female'] = voice
                break

        # Add neutral as fallback
        for key, voice in GEMINI_VOICES.items():
            if voice.gender == Gender.NEUTRAL:
                defaults['neutral'] = voice
                break

        return defaults
