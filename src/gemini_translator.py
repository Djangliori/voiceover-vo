"""
Gemini Translation Module
Translates text to Georgian using Google Gemini API (FREE alternative to OpenAI)
"""

import os
from typing import List, Dict, Optional
from google import genai
from google.genai import types
from src.logging_config import get_logger

logger = get_logger(__name__)


class GeminiTranslator:
    """Translator using Google Gemini API"""

    def __init__(self):
        """Initialize Gemini API"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        # Initialize client with new google.genai package
        self.client = genai.Client(api_key=api_key)

        # Use Gemini 2.5 Flash (free tier: 15 RPM, 1500 RPD, fast and efficient)
        self.model_name = 'models/gemini-2.5-flash'

        logger.info(f"Initialized Gemini translator with {self.model_name} (FREE tier)")

    def translate_text(self, text: str) -> str:
        """
        Translate a single text to Georgian

        Args:
            text: English text to translate

        Returns:
            Georgian translation
        """
        try:
            prompt = f"""You are an expert translator specializing in English to Georgian translation.
Provide natural, fluent Georgian translations suitable for voiceover narration.
Use proper Georgian grammar and culturally appropriate expressions.
Only respond with the translation, no explanations.

Translate to Georgian: {text}"""

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip()

        except Exception as e:
            logger.error(f"Gemini translation failed: {e}")
            return f"[Translation Error] {text}"

    def translate_batch(self, texts: List[str], progress_callback=None) -> List[str]:
        """
        Translate multiple texts to Georgian

        Args:
            texts: List of English texts
            progress_callback: Optional progress callback

        Returns:
            List of Georgian translations
        """
        translations = []
        total = len(texts)

        for i, text in enumerate(texts):
            if progress_callback and (i + 1) % 5 == 0:
                progress_callback(f"Translating {i+1}/{total} segments...")

            translation = self.translate_text(text)
            translations.append(translation)

        return translations

    def translate_segments(self, segments: List[Dict], progress_callback=None) -> List[Dict]:
        """
        Translate segments with context awareness

        Args:
            segments: List of segments with 'text', 'start', 'end'
            progress_callback: Optional progress callback

        Returns:
            Segments with added 'translated_text' field
        """
        if progress_callback:
            progress_callback(f"AI translating {len(segments)} segments to Georgian...")

        # Combine segments for better context
        full_text = "\n\n".join([f"[{i}] {seg['text']}" for i, seg in enumerate(segments)])

        if progress_callback:
            progress_callback("Sending to Gemini for context-aware translation...")

        try:
            # Create context-aware prompt
            prompt = f"""You are an expert translator specializing in English to Georgian translation.
Your translations must be:
1. Natural and fluent in Georgian, not word-for-word mechanical translations
2. Contextually appropriate with proper Georgian grammar
3. Suitable for voiceover narration (spoken language, not overly formal)
4. Culturally appropriate for Georgian speakers
5. Maintain the meaning and tone of the original

Translate each numbered segment below into Georgian. Keep the same numbering format [0], [1], etc.
Do not add any explanations, just provide the translations.

{full_text}"""

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            translated_full = response.text.strip()

            # Split back into segments
            translated_lines = translated_full.split('\n\n')

            translated_segments = []
            for i, segment in enumerate(segments):
                # Find corresponding translation
                translation = None
                for line in translated_lines:
                    if line.startswith(f"[{i}]"):
                        translation = line[len(f"[{i}]"):].strip()
                        break

                if not translation:
                    # Fallback: translate individually
                    translation = self.translate_text(segment['text'])

                translated_segment = segment.copy()
                translated_segment['translated_text'] = translation
                translated_segment['original_text'] = segment['text']
                translated_segments.append(translated_segment)

                if progress_callback and (i + 1) % 10 == 0:
                    progress_callback(f"Processed {i + 1}/{len(segments)} translations")

        except Exception as e:
            logger.error(f"Batch translation failed: {e}")

            # Fallback: translate individually
            if progress_callback:
                progress_callback("Batch translation failed, translating individually...")

            translated_segments = []
            for i, segment in enumerate(segments):
                translation = self.translate_text(segment['text'])

                translated_segment = segment.copy()
                translated_segment['translated_text'] = translation
                translated_segment['original_text'] = segment['text']
                translated_segments.append(translated_segment)

                if progress_callback and (i + 1) % 5 == 0:
                    progress_callback(f"Translated {i + 1}/{len(segments)} segments")

        if progress_callback:
            progress_callback(f"AI translation complete: {len(translated_segments)} segments")

        return translated_segments
