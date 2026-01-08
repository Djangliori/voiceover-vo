"""
gTTS (Google Text-to-Speech) - Free Alternative
No API key needed, no content filtering
"""

import os
import io
from gtts import gTTS
from pydub import AudioSegment
from typing import List, Dict, Optional
from src.logging_config import get_logger

logger = get_logger(__name__)


class GTTSProvider:
    """gTTS provider - free, no API key, no content filter"""

    def __init__(self):
        """Initialize gTTS provider"""
        self.language = 'ka'  # Georgian
        logger.info("gTTS provider initialized (free, no content filter)")

    def generate_voiceover(
        self,
        segments: List[Dict],
        output_dir: str = "temp",
        progress_callback: Optional[callable] = None
    ) -> List[str]:
        """
        Generate voiceover audio files using gTTS

        Args:
            segments: List of segments with 'text' field
            output_dir: Directory to save audio files
            progress_callback: Optional callback for progress updates

        Returns:
            List of audio file paths
        """
        audio_files = []
        total_segments = len(segments)

        logger.info(f"Generating voiceover for {total_segments} segments with gTTS")

        for idx, segment in enumerate(segments):
            try:
                text = segment.get('text', '').strip()

                if not text:
                    logger.warning(f"Segment {idx} has no text, skipping")
                    continue

                if progress_callback:
                    progress_callback(
                        f"TTS: Generating voiceover {idx+1}/{total_segments} with gTTS..."
                    )

                # Generate speech with gTTS
                tts = gTTS(text=text, lang=self.language, slow=False)

                # Save to BytesIO first
                audio_fp = io.BytesIO()
                tts.write_to_fp(audio_fp)
                audio_fp.seek(0)

                # Load with pydub and convert to WAV
                audio = AudioSegment.from_mp3(audio_fp)

                # Save as WAV
                output_path = os.path.join(output_dir, f"segment_{idx}.wav")
                audio.export(output_path, format="wav")

                audio_files.append(output_path)

                logger.info(f"Segment {idx}: Generated {len(text)} chars → {output_path}")

            except Exception as e:
                logger.error(f"Failed to generate voiceover for segment {idx}: {e}")
                # Generate silence as fallback
                silence = AudioSegment.silent(duration=2000)  # 2 seconds
                output_path = os.path.join(output_dir, f"segment_{idx}.wav")
                silence.export(output_path, format="wav")
                audio_files.append(output_path)

        if progress_callback:
            progress_callback(f"TTS: Voiceover generation complete: {len(audio_files)} segments")

        logger.info(f"gTTS generation complete: {len(audio_files)} audio files")
        return audio_files

    def has_speaker_support(self) -> bool:
        """Check if provider supports multiple speakers"""
        return False  # gTTS doesn't support speaker selection
