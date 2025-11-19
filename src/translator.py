"""
Translation Module
Translates text to Georgian using OpenAI GPT-4 for natural, context-aware translations
"""

import os
import openai


class Translator:
    def __init__(self):
        """Initialize OpenAI for AI-powered translation"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        openai.api_key = api_key
        self.target_language = 'Georgian'

    def translate_segments(self, segments, progress_callback=None):
        """
        Translate text segments to Georgian using GPT-4 for natural translation

        Args:
            segments: List of segments with 'text', 'start', 'end'
            progress_callback: Optional callback for progress updates

        Returns:
            List of segments with translated text added as 'translated_text'
        """
        if progress_callback:
            progress_callback(f"AI translating {len(segments)} segments to Georgian...")

        # Combine all segments into one request for better context
        full_text = "\n\n".join([f"[{i}] {seg['text']}" for i, seg in enumerate(segments)])

        if progress_callback:
            progress_callback("Sending to GPT-4 for context-aware translation...")

        # Use GPT-4 for high-quality translation
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",  # Latest GPT-4 model
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert translator specializing in English to Georgian translation.
Your translations must be:
1. Natural and fluent in Georgian, not word-for-word mechanical translations
2. Contextually appropriate with proper Georgian grammar
3. Suitable for voiceover narration (spoken language, not overly formal)
4. Culturally appropriate for Georgian speakers
5. Maintain the meaning and tone of the original

Translate each numbered segment below into Georgian. Keep the same numbering format [0], [1], etc.
Do not add any explanations, just provide the translations."""
                    },
                    {
                        "role": "user",
                        "content": f"Translate these segments to Georgian:\n\n{full_text}"
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent translations
            )

            # Parse the response
            translated_full = response['choices'][0]['message']['content']

            # Split back into segments
            translated_lines = translated_full.strip().split('\n\n')

            translated_segments = []
            for i, segment in enumerate(segments):
                # Find the corresponding translation
                translation = None
                for line in translated_lines:
                    if line.startswith(f"[{i}]"):
                        translation = line[len(f"[{i}]"):].strip()
                        break

                if not translation:
                    # Fallback: translate individually if batch failed
                    translation = self._translate_single(segment['text'])

                translated_segment = segment.copy()
                translated_segment['translated_text'] = translation
                translated_segment['original_text'] = segment['text']
                translated_segments.append(translated_segment)

                if progress_callback and (i + 1) % 10 == 0:
                    progress_callback(f"Processed {i + 1}/{len(segments)} translations")

        except Exception as e:
            # Fallback: translate segments individually
            if progress_callback:
                progress_callback(f"Batch translation failed, translating individually...")

            translated_segments = []
            for i, segment in enumerate(segments):
                translation = self._translate_single(segment['text'])

                translated_segment = segment.copy()
                translated_segment['translated_text'] = translation
                translated_segment['original_text'] = segment['text']
                translated_segments.append(translated_segment)

                if progress_callback and (i + 1) % 5 == 0:
                    progress_callback(f"Translated {i + 1}/{len(segments)} segments")

        if progress_callback:
            progress_callback(f"AI translation complete: {len(translated_segments)} segments")

        return translated_segments

    def _translate_single(self, text):
        """
        Translate a single text segment to Georgian

        Args:
            text: Text to translate

        Returns:
            Translated text
        """
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert translator specializing in English to Georgian translation.
Provide natural, fluent Georgian translations suitable for voiceover narration.
Use proper Georgian grammar and culturally appropriate expressions.
Only respond with the translation, no explanations."""
                    },
                    {
                        "role": "user",
                        "content": f"Translate to Georgian: {text}"
                    }
                ],
                temperature=0.3,
            )

            return response['choices'][0]['message']['content'].strip()

        except Exception as e:
            # Ultimate fallback: return original text with error marker
            print(f"Translation error: {e}")
            return f"[Translation Error] {text}"

    def translate_text(self, text):
        """
        Translate a single text string to Georgian

        Args:
            text: Text to translate

        Returns:
            Translated text
        """
        return self._translate_single(text)
