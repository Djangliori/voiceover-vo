"""
Segment Merger Module
Groups transcription segments into paragraphs for natural translation
Maintains speaker boundaries and conversation context
"""

import re
from typing import List, Dict, Optional, Tuple
from src.logging_config import get_logger

logger = get_logger(__name__)


class SegmentMerger:
    """Intelligently merges segments into paragraphs for translation"""

    def __init__(
        self,
        max_paragraph_duration: float = 30.0,
        min_paragraph_duration: float = 5.0,
        max_paragraph_words: int = 150,
        min_paragraph_words: int = 20
    ):
        """
        Initialize segment merger

        Args:
            max_paragraph_duration: Maximum paragraph duration in seconds
            min_paragraph_duration: Minimum paragraph duration in seconds
            max_paragraph_words: Maximum words per paragraph
            min_paragraph_words: Minimum words per paragraph
        """
        self.max_duration = max_paragraph_duration
        self.min_duration = min_paragraph_duration
        self.max_words = max_paragraph_words
        self.min_words = min_paragraph_words

    def merge_segments_to_paragraphs(
        self,
        segments: List[Dict],
        speakers: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Merge segments into paragraphs suitable for translation

        Args:
            segments: List of transcription segments
            speakers: Optional speaker information

        Returns:
            List of paragraph-level segments
        """
        if not segments:
            return []

        # If we have speaker information, group by speaker first
        if self._has_speaker_info(segments):
            return self._merge_with_speakers(segments, speakers)
        else:
            return self._merge_without_speakers(segments)

    def _has_speaker_info(self, segments: List[Dict]) -> bool:
        """Check if segments have speaker information"""
        return any('speaker' in seg for seg in segments)

    def _merge_with_speakers(
        self,
        segments: List[Dict],
        speakers: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Merge segments while respecting speaker boundaries

        Args:
            segments: List of segments with speaker info
            speakers: Optional speaker profiles

        Returns:
            List of merged paragraphs
        """
        paragraphs = []
        current_para = None

        for segment in segments:
            # Check if we should start a new paragraph
            should_split = False

            if current_para is None:
                # Start first paragraph
                current_para = self._create_paragraph(segment)
            elif segment.get('speaker') != current_para.get('speaker'):
                # Speaker changed - always split
                should_split = True
            else:
                # Same speaker - check other criteria
                should_split = self._should_split_paragraph(current_para, segment)

            if should_split:
                # Finalize current paragraph
                if current_para:
                    paragraphs.append(self._finalize_paragraph(current_para))
                # Start new paragraph
                current_para = self._create_paragraph(segment)
            else:
                # Extend current paragraph
                current_para = self._extend_paragraph(current_para, segment)

        # Don't forget the last paragraph
        if current_para:
            paragraphs.append(self._finalize_paragraph(current_para))

        logger.info(f"Merged {len(segments)} segments into {len(paragraphs)} speaker-aware paragraphs")

        # Add speaker labels if available
        if speakers:
            self._add_speaker_labels(paragraphs, speakers)

        return paragraphs

    def _merge_without_speakers(self, segments: List[Dict]) -> List[Dict]:
        """
        Merge segments based on natural breaks and length constraints

        Args:
            segments: List of segments without speaker info

        Returns:
            List of merged paragraphs
        """
        paragraphs = []
        current_para = None

        for segment in segments:
            if current_para is None:
                # Start first paragraph
                current_para = self._create_paragraph(segment)
            elif self._should_split_paragraph(current_para, segment):
                # Split into new paragraph
                paragraphs.append(self._finalize_paragraph(current_para))
                current_para = self._create_paragraph(segment)
            else:
                # Extend current paragraph
                current_para = self._extend_paragraph(current_para, segment)

        # Add last paragraph
        if current_para:
            paragraphs.append(self._finalize_paragraph(current_para))

        logger.info(f"Merged {len(segments)} segments into {len(paragraphs)} paragraphs")

        return paragraphs

    def _should_split_paragraph(self, current: Dict, next_seg: Dict) -> bool:
        """
        Determine if we should split into a new paragraph

        Args:
            current: Current paragraph being built
            next_seg: Next segment to consider

        Returns:
            True if should split, False otherwise
        """
        # Calculate current metrics
        current_duration = current['end'] - current['start']
        current_words = len(current['text'].split())
        gap_duration = next_seg['start'] - current['end']

        # Check duration constraints
        if current_duration >= self.max_duration:
            return True

        # Check word count constraints
        if current_words >= self.max_words:
            return True

        # Check for natural breaks (long pauses)
        if gap_duration > 2.0:  # 2+ second pause suggests natural break
            return True

        # Check for sentence boundaries if we have enough content
        if current_duration >= self.min_duration and current_words >= self.min_words:
            # Look for sentence-ending punctuation
            if re.search(r'[.!?]\s*$', current['text'].strip()):
                return True

        return False

    def _create_paragraph(self, segment: Dict) -> Dict:
        """Create a new paragraph from a segment"""
        para = segment.copy()
        para['segments'] = [segment]  # Track original segments
        para['segment_count'] = 1
        return para

    def _extend_paragraph(self, paragraph: Dict, segment: Dict) -> Dict:
        """Extend a paragraph with a new segment"""
        # Add text with proper spacing
        if paragraph['text'] and not paragraph['text'].endswith(' '):
            paragraph['text'] += ' '
        paragraph['text'] += segment['text']

        # Update timing
        paragraph['end'] = segment['end']

        # Track segments
        paragraph['segments'].append(segment)
        paragraph['segment_count'] += 1

        return paragraph

    def _finalize_paragraph(self, paragraph: Dict) -> Dict:
        """Finalize a paragraph for output"""
        # Clean up text
        paragraph['text'] = self._clean_text(paragraph['text'])

        # Add metadata
        paragraph['duration'] = paragraph['end'] - paragraph['start']
        paragraph['word_count'] = len(paragraph['text'].split())
        paragraph['type'] = 'paragraph'

        # Remove temporary tracking
        if 'segments' in paragraph:
            del paragraph['segments']

        return paragraph

    def _clean_text(self, text: str) -> str:
        """Clean up paragraph text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Ensure proper sentence capitalization
        sentences = re.split(r'([.!?]\s+)', text)
        cleaned = []

        for i, part in enumerate(sentences):
            if i % 2 == 0 and part:  # Text parts (not punctuation)
                # Capitalize first letter
                part = part[0].upper() + part[1:] if len(part) > 0 else part
            cleaned.append(part)

        return ''.join(cleaned)

    def _add_speaker_labels(self, paragraphs: List[Dict], speakers: List[Dict]):
        """Add human-readable speaker labels to paragraphs"""
        # Create speaker ID to label mapping
        speaker_map = {s['id']: s['label'] for s in speakers}

        for para in paragraphs:
            if 'speaker' in para:
                speaker_id = para['speaker']
                para['speaker_label'] = speaker_map.get(speaker_id, f'Speaker {speaker_id}')

    def group_by_conversation_turn(
        self,
        paragraphs: List[Dict]
    ) -> List[List[Dict]]:
        """
        Group paragraphs by conversation turns (speaker changes)

        Args:
            paragraphs: List of paragraph segments

        Returns:
            List of conversation turns, each containing paragraphs from same speaker
        """
        if not paragraphs:
            return []

        turns = []
        current_turn = []
        current_speaker = None

        for para in paragraphs:
            para_speaker = para.get('speaker')

            if current_speaker is None:
                # First turn
                current_speaker = para_speaker
                current_turn = [para]
            elif para_speaker != current_speaker:
                # Speaker changed - new turn
                if current_turn:
                    turns.append(current_turn)
                current_speaker = para_speaker
                current_turn = [para]
            else:
                # Same speaker - continue turn
                current_turn.append(para)

        # Add last turn
        if current_turn:
            turns.append(current_turn)

        logger.info(f"Grouped {len(paragraphs)} paragraphs into {len(turns)} conversation turns")

        return turns

    def calculate_translation_context(
        self,
        paragraphs: List[Dict],
        current_index: int,
        context_window: int = 2
    ) -> Dict:
        """
        Calculate context for translating a specific paragraph

        Args:
            paragraphs: All paragraphs
            current_index: Index of paragraph to translate
            context_window: Number of previous paragraphs to include

        Returns:
            Context information for translation
        """
        context = {
            'current': paragraphs[current_index],
            'previous': [],
            'speaker_history': {},
            'conversation_flow': []
        }

        # Get previous context
        start_idx = max(0, current_index - context_window)
        for i in range(start_idx, current_index):
            context['previous'].append(paragraphs[i])

            # Track what each speaker has said
            speaker = paragraphs[i].get('speaker', 'unknown')
            if speaker not in context['speaker_history']:
                context['speaker_history'][speaker] = []
            context['speaker_history'][speaker].append(paragraphs[i]['text'])

        # Analyze conversation flow
        if context['previous']:
            # Check if it's a question-answer pattern
            last_text = context['previous'][-1]['text'] if context['previous'] else ''
            if re.search(r'[?]\s*$', last_text):
                context['conversation_flow'].append('responding_to_question')

            # Check if speakers are alternating (dialogue)
            speakers = [p.get('speaker') for p in context['previous'] + [paragraphs[current_index]]]
            if len(set(speakers)) > 1:
                context['conversation_flow'].append('dialogue')
            else:
                context['conversation_flow'].append('monologue')

        return context