"""
Voice Manager Module
Handles multi-voice synthesis for both ElevenLabs and Gemini TTS
Manages speaker-to-voice assignment and maintains parallel processing
"""

import os
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from src.voice_profiles import (
    VoiceProfile, Gender, AgeGroup,
    ELEVENLABS_VOICES, GEMINI_VOICES, VOICE_EQUIVALENTS,
    VoiceSelector
)
from src.config import Config
from src.logging_config import get_logger

logger = get_logger(__name__)


class VoiceManager:
    """Manages multi-voice synthesis across providers"""

    def __init__(self, provider: str = None):
        """
        Initialize voice manager

        Args:
            provider: TTS provider ('elevenlabs' or 'gemini')
        """
        self.provider = provider or Config.TTS_PROVIDER
        self.voice_assignments = {}  # speaker_id -> voice_profile
        self.voice_selector = VoiceSelector()

        # Load available voices for provider
        self.available_voices = (
            ELEVENLABS_VOICES if self.provider == "elevenlabs"
            else GEMINI_VOICES
        )

        # Initialize voice pools for round-robin assignment
        self.male_voices = [v for v in self.available_voices.values() if v.gender == Gender.MALE]
        self.female_voices = [v for v in self.available_voices.values() if v.gender == Gender.FEMALE]

        logger.info(f"VoiceManager initialized for {self.provider}: "
                   f"{len(self.male_voices)} male, {len(self.female_voices)} female voices")

    def assign_voices_to_speakers(
        self,
        speakers: List[Dict],
        segments: Optional[List[Dict]] = None,
        auto_detect_gender: bool = True
    ) -> Dict[str, VoiceProfile]:
        """
        Assign voices to speakers based on characteristics

        Args:
            speakers: List of speaker profiles from transcription
            segments: Optional segments for gender detection
            auto_detect_gender: Whether to auto-detect gender from content

        Returns:
            Dictionary mapping speaker IDs to voice profiles
        """
        assignments = {}

        for i, speaker in enumerate(speakers):
            speaker_id = speaker.get('id', f'speaker_{i}')

            # Try to detect gender if enabled
            gender = None
            if auto_detect_gender and segments:
                gender = self._detect_speaker_gender(speaker_id, segments)

            # Assign voice based on gender or round-robin
            if gender == Gender.MALE and self.male_voices:
                voice = self.male_voices[i % len(self.male_voices)]
            elif gender == Gender.FEMALE and self.female_voices:
                voice = self.female_voices[i % len(self.female_voices)]
            else:
                # Alternate between male and female for unknown gender
                all_voices = self.male_voices + self.female_voices
                voice = all_voices[i % len(all_voices)]

            assignments[speaker_id] = voice
            logger.info(f"Assigned {voice.name} ({voice.provider}) to {speaker.get('label', speaker_id)}")

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
        # (In production, you might use a more sophisticated method)
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

        prepared = []
        for segment in segments:
            seg = segment.copy()

            # Get speaker and assigned voice
            speaker_id = seg.get('speaker')
            if speaker_id and speaker_id in assignments:
                voice = assignments[speaker_id]
                seg['voice_id'] = voice.id
                seg['voice_name'] = voice.name
                seg['voice_provider'] = voice.provider

                logger.debug(f"Segment assigned voice: {voice.name} for speaker {speaker_id}")
            else:
                # Use default voice if no assignment
                default_voice = list(self.available_voices.values())[0]
                seg['voice_id'] = default_voice.id
                seg['voice_name'] = default_voice.name
                seg['voice_provider'] = default_voice.provider

            prepared.append(seg)

        return prepared

    def get_fallback_voice(
        self,
        original_voice_id: str,
        target_provider: str
    ) -> Optional[str]:
        """
        Get equivalent voice in fallback provider

        Args:
            original_voice_id: Voice ID/name in original provider
            target_provider: Target provider for fallback

        Returns:
            Equivalent voice ID/name or None
        """
        # Check direct mapping
        if original_voice_id in VOICE_EQUIVALENTS:
            return VOICE_EQUIVALENTS[original_voice_id]

        # Try to find similar voice by characteristics
        original_voice = None
        for voice in self.available_voices.values():
            if voice.id == original_voice_id:
                original_voice = voice
                break

        if original_voice:
            # Find voice with similar characteristics in target provider
            equivalent = self.voice_selector.get_voice_by_characteristics(
                target_provider,
                gender=original_voice.gender,
                age_group=original_voice.age_group,
                style_tags=original_voice.style_tags
            )
            if equivalent:
                return equivalent.id

        # Default fallback
        target_voices = ELEVENLABS_VOICES if target_provider == "elevenlabs" else GEMINI_VOICES
        return list(target_voices.values())[0].id if target_voices else None

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

    def optimize_parallel_processing(
        self,
        segments: List[Dict],
        max_workers: int = None
    ) -> List[List[Dict]]:
        """
        Optimize segment batching for parallel TTS processing

        Args:
            segments: List of segments
            max_workers: Maximum parallel workers

        Returns:
            List of segment batches optimized for parallel processing
        """
        if not max_workers:
            max_workers = (
                Config.ELEVENLABS_MAX_CONCURRENT if self.provider == "elevenlabs"
                else Config.GEMINI_TTS_MAX_CONCURRENT
            )

        # Group by voice to minimize voice switching
        voice_groups = self.group_segments_by_voice(segments)

        # Create balanced batches
        batches = []
        batch_size = max(1, len(segments) // max_workers)

        for voice_id, voice_segments in voice_groups.items():
            # Split voice group into batches
            for i in range(0, len(voice_segments), batch_size):
                batch = voice_segments[i:i + batch_size]
                batches.append(batch)

        logger.info(f"Created {len(batches)} batches for {max_workers} workers")

        return batches

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
            tts_provider: TTS provider instance (ElevenLabs or Gemini)
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
        # (Assuming segments have an index or we can match by content)
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

    @staticmethod
    def create_voice_mapping_config() -> Dict:
        """
        Create a configuration template for manual voice mapping

        Returns:
            Template configuration for voice mapping
        """
        template = {
            'voice_mapping': {
                'speaker_1': {
                    'elevenlabs': 'TX3LPaxmHKxFdv7VOQHJ',  # Liam
                    'gemini': 'Orus',
                    'gender': 'male',
                    'description': 'Main narrator'
                },
                'speaker_2': {
                    'elevenlabs': '21m00Tcm4TlvDq8ikWAM',  # Rachel
                    'gemini': 'Kore',
                    'gender': 'female',
                    'description': 'Secondary speaker'
                }
            },
            'auto_assign': {
                'enabled': True,
                'detect_gender': True,
                'round_robin': True
            }
        }

        return template