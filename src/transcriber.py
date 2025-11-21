"""
Speech-to-Text Transcription Module
Uses OpenAI Whisper API for transcription with timestamps
"""

import os
from pathlib import Path
import openai


class Transcriber:
    def __init__(self):
        """
        Initialize transcriber with OpenAI Whisper API
        """
        # Set OpenAI API key for v0.28.1 compatibility
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        openai.api_key = api_key

    def transcribe(self, audio_path, progress_callback=None):
        """
        Transcribe audio file with timestamps using OpenAI Whisper API v1.x

        Args:
            audio_path: Path to audio file (WAV format)
            progress_callback: Optional callback for progress updates

        Returns:
            List of segments with text, start_time, end_time
        """
        if progress_callback:
            progress_callback("Starting Whisper API transcription...")

        # OpenAI Whisper API v0.28.1 usage
        with open(audio_path, 'rb') as audio_file:
            response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                language='en',  # Source language
                response_format='verbose_json',  # Get timestamps
                timestamp_granularities=['segment']  # Get segment-level timestamps
            )

        # Extract segments with timestamps from API response
        segments = []
        if hasattr(response, 'segments') and response.segments:
            for segment in response.segments:
                segments.append({
                    'text': segment['text'].strip(),
                    'start': segment['start'],
                    'end': segment['end']
                })
        else:
            # Fallback: if no segments, create one segment with full text
            segments.append({
                'text': response.get('text', '').strip(),
                'start': 0.0,
                'end': 0.0  # Unknown duration
            })

        if progress_callback:
            progress_callback(f"Transcription complete: {len(segments)} segments")

        return segments

    def merge_short_segments(self, segments, min_duration=3.0):
        """
        Merge very short segments together for better voiceover pacing

        Args:
            segments: List of transcription segments
            min_duration: Minimum segment duration in seconds

        Returns:
            List of merged segments
        """
        if not segments:
            return []

        merged = []
        current = segments[0].copy()

        for segment in segments[1:]:
            current_duration = current['end'] - current['start']

            if current_duration < min_duration:
                # Merge with next segment
                current['text'] += ' ' + segment['text']
                current['end'] = segment['end']
            else:
                merged.append(current)
                current = segment.copy()

        # Add last segment
        merged.append(current)

        return merged
