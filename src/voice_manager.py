"""
Voice Manager Module
Handles multi-voice synthesis for Gemini TTS
Manages speaker-to-voice assignment and maintains parallel processing
"""

import os
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from src.voice_profiles import (
    VoiceProfile, Gender, AgeGroup,
    GEMINI_VOICES,
    VoiceSelector
)
from src.config import Config
from src.logging_config import get_logger

logger = get_logger(__name__)


class VoiceManager:
    """Manages multi-voice synthesis for Gemini TTS"""

    def __init__(self):
        """Initialize voice manager for Gemini TTS"""
        self.provider = "gemini"
        self.voice_assignments = {}  # speaker_id -> voice_profile
        self.voice_selector = VoiceSelector()

        # Load available voices
        self.available_voices = GEMINI_VOICES

        # Initialize voice pools for round-robin assignment
        self.male_voices = [v for v in self.available_voices.values() if v.gender == Gender.MALE]
        self.female_voices = [v for v in self.available_voices.values() if v.gender == Gender.FEMALE]

        logger.info(f"VoiceManager initialized for Gemini: "
                   f"{len(self.male_voices)} male, {len(self.female_voices)} female voices")

    def assign_voices_to_speakers(
        self,
        speakers: List[Dict],
        segments: Optional[List[Dict]] = None,
        auto_detect_gender: bool = True
    ) -> Dict[str, VoiceProfile]:
        """
        Assign voices to speakers based on Voicegain gender/age detection

        Args:
            speakers: List of speaker profiles from Voicegain with gender/age
            segments: Optional segments for additional context
            auto_detect_gender: Ignored - we use Voicegain's gender detection

        Returns:
            Dictionary mapping speaker IDs to voice profiles
        """
        assignments = {}
        import random

        # Track used voices to ensure variety
        used_male_voices = []
        used_female_voices = []

        for i, speaker in enumerate(speakers):
            speaker_id = speaker.get('id', f'speaker_{i}')
            voicegain_gender = speaker.get('gender', 'unknown').lower()
            voicegain_age = speaker.get('age', 'unknown').lower()

            # Map Voicegain gender to our Gender enum
            if voicegain_gender == 'male':
                gender = Gender.MALE
                available_pool = self.male_voices.copy()
                used_pool = used_male_voices
            elif voicegain_gender == 'female':
                gender = Gender.FEMALE
                available_pool = self.female_voices.copy()
                used_pool = used_female_voices
            else:
                # Unknown gender - default to male (most YouTube content has male speakers)
                gender = Gender.MALE
                available_pool = self.male_voices.copy()
                used_pool = used_male_voices
                logger.info(f"Speaker {speaker_id} has unknown gender, defaulting to male voice")

            # Filter by age if possible
            if voicegain_age == 'young-adult':
                # Prefer young voices
                age_filtered = [v for v in available_pool if v.age_group == AgeGroup.YOUNG]
                if age_filtered:
                    available_pool = age_filtered
            elif voicegain_age == 'senior':
                # Prefer mature voices
                age_filtered = [v for v in available_pool if v.age_group == AgeGroup.MATURE]
                if age_filtered:
                    available_pool = age_filtered

            # Remove already used voices for variety
            unused_voices = [v for v in available_pool if v.id not in used_pool]
            if unused_voices:
                available_pool = unused_voices
            else:
                # All voices used, reset the pool
                used_pool.clear()

            # Randomly select a voice from the appropriate pool
            if available_pool:
                voice = random.choice(available_pool)
                used_pool.append(voice.id)
            else:
                # Fallback to any voice
                all_voices = self.male_voices + self.female_voices
                voice = all_voices[i % len(all_voices)]

            assignments[speaker_id] = voice
            logger.info(f"Assigned {voice.name} ({voice.gender.value}, {voice.age_group.value}) "
                       f"to {speaker.get('label', speaker_id)} ({voicegain_gender}, {voicegain_age})")

        self.voice_assignments = assignments
        return assignments

    def _detect_speaker_gender(
        self,
        speaker_id: str,
        segments: List[Dict]
    ) -> Optional[Gender]:
        """
        Attempt to detect speaker gender from their speech content

        Args:
            speaker_id: Speaker identifier
            segments: Transcript segments

        Returns:
            Detected gender or None
        """
        # Collect all text from this speaker
        speaker_texts = []
        for seg in segments:
            if seg.get('speaker') == speaker_id:
                text = seg.get('original_text', seg.get('text', ''))
                speaker_texts.append(text.lower())

        if not speaker_texts:
            return None

        combined_text = ' '.join(speaker_texts)

        # Simple heuristic-based gender detection
        male_indicators = ['my wife', 'i am a man', 'as a father', 'my girlfriend']
        female_indicators = ['my husband', 'i am a woman', 'as a mother', 'my boyfriend']

        male_score = sum(1 for indicator in male_indicators if indicator in combined_text)
        female_score = sum(1 for indicator in female_indicators if indicator in combined_text)

        if male_score > female_score:
            logger.debug(f"Detected {speaker_id} as male (score: {male_score})")
            return Gender.MALE
        elif female_score > male_score:
            logger.debug(f"Detected {speaker_id} as female (score: {female_score})")
            return Gender.FEMALE

        return None

    def prepare_segments_for_multivoice(
        self,
        segments: List[Dict],
        voice_assignments: Optional[Dict[str, VoiceProfile]] = None
    ) -> List[Dict]:
        """
        Prepare segments with voice assignments for TTS

        Args:
            segments: List of transcript segments
            voice_assignments: Optional custom voice assignments

        Returns:
            Segments with voice information added
        """
        assignments = voice_assignments or self.voice_assignments

        if not assignments:
            logger.warning("No voice assignments, using default voice")
            return segments

        # Debug logging
        logger.info(f"Voice assignments keys: {list(assignments.keys())}")
        if segments:
            sample_speakers = [seg.get('speaker') for seg in segments[:5]]
            logger.info(f"Sample segment speakers: {sample_speakers}")

        prepared = []
        matched_count = 0
        unmatched_count = 0

        for segment in segments:
            seg = segment.copy()

            # Get speaker and assigned voice
            speaker_id = seg.get('speaker')
            if speaker_id and speaker_id in assignments:
                voice = assignments[speaker_id]
                seg['voice_id'] = voice.id
                seg['voice_name'] = voice.name
                seg['voice_provider'] = voice.provider
                matched_count += 1

                logger.debug(f"Segment assigned voice: {voice.name} for speaker {speaker_id}")
            else:
                # Use default voice if no assignment
                default_voice = list(self.available_voices.values())[0]
                seg['voice_id'] = default_voice.id
                seg['voice_name'] = default_voice.name
                seg['voice_provider'] = default_voice.provider
                unmatched_count += 1

                if speaker_id:
                    logger.warning(f"No voice assignment for speaker '{speaker_id}', using default {default_voice.name}")

            prepared.append(seg)

        logger.info(f"Voice assignment results: {matched_count} matched, {unmatched_count} unmatched")
        return prepared

    def group_segments_by_voice(
        self,
        segments: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """
        Group segments by assigned voice for efficient batch processing

        Args:
            segments: List of segments with voice assignments

        Returns:
            Dictionary mapping voice_id to list of segments
        """
        grouped = defaultdict(list)

        for segment in segments:
            voice_id = segment.get('voice_id', 'default')
            grouped[voice_id].append(segment)

        logger.info(f"Grouped segments into {len(grouped)} voice groups")
        for voice_id, segs in grouped.items():
            logger.debug(f"  {voice_id}: {len(segs)} segments")

        return dict(grouped)

    def generate_voiceover_multivoice(
        self,
        tts_provider,
        segments: List[Dict],
        temp_dir: str = "temp",
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        Generate multi-voice voiceover using assigned voices

        Args:
            tts_provider: TTS provider instance (Gemini)
            segments: Segments with voice assignments
            temp_dir: Temporary directory for audio files
            progress_callback: Progress callback

        Returns:
            Segments with audio paths
        """
        if progress_callback:
            progress_callback("Starting multi-voice synthesis...")

        # Check if provider supports voice switching
        has_set_voice = hasattr(tts_provider, 'set_voice')

        if not has_set_voice:
            logger.warning("Provider doesn't support voice switching, using default")
            return tts_provider.generate_voiceover(segments, temp_dir, progress_callback)

        # Process segments with voice switching
        results = []
        voice_groups = self.group_segments_by_voice(segments)
        total_segments = len(segments)
        processed = 0

        for voice_id, voice_segments in voice_groups.items():
            # Set voice for this group
            logger.info(f"Switching to voice: {voice_id}")
            tts_provider.set_voice(voice_id)

            # Generate voiceover for this voice group
            if progress_callback:
                progress_callback(f"Synthesizing with voice {voice_id} ({len(voice_segments)} segments)")

            # Process this voice group
            voice_results = tts_provider.generate_voiceover(
                voice_segments,
                temp_dir,
                lambda msg: progress_callback(f"[{voice_id}] {msg}") if progress_callback else None
            )

            results.extend(voice_results)
            processed += len(voice_results)

            if progress_callback:
                progress_callback(f"Completed {processed}/{total_segments} segments")

        # Sort results back to original order
        results.sort(key=lambda x: segments.index(
            next((s for s in segments if s.get('text') == x.get('text')), segments[0])
        ))

        if progress_callback:
            progress_callback(f"Multi-voice synthesis complete: {len(results)} segments")

        return results

    def get_voice_configuration(self) -> Dict:
        """
        Get current voice configuration

        Returns:
            Dictionary with voice assignments and settings
        """
        config = {
            'provider': self.provider,
            'assignments': {},
            'available_voices': len(self.available_voices),
            'voice_pools': {
                'male': len(self.male_voices),
                'female': len(self.female_voices)
            }
        }

        # Add voice assignment details
        for speaker_id, voice in self.voice_assignments.items():
            config['assignments'][speaker_id] = {
                'voice_id': voice.id,
                'voice_name': voice.name,
                'gender': voice.gender.value,
                'age_group': voice.age_group.value
            }

        return config
