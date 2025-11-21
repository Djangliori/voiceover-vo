"""
Conversation Flow Manager
Manages dialogue flow, speaker turns, and natural conversation pacing
Coordinates between transcription, translation, and voice synthesis
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from src.logging_config import get_logger

logger = get_logger(__name__)


class ConversationType(Enum):
    """Types of conversation patterns"""
    MONOLOGUE = "monologue"
    DIALOGUE = "dialogue"
    INTERVIEW = "interview"
    PRESENTATION = "presentation"
    DISCUSSION = "discussion"


@dataclass
class ConversationTurn:
    """Represents a single conversation turn"""
    speaker: str
    speaker_label: str
    segments: List[Dict]
    start_time: float
    end_time: float
    is_question: bool = False
    is_response: bool = False
    emotion: Optional[str] = None


class ConversationFlowManager:
    """Manages conversation flow and dialogue patterns"""

    def __init__(self):
        """Initialize conversation flow manager"""
        self.conversation_type = None
        self.turns = []
        self.speaker_profiles = {}

    def analyze_conversation(
        self,
        segments: List[Dict],
        speakers: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Analyze conversation structure and patterns

        Args:
            segments: List of transcript segments
            speakers: Optional speaker information

        Returns:
            Analysis results with conversation metadata
        """
        analysis = {
            'type': ConversationType.MONOLOGUE,
            'speaker_count': 1,
            'turn_count': 0,
            'question_answer_pairs': 0,
            'average_turn_duration': 0,
            'dialogue_pace': 'normal',
            'interruptions': 0
        }

        if not segments:
            return analysis

        # Determine conversation type
        has_speakers = any('speaker' in seg for seg in segments)

        if has_speakers:
            unique_speakers = set(seg.get('speaker') for seg in segments if 'speaker' in seg)
            analysis['speaker_count'] = len(unique_speakers)

            if len(unique_speakers) == 1:
                analysis['type'] = ConversationType.MONOLOGUE
            elif len(unique_speakers) == 2:
                # Check if it's an interview pattern
                if self._is_interview_pattern(segments):
                    analysis['type'] = ConversationType.INTERVIEW
                else:
                    analysis['type'] = ConversationType.DIALOGUE
            else:
                analysis['type'] = ConversationType.DISCUSSION

        # Create conversation turns
        self.turns = self._create_turns(segments, speakers)
        analysis['turn_count'] = len(self.turns)

        # Analyze dialogue patterns
        if self.turns:
            analysis['question_answer_pairs'] = self._count_qa_pairs()
            analysis['average_turn_duration'] = self._avg_turn_duration()
            analysis['dialogue_pace'] = self._analyze_pace()
            analysis['interruptions'] = self._detect_interruptions()

        # Store for later use
        self.conversation_type = analysis['type']

        logger.info(f"Conversation analysis: {analysis}")

        return analysis

    def _create_turns(
        self,
        segments: List[Dict],
        speakers: Optional[List[Dict]]
    ) -> List[ConversationTurn]:
        """
        Create conversation turns from segments

        Args:
            segments: Transcript segments
            speakers: Speaker information

        Returns:
            List of conversation turns
        """
        if not segments:
            return []

        turns = []
        current_turn_segments = []
        current_speaker = None

        # Create speaker label mapping
        speaker_labels = {}
        if speakers:
            for speaker in speakers:
                speaker_labels[speaker['id']] = speaker.get('label', f'Speaker {speaker["id"]}')

        for segment in segments:
            seg_speaker = segment.get('speaker', 'unknown')

            if current_speaker is None:
                # First turn
                current_speaker = seg_speaker
                current_turn_segments = [segment]
            elif seg_speaker != current_speaker:
                # Speaker changed - create turn
                if current_turn_segments:
                    turn = self._create_turn(
                        current_turn_segments,
                        current_speaker,
                        speaker_labels.get(current_speaker, f'Speaker {current_speaker}')
                    )
                    turns.append(turn)

                # Start new turn
                current_speaker = seg_speaker
                current_turn_segments = [segment]
            else:
                # Continue current turn
                current_turn_segments.append(segment)

        # Add last turn
        if current_turn_segments:
            turn = self._create_turn(
                current_turn_segments,
                current_speaker,
                speaker_labels.get(current_speaker, f'Speaker {current_speaker}')
            )
            turns.append(turn)

        # Analyze Q&A relationships
        self._analyze_qa_relationships(turns)

        return turns

    def _create_turn(
        self,
        segments: List[Dict],
        speaker: str,
        speaker_label: str
    ) -> ConversationTurn:
        """Create a conversation turn from segments"""
        # Combine text
        full_text = ' '.join(seg['text'] for seg in segments)

        # Detect if it's a question
        is_question = self._is_question(full_text)

        # Detect emotion (basic)
        emotion = self._detect_emotion(full_text)

        return ConversationTurn(
            speaker=speaker,
            speaker_label=speaker_label,
            segments=segments,
            start_time=segments[0]['start'],
            end_time=segments[-1]['end'],
            is_question=is_question,
            emotion=emotion
        )

    def _is_question(self, text: str) -> bool:
        """Check if text is a question"""
        text = text.strip().lower()

        # Check for question mark
        if text.endswith('?'):
            return True

        # Check for question words at start
        question_words = ['what', 'when', 'where', 'who', 'why', 'how', 'can', 'could',
                          'would', 'should', 'is', 'are', 'do', 'does', 'did']

        first_word = text.split()[0] if text.split() else ''
        return first_word in question_words

    def _detect_emotion(self, text: str) -> Optional[str]:
        """Detect basic emotion from text"""
        text_lower = text.lower()

        # Simple keyword-based emotion detection
        if any(word in text_lower for word in ['excited', 'amazing', 'wonderful', 'fantastic', '!']):
            return 'excited'
        elif any(word in text_lower for word in ['sorry', 'sad', 'unfortunately', 'regret']):
            return 'sad'
        elif any(word in text_lower for word in ['angry', 'frustrated', 'annoyed', 'upset']):
            return 'angry'
        elif any(word in text_lower for word in ['confused', 'unsure', "don't understand"]):
            return 'confused'
        elif '?' in text:
            return 'curious'

        return 'neutral'

    def _analyze_qa_relationships(self, turns: List[ConversationTurn]):
        """Analyze question-answer relationships between turns"""
        for i in range(len(turns) - 1):
            current = turns[i]
            next_turn = turns[i + 1]

            # If current is a question and next is from different speaker
            if current.is_question and current.speaker != next_turn.speaker:
                next_turn.is_response = True

    def _is_interview_pattern(self, segments: List[Dict]) -> bool:
        """Check if conversation follows interview pattern"""
        # Interview pattern: One speaker asks most questions, other responds
        speaker_questions = {}

        for seg in segments:
            speaker = seg.get('speaker', 'unknown')
            if speaker not in speaker_questions:
                speaker_questions[speaker] = {'questions': 0, 'total': 0}

            speaker_questions[speaker]['total'] += 1
            if self._is_question(seg['text']):
                speaker_questions[speaker]['questions'] += 1

        # Check if one speaker is primarily asking questions
        if len(speaker_questions) == 2:
            speakers = list(speaker_questions.values())
            # If one speaker asks >60% questions and other asks <20%
            q_ratios = [s['questions'] / max(s['total'], 1) for s in speakers]
            return (max(q_ratios) > 0.6 and min(q_ratios) < 0.2)

        return False

    def _count_qa_pairs(self) -> int:
        """Count question-answer pairs in conversation"""
        count = 0
        for i in range(len(self.turns) - 1):
            if self.turns[i].is_question and self.turns[i + 1].is_response:
                count += 1
        return count

    def _avg_turn_duration(self) -> float:
        """Calculate average turn duration"""
        if not self.turns:
            return 0
        total_duration = sum(t.end_time - t.start_time for t in self.turns)
        return total_duration / len(self.turns)

    def _analyze_pace(self) -> str:
        """Analyze conversation pace"""
        if not self.turns:
            return 'normal'

        avg_duration = self._avg_turn_duration()

        if avg_duration < 3:
            return 'fast'  # Rapid exchanges
        elif avg_duration < 10:
            return 'normal'
        else:
            return 'slow'  # Long monologues

    def _detect_interruptions(self) -> int:
        """Detect potential interruptions (overlapping speech)"""
        interruptions = 0

        for i in range(len(self.turns) - 1):
            current = self.turns[i]
            next_turn = self.turns[i + 1]

            # Check for overlap or very small gap (< 0.1s)
            gap = next_turn.start_time - current.end_time
            if gap < 0.1:  # Less than 100ms gap suggests interruption
                interruptions += 1

        return interruptions

    def optimize_for_voiceover(
        self,
        segments: List[Dict],
        target_language: str = 'Georgian'
    ) -> List[Dict]:
        """
        Optimize segments for voiceover generation

        Args:
            segments: Translated segments
            target_language: Target language for voiceover

        Returns:
            Optimized segments for better voiceover flow
        """
        optimized = []

        for i, segment in enumerate(segments):
            opt_segment = segment.copy()

            # Add pause hints for natural flow
            if i > 0:
                prev_segment = segments[i - 1]

                # Add longer pause after questions
                if self._is_question(prev_segment.get('original_text', '')):
                    opt_segment['pause_before'] = 0.8
                # Add pause for speaker changes
                elif prev_segment.get('speaker') != segment.get('speaker'):
                    opt_segment['pause_before'] = 0.5
                else:
                    opt_segment['pause_before'] = 0.2

            # Add emotion hints for TTS
            if 'original_text' in segment:
                emotion = self._detect_emotion(segment['original_text'])
                if emotion and emotion != 'neutral':
                    opt_segment['emotion_hint'] = emotion

            # Mark if this is a response to a question
            if i > 0 and self._is_question(segments[i - 1].get('original_text', '')):
                opt_segment['is_response'] = True

            optimized.append(opt_segment)

        logger.info(f"Optimized {len(optimized)} segments for voiceover")

        return optimized

    def generate_voice_instructions(
        self,
        segment: Dict,
        speaker_profile: Optional[Dict] = None
    ) -> Dict:
        """
        Generate voice synthesis instructions for a segment

        Args:
            segment: Segment to generate voice for
            speaker_profile: Optional speaker profile

        Returns:
            Voice synthesis parameters
        """
        instructions = {
            'text': segment.get('translated_text', segment.get('text', '')),
            'speed': 1.0,
            'pitch': 1.0,
            'emotion': 'neutral'
        }

        # Adjust for emotion
        emotion = segment.get('emotion_hint', 'neutral')
        if emotion == 'excited':
            instructions['speed'] = 1.1
            instructions['pitch'] = 1.05
            instructions['emotion'] = 'excited'
        elif emotion == 'sad':
            instructions['speed'] = 0.95
            instructions['pitch'] = 0.95
            instructions['emotion'] = 'sad'
        elif emotion == 'curious':
            instructions['pitch'] = 1.02
            instructions['emotion'] = 'curious'

        # Adjust for questions
        if segment.get('is_question') or self._is_question(segment.get('original_text', '')):
            instructions['pitch'] = 1.03  # Slight pitch rise for questions

        # Adjust for responses
        if segment.get('is_response'):
            instructions['pause_before'] = 0.5  # Natural pause before answering

        # Apply speaker-specific adjustments
        if speaker_profile:
            # Future: Apply voice characteristics based on speaker profile
            pass

        return instructions