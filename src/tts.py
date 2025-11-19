"""
Text-to-Speech Module
Generates Georgian voiceover using ElevenLabs API
"""

import os
import ffmpeg
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

    def generate_voiceover(self, segments, temp_dir="temp", progress_callback=None):
        """
        Generate Georgian voiceover for all segments

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
            progress_callback(f"Generating Georgian voiceover for {len(segments)} segments...")

        voiceover_segments = []

        for i, segment in enumerate(segments):
            # Generate speech for this segment
            audio_data = self._synthesize_speech(segment['translated_text'])

            # Save to temporary file
            audio_filename = f"segment_{i:04d}.mp3"
            audio_path = temp_path / audio_filename

            # Save the audio data
            with open(audio_path, 'wb') as f:
                for chunk in audio_data:
                    f.write(chunk)

            # Convert MP3 to WAV for consistency with rest of pipeline
            wav_filename = f"segment_{i:04d}.wav"
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

            # Add audio path to segment
            voiceover_segment = segment.copy()
            voiceover_segment['audio_path'] = str(wav_path)

            # Calculate audio duration
            voiceover_segment['audio_duration'] = duration

            voiceover_segments.append(voiceover_segment)

            if progress_callback and (i + 1) % 5 == 0:
                progress_callback(f"Generated {i + 1}/{len(segments)} voiceover segments")

        if progress_callback:
            progress_callback(f"Voiceover generation complete: {len(voiceover_segments)} segments")

        return voiceover_segments

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
