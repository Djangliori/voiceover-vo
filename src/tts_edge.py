"""
Microsoft Edge TTS - Free, unlimited, multi-voice support
No API key required, supports Georgian with male/female voices
"""

import os
import asyncio
import edge_tts
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.logging_config import get_logger

logger = get_logger(__name__)


class EdgeTTSProvider:
    """Microsoft Edge TTS provider - free, unlimited, multi-voice"""

    # Georgian voices available in Edge TTS
    VOICES = {
        'male': 'ka-GE-GiorgiNeural',
        'female': 'ka-GE-EkaNeural'
    }

    def __init__(self, default_voice='male'):
        """
        Initialize Edge TTS provider

        Args:
            default_voice: 'male' or 'female' for default voice
        """
        self.default_voice = self.VOICES.get(default_voice, self.VOICES['male'])
        self.max_workers = int(os.getenv('TTS_MAX_CONCURRENT', '5'))
        logger.info(f"Edge TTS initialized - Default: {self.default_voice}")

    def generate_voiceover(self, segments, temp_dir="temp", progress_callback=None):
        """
        Generate Georgian voiceover for all segments using Edge TTS

        Args:
            segments: List of segments with 'translated_text', 'start', 'end'
                     Optional: 'speaker' field for multi-voice support
            temp_dir: Directory for temporary audio files
            progress_callback: Optional callback for progress updates

        Returns:
            List of segments with 'audio_path' added
        """
        temp_path = Path(temp_dir)
        temp_path.mkdir(exist_ok=True)

        # Filter out segments with empty text
        valid_segments = []
        skipped_indices = []
        for i, seg in enumerate(segments):
            text = seg.get('translated_text', '').strip()
            if text:
                valid_segments.append((i, seg))
            else:
                skipped_indices.append(i)
                logger.warning(f"Skipping segment {i} - empty translated text")

        if skipped_indices:
            logger.info(f"Skipped {len(skipped_indices)} segments with empty text")

        if progress_callback:
            progress_callback(f"Generating Georgian voiceover with Edge TTS ({len(valid_segments)} segments)...")

        if not valid_segments:
            logger.warning("No valid segments to process")
            return []

        # Process segments in parallel using thread pool
        results = {}
        completed_count = 0
        total_segments = len(valid_segments)

        def process_segment(args):
            """Process a single segment - runs in thread pool"""
            idx, segment = args
            return idx, self._process_single_segment(segment, idx, temp_path)

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(process_segment, (idx, seg)): idx
                for idx, seg in valid_segments
            }

            for future in as_completed(futures):
                try:
                    idx, result = future.result()
                    results[idx] = result
                    completed_count += 1

                    if progress_callback:
                        progress_callback(f"Generated {completed_count}/{total_segments} voiceover segments")
                except Exception as e:
                    idx = futures[future]
                    logger.error(f"Failed to generate segment {idx}: {e}")
                    raise Exception(f"Failed to generate segment {idx}: {str(e)}")

        # Return results sorted by original index
        voiceover_segments = [results[idx] for idx, _ in valid_segments if idx in results]

        if progress_callback:
            progress_callback(f"Voiceover generation complete: {len(voiceover_segments)} segments")

        return voiceover_segments

    def _process_single_segment(self, segment, index, temp_path):
        """
        Process a single segment: synthesize speech with Edge TTS

        Args:
            segment: Segment dict with 'translated_text', 'start', 'end'
                    Optional: 'speaker' for voice selection
            index: Segment index for filename
            temp_path: Path object for temp directory

        Returns:
            Updated segment dict with 'audio_path' and 'audio_duration'
        """
        text = segment['translated_text']

        # Select voice: check 'voice' field first, then 'speaker' field
        if 'voice' in segment:
            # Speaker detection assigned voice directly ('male' or 'female')
            voice = self.VOICES.get(segment['voice'], self.default_voice)
        else:
            # Fall back to speaker-based voice selection
            voice = self._select_voice(segment.get('speaker'))

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                # Synthesize speech using Edge TTS (async)
                audio_path = asyncio.run(self._synthesize_speech(text, voice, index, temp_path))
                break  # Success
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    import time
                    wait_time = (attempt + 1) * 2  # 2, 4, 6 seconds
                    logger.warning(f"Segment {index} error, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    # All retries failed, generate silence
                    logger.warning(f"Segment {index} failed after {max_retries} retries, generating silence")
                    duration = segment.get('end', 0) - segment.get('start', 0)
                    if duration <= 0:
                        duration = 2.0
                    audio_path = self._generate_silence(duration, index, temp_path)
                    break

        # Get audio duration
        duration = self._get_audio_duration(audio_path)

        # Create result segment
        voiceover_segment = segment.copy()
        voiceover_segment['audio_path'] = str(audio_path)
        voiceover_segment['audio_duration'] = duration

        return voiceover_segment

    def _select_voice(self, speaker=None):
        """
        Select appropriate voice based on speaker info

        Args:
            speaker: Speaker identifier (e.g., 'SPEAKER_00', 'SPEAKER_01')
                    or gender ('male', 'female')

        Returns:
            Voice name for Edge TTS
        """
        if not speaker:
            return self.default_voice

        # If speaker is a gender string
        if speaker.lower() in ['male', 'female']:
            return self.VOICES.get(speaker.lower(), self.default_voice)

        # If speaker is SPEAKER_00, SPEAKER_01, etc., alternate voices
        if isinstance(speaker, str) and 'SPEAKER' in speaker.upper():
            try:
                speaker_num = int(speaker.split('_')[-1])
                # Even speakers = male, odd speakers = female
                return self.VOICES['male'] if speaker_num % 2 == 0 else self.VOICES['female']
            except:
                pass

        # Default voice
        return self.default_voice

    async def _synthesize_speech(self, text, voice, index, temp_path):
        """
        Synthesize speech using Edge TTS (async)

        Args:
            text: Text to synthesize
            voice: Voice name (e.g., 'ka-GE-GiorgiNeural')
            index: Segment index for filename
            temp_path: Path object for temp directory

        Returns:
            Path to generated audio file
        """
        # Edge TTS outputs MP3 by default, so we save as .mp3 first
        mp3_filename = f"segment_{index:04d}.mp3"
        mp3_path = temp_path / mp3_filename

        wav_filename = f"segment_{index:04d}.wav"
        wav_path = temp_path / wav_filename

        # Use edge-tts to generate audio (saves as MP3)
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(mp3_path))

        # Convert MP3 to WAV using ffmpeg
        import subprocess
        from src.ffmpeg_utils import get_ffmpeg_path

        ffmpeg_path = get_ffmpeg_path()
        cmd = [
            ffmpeg_path,
            '-i', str(mp3_path),
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            '-ar', '44100',          # 44.1kHz sample rate
            '-ac', '1',              # Mono
            '-y',                    # Overwrite
            str(wav_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"ffmpeg conversion failed: {result.stderr}")
            raise Exception(f"Failed to convert MP3 to WAV: {result.stderr}")

        # Clean up MP3 file
        if mp3_path.exists():
            mp3_path.unlink()

        return wav_path

    def _generate_silence(self, duration_seconds, index, temp_path):
        """
        Generate silent WAV audio for the specified duration

        Args:
            duration_seconds: Duration in seconds
            index: Segment index for filename
            temp_path: Path object for temp directory

        Returns:
            Path to generated silence file
        """
        import struct

        sample_rate = 24000  # Edge TTS uses 24kHz
        num_samples = int(sample_rate * duration_seconds)

        # WAV header for 16-bit mono PCM
        wav_header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            36 + num_samples * 2,
            b'WAVE',
            b'fmt ',
            16,
            1,   # PCM
            1,   # Mono
            sample_rate,
            sample_rate * 2,
            2,
            16,
            b'data',
            num_samples * 2
        )

        silence_data = b'\x00' * (num_samples * 2)

        wav_filename = f"segment_{index:04d}.wav"
        wav_path = temp_path / wav_filename

        with open(wav_path, 'wb') as f:
            f.write(wav_header + silence_data)

        return wav_path

    def _get_audio_duration(self, audio_path):
        """Get audio duration using ffprobe"""
        import subprocess
        from src.ffmpeg_utils import get_ffprobe_path

        ffprobe_path = get_ffprobe_path()

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

    def has_speaker_support(self):
        """Check if provider supports multiple speakers"""
        return True  # Edge TTS supports male/female voices
