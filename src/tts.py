"""
Text-to-Speech Module
Generates Georgian voiceover using ElevenLabs API
Supports parallel requests for faster processing
"""

import os
import ffmpeg
from concurrent.futures import ThreadPoolExecutor, as_completed
from elevenlabs import ElevenLabs
from pathlib import Path


class TextToSpeech:
    def __init__(self):
        """Initialize ElevenLabs Text-to-Speech client"""
        api_key = os.getenv('ELEVENLABS_API_KEY')
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY not found in environment variables")

        self.client = ElevenLabs(api_key=api_key)

        # Use Georgian voice
        self.voice_id = "TX3LPaxmHKxFdv7VOQHJ"  # Liam voice for Georgian

        # Model settings - using Eleven v3 for best quality
        self.model_id = "eleven_v3"  # Most expressive model

        # Parallel processing settings
        # ElevenLabs concurrent limits: Free=2, Starter=3, Creator=5, Pro=10, Scale=15
        self.max_workers = int(os.getenv('ELEVENLABS_MAX_CONCURRENT', '3'))

    def generate_voiceover(self, segments, temp_dir="temp", progress_callback=None):
        """
        Generate Georgian voiceover for all segments using parallel requests

        Args:
            segments: List of segments with 'translated_text', 'start', 'end'
            temp_dir: Directory for temporary audio files
            progress_callback: Optional callback for progress updates

        Returns:
            List of segments with 'audio_path' added
        """
        temp_path = Path(temp_dir)
        temp_path.mkdir(exist_ok=True)

        if progress_callback:
            progress_callback(f"Generating Georgian voiceover for {len(segments)} segments (parallel)...")

        # Process segments in parallel
        results = {}
        completed_count = 0
        total_segments = len(segments)

        def process_segment(args):
            """Process a single segment - runs in thread pool"""
            idx, segment = args
            return idx, self._process_single_segment(segment, idx, temp_path)

        # Use ThreadPoolExecutor for parallel API calls
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(process_segment, (i, seg)): i
                for i, seg in enumerate(segments)
            }

            # Process completed tasks as they finish
            for future in as_completed(futures):
                idx, result = future.result()
                results[idx] = result
                completed_count += 1

                if progress_callback:
                    progress_callback(f"Generated {completed_count}/{total_segments} voiceover segments")

        # Sort results by original index to maintain order
        voiceover_segments = [results[i] for i in range(len(segments))]

        if progress_callback:
            progress_callback(f"Voiceover generation complete: {len(voiceover_segments)} segments")

        return voiceover_segments

    def _process_single_segment(self, segment, index, temp_path):
        """
        Process a single segment: synthesize speech, save, and convert to WAV

        Args:
            segment: Segment dict with 'translated_text', 'start', 'end'
            index: Segment index for filename
            temp_path: Path object for temp directory

        Returns:
            Updated segment dict with 'audio_path' and 'audio_duration'
        """
        # Generate speech for this segment
        audio_data = self._synthesize_speech(segment['translated_text'])

        # Save to temporary file
        audio_filename = f"segment_{index:04d}.mp3"
        audio_path = temp_path / audio_filename

        # Save the audio data
        with open(audio_path, 'wb') as f:
            for chunk in audio_data:
                f.write(chunk)

        # Convert MP3 to WAV for consistency with rest of pipeline
        wav_filename = f"segment_{index:04d}.wav"
        wav_path = temp_path / wav_filename

        # Use ffmpeg-python for conversion
        stream = ffmpeg.input(str(audio_path))
        stream = ffmpeg.output(stream, str(wav_path), acodec='pcm_s16le', ar='44100')
        ffmpeg.run(stream, overwrite_output=True, quiet=True)

        # Get audio duration using ffmpeg probe
        probe = ffmpeg.probe(str(wav_path))
        duration = float(probe['streams'][0]['duration'])

        # Remove the MP3 file
        audio_path.unlink()

        # Create result segment
        voiceover_segment = segment.copy()
        voiceover_segment['audio_path'] = str(wav_path)
        voiceover_segment['audio_duration'] = duration

        return voiceover_segment

    def _synthesize_speech(self, text):
        """
        Synthesize speech for a text segment using ElevenLabs

        Args:
            text: Text to synthesize (in Georgian)

        Returns:
            Audio data generator (bytes)
        """
        try:
            # Generate speech using ElevenLabs API with voice settings
            audio_generator = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id=self.model_id,
                output_format="mp3_44100_128",  # High quality audio output
                voice_settings={
                    "stability": 0.5,  # Balance between expressiveness and consistency
                    "similarity_boost": 0.75,  # Higher for more natural voice
                    "style": 0.0,  # No style exaggeration
                    "use_speaker_boost": True  # Enhance voice clarity
                }
            )

            return audio_generator

        except Exception as e:
            raise Exception(f"ElevenLabs TTS error: {str(e)}")

    def set_voice(self, voice_id):
        """
        Change the voice

        Args:
            voice_id: ElevenLabs voice ID
        """
        self.voice_id = voice_id
