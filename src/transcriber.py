"""
Speech-to-Text Transcription Module
Uses OpenAI Whisper API for transcription with timestamps
"""

import os
import openai
from pathlib import Path


class Transcriber:
    def __init__(self, use_google_cloud=False):
        """
        Initialize transcriber with OpenAI Whisper API

        Args:
            use_google_cloud: Deprecated - only Whisper API is supported now
        """
        if use_google_cloud:
            raise NotImplementedError(
                "Google Cloud Speech-to-Text is no longer supported."
            )

        # Set OpenAI API key
        openai.api_key = os.getenv('OPENAI_API_KEY')
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

    def transcribe(self, audio_path, progress_callback=None):
        """
        Transcribe audio file with timestamps using OpenAI Whisper API

        Args:
            audio_path: Path to audio file (WAV format)
            progress_callback: Optional callback for progress updates

        Returns:
            List of segments with text, start_time, end_time
            [
                {
                    'text': 'Hello world',
                    'start': 0.0,
                    'end': 2.5
                },
                ...
            ]
        """
        return self._transcribe_whisper_api(audio_path, progress_callback)

    def _transcribe_google(self, audio_path, progress_callback=None):
        """Transcribe using Google Cloud Speech-to-Text"""
        if progress_callback:
            progress_callback("Starting Google Cloud transcription...")

        with open(audio_path, 'rb') as audio_file:
            content = audio_file.read()

        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code='en-US',  # Source language
            enable_word_time_offsets=True,
            enable_automatic_punctuation=True,
        )

        if progress_callback:
            progress_callback("Sending audio to Google Cloud...")

        # Use long-running recognition for files > 1 minute
        operation = self.client.long_running_recognize(config=config, audio=audio)

        if progress_callback:
            progress_callback("Waiting for transcription results...")

        response = operation.result(timeout=600)

        # Extract segments with timestamps
        segments = []
        for result in response.results:
            alternative = result.alternatives[0]

            # Get timing from words
            if alternative.words:
                start_time = alternative.words[0].start_time.total_seconds()
                end_time = alternative.words[-1].end_time.total_seconds()
            else:
                start_time = 0
                end_time = 0

            segments.append({
                'text': alternative.transcript.strip(),
                'start': start_time,
                'end': end_time
            })

        if progress_callback:
            progress_callback(f"Transcription complete: {len(segments)} segments")

        return segments

    def _transcribe_whisper_api(self, audio_path, progress_callback=None):
        """Transcribe using OpenAI Whisper API"""
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
                'text': response['text'].strip(),
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
