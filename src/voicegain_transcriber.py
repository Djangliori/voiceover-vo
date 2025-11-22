"""
Voicegain Transcriber with Speaker Diarization, Gender, and Age Detection
Uses official Voicegain Python SDK
"""

import os
import time
from typing import List, Dict, Optional, Tuple
from voicegain_speech import ApiClient, Configuration, TranscribeApi, DataApi
from voicegain_speech.models import *
from src.logging_config import get_logger

logger = get_logger(__name__)


class VoicegainTranscriber:
    """Transcriber using Voicegain API for complete speech analytics"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Voicegain transcriber using official SDK

        Args:
            api_key: Voicegain API key (or from environment)
        """
        self.api_key = api_key or os.getenv('VOICEGAIN_API_KEY')
        if not self.api_key:
            raise ValueError("VOICEGAIN_API_KEY not found in environment variables")

        # Configure the SDK
        configuration = Configuration()
        configuration.host = "https://api.voicegain.ai/v1"
        configuration.access_token = self.api_key

        # Create API clients
        self.api_client = ApiClient(configuration)
        self.transcribe_api = TranscribeApi(self.api_client)
        self.data_api = DataApi(self.api_client)

        logger.info("Voicegain transcriber initialized successfully using SDK")

    def transcribe_with_analytics(
        self,
        audio_path: str,
        progress_callback: Optional[callable] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Transcribe audio with speaker diarization, gender, and age detection

        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (segments, speakers) where:
                - segments: List of transcript segments with speaker labels
                - speakers: List of speaker profiles with gender and age
        """
        try:
            if progress_callback:
                progress_callback("Uploading audio to Voicegain...")

            # Step 1: Upload audio file
            object_id = self._upload_audio(audio_path)

            if progress_callback:
                progress_callback("Starting transcription with speaker analytics...")

            # Step 2: Start transcription with analytics
            session_id = self._start_transcription(object_id)

            # Step 3: Poll for results
            result = self._poll_for_results(session_id, progress_callback)

            # Step 4: Parse results
            segments, speakers = self._parse_results(result)

            if progress_callback:
                progress_callback(f"Transcription complete: {len(segments)} segments, {len(speakers)} speakers")

            return segments, speakers

        except Exception as e:
            logger.error(f"Voicegain transcription failed: {e}")
            raise

    def _upload_audio(self, audio_path: str) -> str:
        """Upload audio file to Voicegain using SDK"""
        try:
            # Create data object request
            file_name = os.path.basename(audio_path)

            # Create the data object first
            data_object = DataObject(
                name=file_name,
                description="Georgian voiceover transcription"
            )

            # Create the data object and get upload URL
            response = self.data_api.create_data_object(data_object=data_object)

            # Upload the file content
            with open(audio_path, 'rb') as f:
                import requests
                upload_response = requests.put(response.url, data=f)
                upload_response.raise_for_status()

            logger.info(f"Audio uploaded successfully: {response.object_id}")
            return response.object_id

        except Exception as e:
            logger.error(f"Failed to upload audio: {e}")
            raise

    def _start_transcription(self, audio_object_id: str) -> str:
        """Start transcription with analytics using SDK"""
        try:
            # Create transcription request
            transcribe_request = TranscribeRequestAsync(
                audio=AudioInput(
                    source=AudioSource(
                        data_store=DataStore(
                            object_id=audio_object_id
                        )
                    )
                ),
                settings=TranscriptionSettings(
                    asr=AsrSettings(
                        languages=["en-US"],  # Will auto-detect if needed
                        acoustic_model="latest",
                        no_input_timeout=60000,
                        complete_timeout=3600000
                    ),
                    speaker=SpeakerSettings(
                        diarization=DiarizationSettings(
                            enable=True,
                            min_speakers=1,
                            max_speakers=10
                        )
                    ),
                    analytics=AnalyticsSettings(
                        enable=True,
                        gender=True,
                        age=True,
                        emotion=False  # We don't need emotion for now
                    )
                ),
                output=OutputSettings(
                    format="json-srt"  # Get both JSON and SRT-like timing
                )
            )

            # Start async transcription
            response = self.transcribe_api.asr_transcribe_async(
                transcribe_request_async=transcribe_request
            )

            logger.info(f"Transcription started: session_id={response.session_id}")
            return response.session_id

        except Exception as e:
            logger.error(f"Failed to start transcription: {e}")
            raise

    def _poll_for_results(self, session_id: str, progress_callback: Optional[callable] = None) -> Dict:
        """Poll for transcription results using SDK"""
        max_polls = 300  # 5 minutes max
        poll_interval = 1  # Start with 1 second

        for i in range(max_polls):
            try:
                # Get transcription status
                result = self.transcribe_api.asr_transcribe_get(session_id=session_id)

                if result.status == "COMPLETED":
                    return result.to_dict()
                elif result.status == "FAILED":
                    raise Exception(f"Transcription failed: {getattr(result, 'error', 'Unknown error')}")

                if progress_callback and i % 5 == 0:
                    progress_callback(f"Processing... ({i}/{max_polls})")

                time.sleep(poll_interval)
                # Increase poll interval over time
                if i > 10:
                    poll_interval = 2
                if i > 30:
                    poll_interval = 5

            except Exception as e:
                if "404" in str(e):
                    # Session might not be ready yet
                    time.sleep(poll_interval)
                    continue
                raise

        raise Exception("Transcription timed out")

    def _parse_results(self, result: Dict) -> Tuple[List[Dict], List[Dict]]:
        """
        Parse Voicegain results into our format

        Returns:
            Tuple of (segments, speakers)
        """
        segments = []
        speakers = {}

        # Parse the transcript
        if 'transcript' in result:
            transcript = result['transcript']

            # Extract speaker information from analytics
            if 'speakers' in result:
                for speaker_data in result['speakers']:
                    speaker_id = speaker_data.get('speaker_id', f"speaker_{len(speakers)}")
                    speakers[speaker_id] = {
                        'id': speaker_id,
                        'label': speaker_data.get('label', f"Speaker {len(speakers) + 1}"),
                        'gender': speaker_data.get('gender', 'unknown'),
                        'age': speaker_data.get('age_group', 'unknown')
                    }

            # Parse segments with timing
            if 'segments' in transcript:
                for seg in transcript['segments']:
                    segment = {
                        'text': seg.get('text', ''),
                        'start': seg.get('start', 0) / 1000.0,  # Convert ms to seconds
                        'end': seg.get('end', 0) / 1000.0,
                        'speaker': seg.get('speaker', 'speaker_0')
                    }
                    segments.append(segment)
            elif 'words' in transcript:
                # If we have word-level timing, group into segments
                current_segment = None
                for word in transcript['words']:
                    speaker = word.get('speaker', 'speaker_0')

                    if current_segment is None or current_segment['speaker'] != speaker:
                        if current_segment:
                            segments.append(current_segment)
                        current_segment = {
                            'text': word.get('text', ''),
                            'start': word.get('start', 0) / 1000.0,
                            'end': word.get('end', 0) / 1000.0,
                            'speaker': speaker
                        }
                    else:
                        current_segment['text'] += ' ' + word.get('text', '')
                        current_segment['end'] = word.get('end', 0) / 1000.0

                if current_segment:
                    segments.append(current_segment)

        # If no speaker analytics, create default speakers
        if not speakers:
            unique_speakers = set(seg.get('speaker', 'speaker_0') for seg in segments)
            for idx, speaker_id in enumerate(unique_speakers):
                speakers[speaker_id] = {
                    'id': speaker_id,
                    'label': f"Speaker {idx + 1}",
                    'gender': 'unknown',
                    'age': 'unknown'
                }

        # Merge short segments from the same speaker
        merged_segments = []
        for segment in segments:
            if merged_segments and \
               merged_segments[-1]['speaker'] == segment['speaker'] and \
               segment['start'] - merged_segments[-1]['end'] < 1.5:
                # Merge with previous segment
                merged_segments[-1]['text'] += ' ' + segment['text']
                merged_segments[-1]['end'] = segment['end']
            else:
                merged_segments.append(segment)

        logger.info(f"Parsed {len(merged_segments)} segments and {len(speakers)} speakers")

        return merged_segments, list(speakers.values())