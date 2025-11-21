"""
AssemblyAI Transcriber Module
Handles transcription with speaker diarization using AssemblyAI API
"""

import os
import time
import assemblyai as aai
from typing import List, Dict, Optional, Tuple
from src.logging_config import get_logger

logger = get_logger(__name__)


class AssemblyAITranscriber:
    """Transcriber using AssemblyAI for speaker diarization"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AssemblyAI transcriber

        Args:
            api_key: AssemblyAI API key (defaults to env var)
        """
        self.api_key = api_key or os.getenv('ASSEMBLYAI_API_KEY')
        if not self.api_key:
            raise ValueError("AssemblyAI API key not found")

        # Configure AssemblyAI
        aai.settings.api_key = self.api_key
        logger.info("AssemblyAI transcriber initialized")

    def transcribe_with_speakers(
        self,
        audio_path: str,
        progress_callback: Optional[callable] = None,
        speaker_count: Optional[int] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Transcribe audio with speaker diarization

        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for progress updates
            speaker_count: Optional number of speakers (2-10), auto-detect if None

        Returns:
            Tuple of (segments with speaker info, speaker profiles)
        """
        try:
            if progress_callback:
                progress_callback("Uploading audio to AssemblyAI...")

            # Configure transcription with speaker diarization
            config = aai.TranscriptionConfig(
                speaker_labels=True,  # Enable speaker diarization
                speakers_expected=speaker_count  # Auto-detect if None
            )

            # Create transcriber
            transcriber = aai.Transcriber()

            # Start transcription
            logger.info(f"Starting AssemblyAI transcription for: {audio_path}")
            transcript = transcriber.transcribe(audio_path, config=config)

            # Poll for completion
            start_time = time.time()
            last_status = None

            while transcript.status not in [aai.TranscriptStatus.completed, aai.TranscriptStatus.error]:
                elapsed = int(time.time() - start_time)

                if transcript.status != last_status:
                    last_status = transcript.status
                    status_msg = f"Status: {transcript.status} ({elapsed}s elapsed)"
                    logger.info(status_msg)
                    if progress_callback:
                        progress_callback(status_msg)

                time.sleep(3)
                transcript = transcriber.get_transcript(transcript.id)

            if transcript.status == aai.TranscriptStatus.error:
                error_msg = f"Transcription failed: {transcript.error}"
                logger.error(error_msg)
                raise Exception(error_msg)

            # Process results
            segments = self._process_transcript(transcript, progress_callback)
            speakers = self._extract_speaker_profiles(transcript)

            logger.info(f"Transcription complete: {len(segments)} segments, {len(speakers)} speakers")

            return segments, speakers

        except Exception as e:
            logger.error(f"AssemblyAI transcription failed: {str(e)}", exc_info=True)
            raise

    def _process_transcript(
        self,
        transcript: aai.Transcript,
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        Process AssemblyAI transcript into segments with speaker labels

        Args:
            transcript: AssemblyAI transcript object
            progress_callback: Optional progress callback

        Returns:
            List of segments with speaker information
        """
        if progress_callback:
            progress_callback("Processing transcript segments...")

        segments = []

        # Group utterances by speaker and time proximity
        for utterance in transcript.utterances:
            segment = {
                'start': utterance.start / 1000.0,  # Convert ms to seconds
                'end': utterance.end / 1000.0,
                'text': utterance.text,
                'speaker': utterance.speaker,  # Speaker label (A, B, C, etc.)
                'confidence': utterance.confidence if hasattr(utterance, 'confidence') else 1.0
            }
            segments.append(segment)

        # Merge adjacent segments from same speaker for paragraph-level processing
        merged_segments = self._merge_speaker_segments(segments)

        logger.info(f"Processed {len(transcript.utterances)} utterances into {len(merged_segments)} segments")

        return merged_segments

    def _merge_speaker_segments(
        self,
        segments: List[Dict],
        max_pause: float = 1.5
    ) -> List[Dict]:
        """
        Merge adjacent segments from the same speaker into paragraphs

        Args:
            segments: List of transcript segments
            max_pause: Maximum pause (seconds) to consider segments as continuous

        Returns:
            List of merged segments
        """
        if not segments:
            return []

        merged = []
        current = segments[0].copy()

        for segment in segments[1:]:
            # Check if we should merge with current segment
            same_speaker = segment['speaker'] == current['speaker']
            small_gap = (segment['start'] - current['end']) <= max_pause

            if same_speaker and small_gap:
                # Extend current segment
                current['end'] = segment['end']
                current['text'] += ' ' + segment['text']
                # Average confidence
                if 'confidence' in current and 'confidence' in segment:
                    current['confidence'] = (current['confidence'] + segment['confidence']) / 2
            else:
                # Save current and start new segment
                merged.append(current)
                current = segment.copy()

        # Don't forget the last segment
        merged.append(current)

        logger.info(f"Merged {len(segments)} segments into {len(merged)} paragraphs")

        return merged

    def _extract_speaker_profiles(self, transcript: aai.Transcript) -> List[Dict]:
        """
        Extract speaker profiles from transcript

        Args:
            transcript: AssemblyAI transcript object

        Returns:
            List of speaker profiles with metadata
        """
        speakers = {}

        for utterance in transcript.utterances:
            speaker_id = utterance.speaker

            if speaker_id not in speakers:
                speakers[speaker_id] = {
                    'id': speaker_id,
                    'label': f'Speaker {speaker_id}',
                    'utterance_count': 0,
                    'total_duration': 0.0,
                    'first_appearance': utterance.start / 1000.0,
                    'detected_gender': None,  # To be enhanced with voice analysis
                    'voice_characteristics': {}  # For future voice profiling
                }

            speakers[speaker_id]['utterance_count'] += 1
            duration = (utterance.end - utterance.start) / 1000.0
            speakers[speaker_id]['total_duration'] += duration

        # Sort speakers by first appearance
        speaker_list = sorted(speakers.values(), key=lambda s: s['first_appearance'])

        # Assign more meaningful labels
        for i, speaker in enumerate(speaker_list):
            speaker['label'] = f'Speaker {i + 1}'

            # Log speaker statistics
            logger.info(
                f"{speaker['label']}: {speaker['utterance_count']} utterances, "
                f"{speaker['total_duration']:.1f}s total speech"
            )

        return speaker_list

    def analyze_speakers(
        self,
        segments: List[Dict],
        speakers: List[Dict]
    ) -> Dict:
        """
        Analyze speaker patterns and dialogue structure

        Args:
            segments: List of transcript segments
            speakers: List of speaker profiles

        Returns:
            Analysis results
        """
        analysis = {
            'speaker_count': len(speakers),
            'total_segments': len(segments),
            'dialogue_type': 'monologue' if len(speakers) == 1 else 'dialogue',
            'speaker_balance': {},
            'turn_taking_rate': 0
        }

        # Calculate speaker balance
        total_duration = sum(s['total_duration'] for s in speakers)
        for speaker in speakers:
            percentage = (speaker['total_duration'] / total_duration * 100) if total_duration > 0 else 0
            analysis['speaker_balance'][speaker['id']] = {
                'percentage': round(percentage, 1),
                'duration': round(speaker['total_duration'], 1)
            }

        # Calculate turn-taking rate
        if len(segments) > 1:
            speaker_changes = sum(
                1 for i in range(1, len(segments))
                if segments[i]['speaker'] != segments[i-1]['speaker']
            )
            analysis['turn_taking_rate'] = speaker_changes / (len(segments) - 1)

        logger.info(f"Speaker analysis: {analysis}")

        return analysis