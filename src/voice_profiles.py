"""
Voice Profiles Configuration
Defines available voices for both ElevenLabs and Google Gemini TTS
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
    id: str  # Voice ID or name
    name: str  # Display name
    provider: str  # elevenlabs or gemini
    gender: Gender
    age_group: AgeGroup
    description: str
    language_support: List[str]
    style_tags: List[str]  # e.g., ["warm", "professional", "energetic"]


# ElevenLabs Voice Profiles (Premade voices that support Georgian)
# Selected voices that work well for multi-speaker scenarios
ELEVENLABS_VOICES = {
    # Male voices
    "liam": VoiceProfile(
        id="TX3LPaxmHKxFdv7VOQHJ",
        name="Liam",
        provider="elevenlabs",
        gender=Gender.MALE,
        age_group=AgeGroup.MIDDLE,
        description="Clear male voice, professional narrator",
        language_support=["ka-GE", "multilingual"],
        style_tags=["clear", "professional", "narrator"]
    ),
    "adam": VoiceProfile(
        id="pNInz6obpgDQGcFmaJgB",
        name="Adam",
        provider="elevenlabs",
        gender=Gender.MALE,
        age_group=AgeGroup.MATURE,
        description="Deep male voice with authority",
        language_support=["ka-GE", "multilingual"],
        style_tags=["deep", "authoritative", "news"]
    ),
    "daniel": VoiceProfile(
        id="onwK4e9ZLuTAKqWW03F9",
        name="Daniel",
        provider="elevenlabs",
        gender=Gender.MALE,
        age_group=AgeGroup.YOUNG,
        description="British accent, younger male voice",
        language_support=["ka-GE", "multilingual"],
        style_tags=["young", "british", "friendly"]
    ),
    "josh": VoiceProfile(
        id="TxGEqnHWrfWFTfGW9XjX",
        name="Josh",
        provider="elevenlabs",
        gender=Gender.MALE,
        age_group=AgeGroup.YOUNG,
        description="Young adult male, casual tone",
        language_support=["ka-GE", "multilingual"],
        style_tags=["casual", "young", "conversational"]
    ),
    # Female voices
    "rachel": VoiceProfile(
        id="21m00Tcm4TlvDq8ikWAM",
        name="Rachel",
        provider="elevenlabs",
        gender=Gender.FEMALE,
        age_group=AgeGroup.MIDDLE,
        description="American female, warm and professional",
        language_support=["ka-GE", "multilingual"],
        style_tags=["warm", "professional", "clear"]
    ),
    "bella": VoiceProfile(
        id="EXAVITQu4vr4xnSDxMaL",
        name="Bella",
        provider="elevenlabs",
        gender=Gender.FEMALE,
        age_group=AgeGroup.YOUNG,
        description="Soft, younger female voice",
        language_support=["ka-GE", "multilingual"],
        style_tags=["soft", "young", "friendly"]
    ),
    "dorothy": VoiceProfile(
        id="ThT5KcBeYPX3keUQqHPh",
        name="Dorothy",
        provider="elevenlabs",
        gender=Gender.FEMALE,
        age_group=AgeGroup.MATURE,
        description="British female, pleasant tone",
        language_support=["ka-GE", "multilingual"],
        style_tags=["british", "pleasant", "mature"]
    ),
    "charlotte": VoiceProfile(
        id="XB0fDUnXU5powFXDhCwa",
        name="Charlotte",
        provider="elevenlabs",
        gender=Gender.FEMALE,
        age_group=AgeGroup.MIDDLE,
        description="Swedish/English accent, seductive",
        language_support=["ka-GE", "multilingual"],
        style_tags=["seductive", "accent", "sophisticated"]
    ),
    # Additional useful voice
    "antoni": VoiceProfile(
        id="ErXwobaYiN019PkySvjV",
        name="Antoni",
        provider="elevenlabs",
        gender=Gender.MALE,  # Listed as male in ElevenLabs
        age_group=AgeGroup.MIDDLE,
        description="Well-rounded American male voice",
        language_support=["ka-GE", "multilingual"],
        style_tags=["balanced", "american", "clear"]
    )
}


# Google Gemini Voice Profiles (All 28 available voices)
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
        gender=Gender.FEMALE,  # Achernar is actually female
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


# Voice mapping between providers for fallback
# Maps voice IDs/names to equivalent voices in the other provider
VOICE_EQUIVALENTS = {
    # ElevenLabs ID -> Gemini name mapping
    "TX3LPaxmHKxFdv7VOQHJ": "Orus",       # Liam -> Orus (male middle)
    "pNInz6obpgDQGcFmaJgB": "Charon",     # Adam -> Charon (male mature)
    "onwK4e9ZLuTAKqWW03F9": "Puck",       # Daniel -> Puck (male young)
    "TxGEqnHWrfWFTfGW9XjX": "Puck",       # Josh -> Puck (male young)
    "21m00Tcm4TlvDq8ikWAM": "Kore",       # Rachel -> Kore (female middle)
    "EXAVITQu4vr4xnSDxMaL": "Aoede",      # Bella -> Aoede (female young)
    "ThT5KcBeYPX3keUQqHPh": "Achernar",   # Dorothy -> Achernar (female mature)
    "XB0fDUnXU5powFXDhCwa": "Kore",       # Charlotte -> Kore (female middle)
    "ErXwobaYiN019PkySvjV": "Orus",       # Antoni -> Orus (male middle)

    # Gemini name -> ElevenLabs ID mapping (reverse)
    "Charon": "pNInz6obpgDQGcFmaJgB",     # Charon -> Adam
    "Puck": "TxGEqnHWrfWFTfGW9XjX",       # Puck -> Josh
    "Orus": "TX3LPaxmHKxFdv7VOQHJ",       # Orus -> Liam
    "Fenrir": "pNInz6obpgDQGcFmaJgB",     # Fenrir -> Adam
    "Achernar": "21m00Tcm4TlvDq8ikWAM",   # Achernar -> Rachel
    "Kore": "21m00Tcm4TlvDq8ikWAM",       # Kore -> Rachel
    "Aoede": "EXAVITQu4vr4xnSDxMaL",      # Aoede -> Bella
    "Zephyr": "EXAVITQu4vr4xnSDxMaL",     # Zephyr -> Bella
}


class VoiceSelector:
    """Helper class for voice selection logic"""

    @staticmethod
    def get_voice_by_gender(provider: str, gender: Gender) -> Optional[VoiceProfile]:
        """Get first available voice matching gender"""
        voices = ELEVENLABS_VOICES if provider == "elevenlabs" else GEMINI_VOICES

        for voice in voices.values():
            if voice.gender == gender:
                return voice

        # Fallback to neutral if no match
        for voice in voices.values():
            if voice.gender == Gender.NEUTRAL:
                return voice

        return None

    @staticmethod
    def get_voice_by_characteristics(
        provider: str,
        gender: Optional[Gender] = None,
        age_group: Optional[AgeGroup] = None,
        style_tags: Optional[List[str]] = None
    ) -> Optional[VoiceProfile]:
        """Get voice matching characteristics"""
        voices = ELEVENLABS_VOICES if provider == "elevenlabs" else GEMINI_VOICES

        candidates = list(voices.values())

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
    def get_equivalent_voice(voice_id: str, target_provider: str) -> Optional[str]:
        """Get equivalent voice in target provider"""
        if voice_id in VOICE_EQUIVALENTS:
            equivalent = VOICE_EQUIVALENTS[voice_id]

            # Check if equivalent is for target provider
            target_voices = ELEVENLABS_VOICES if target_provider == "elevenlabs" else GEMINI_VOICES
            for voice in target_voices.values():
                if voice.id == equivalent:
                    return equivalent

        return None

    @staticmethod
    def get_default_voices(provider: str) -> Dict[str, VoiceProfile]:
        """Get default male and female voices for a provider"""
        voices = ELEVENLABS_VOICES if provider == "elevenlabs" else GEMINI_VOICES

        defaults = {}

        # Find default male voice
        for key, voice in voices.items():
            if voice.gender == Gender.MALE and voice.age_group == AgeGroup.MIDDLE:
                defaults['male'] = voice
                break

        # Find default female voice
        for key, voice in voices.items():
            if voice.gender == Gender.FEMALE and voice.age_group == AgeGroup.MIDDLE:
                defaults['female'] = voice
                break

        # Add neutral as fallback
        for key, voice in voices.items():
            if voice.gender == Gender.NEUTRAL:
                defaults['neutral'] = voice
                break

        return defaults