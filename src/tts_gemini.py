"""
Text-to-Speech Module using Google Gemini TTS
Generates Georgian voiceover using Google Cloud Text-to-Speech API with Gemini models
Supports parallel requests for faster processing
"""

import os
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Google Cloud TTS imports
from google.cloud import texttospeech


class GeminiTextToSpeech:
    """Text-to-Speech using Google Gemini TTS API"""

    def __init__(self):
        """Initialize Google Cloud Text-to-Speech client with Gemini model"""
        # Check for credentials
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_path and not os.getenv('GOOGLE_CLOUD_PROJECT'):
            raise ValueError(
                "Google Cloud credentials not configured. "
                "Set GOOGLE_APPLICATION_CREDENTIALS or run 'gcloud auth application-default login'"
            )

        self.client = texttospeech.TextToSpeechClient()

        # Gemini TTS configuration for Georgian
        self.language_code = "ka-GE"  # Georgian (Georgia)
        self.model_name = os.getenv('GEMINI_TTS_MODEL', 'gemini-2.5-pro-tts')

        # Voice selection - Achernar works well for Georgian based on user testing
        self.voice_name = os.getenv('GEMINI_TTS_VOICE', 'Achernar')

        # Default prompt for consistent tone
        self.default_prompt = os.getenv(
            'GEMINI_TTS_PROMPT',
            'Read aloud in a clear, natural voice with good pacing.'
        )

        # Parallel processing settings
        self.max_workers = int(os.getenv('GEMINI_TTS_MAX_CONCURRENT', '5'))

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
            progress_callback(f"Generating Georgian voiceover with Gemini TTS ({len(segments)} segments)...")

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
                try:
                    idx, result = future.result()
                    results[idx] = result
                    completed_count += 1

                    if progress_callback:
                        progress_callback(f"Generated {completed_count}/{total_segments} voiceover segments")
                except Exception as e:
                    # Log error but continue with other segments
                    idx = futures[future]
                    raise Exception(f"Failed to generate segment {idx}: {str(e)}")

        # Sort results by original index to maintain order
        voiceover_segments = [results[i] for i in range(len(segments))]

        if progress_callback:
            progress_callback(f"Voiceover generation complete: {len(voiceover_segments)} segments")

        return voiceover_segments

    def _process_single_segment(self, segment, index, temp_path):
        """
        Process a single segment: synthesize speech with Gemini TTS

        Args:
            segment: Segment dict with 'translated_text', 'start', 'end'
            index: Segment index for filename
            temp_path: Path object for temp directory

        Returns:
            Updated segment dict with 'audio_path' and 'audio_duration'
        """
        text = segment['translated_text']

        # Synthesize speech using Gemini TTS
        audio_content = self._synthesize_speech(text)

        # Save to WAV file (Gemini outputs LINEAR16 which is WAV-compatible)
        wav_filename = f"segment_{index:04d}.wav"
        wav_path = temp_path / wav_filename

        with open(wav_path, 'wb') as f:
            f.write(audio_content)

        # Get audio duration using ffprobe
        duration = self._get_audio_duration(wav_path)

        # Create result segment
        voiceover_segment = segment.copy()
        voiceover_segment['audio_path'] = str(wav_path)
        voiceover_segment['audio_duration'] = duration

        return voiceover_segment

    def _synthesize_speech(self, text, prompt=None):
        """
        Synthesize speech for a text segment using Gemini TTS

        Args:
            text: Text to synthesize (in Georgian)
            prompt: Optional style prompt (uses default if not provided)

        Returns:
            Audio content bytes (LINEAR16/WAV format)
        """
        try:
            # Build synthesis input with optional prompt
            synthesis_input = texttospeech.SynthesisInput(
                text=text,
                prompt=prompt or self.default_prompt
            )

            # Configure voice parameters for Gemini TTS
            voice = texttospeech.VoiceSelectionParams(
                language_code=self.language_code,
                name=self.voice_name,
                model_name=self.model_name
            )

            # Audio config - LINEAR16 for WAV output at 44.1kHz
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=44100,
                speaking_rate=1.0,
                pitch=0.0
            )

            # Make the API request
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            return response.audio_content

        except Exception as e:
            raise Exception(f"Gemini TTS error: {str(e)}")

    def _get_audio_duration(self, audio_path):
        """Get audio duration using ffprobe"""
        ffprobe_path = self._get_ffprobe_path()

        cmd = [
            ffprobe_path,
            '-v', 'quiet',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(audio_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
        return 0.0

    def _get_ffprobe_path(self):
        """Get ffprobe path"""
        # Check Nix path first (Railway)
        nix_ffprobe = '/nix/var/nix/profiles/default/bin/ffprobe'
        if os.path.exists(nix_ffprobe):
            return nix_ffprobe

        ffprobe_path = shutil.which('ffprobe')
        if ffprobe_path:
            return ffprobe_path

        for path in ['/usr/bin/ffprobe', '/usr/local/bin/ffprobe']:
            if os.path.exists(path):
                return path

        raise Exception("ffprobe not found")

    def set_voice(self, voice_name):
        """
        Change the voice

        Args:
            voice_name: Gemini voice name (e.g., 'Achernar', 'Charon', 'Kore')
        """
        self.voice_name = voice_name

    def set_prompt(self, prompt):
        """
        Change the default style prompt

        Args:
            prompt: Natural language prompt for voice style
        """
        self.default_prompt = prompt
