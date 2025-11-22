"""
Console Logger for Real-Time Debug Output
Shows processing logs in the web UI console
"""

from datetime import datetime
from typing import List, Dict, Optional
import threading
from collections import deque

class ConsoleLogger:
    """Singleton console logger for web UI display"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the console logger"""
        # Keep last 500 log entries
        self.logs = deque(maxlen=500)
        self.session_logs = {}  # Logs per session/job

    def log(self, message: str, level: str = "INFO", session_id: Optional[str] = None):
        """Add a log entry"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }

        # Add to global logs
        self.logs.append(entry)

        # Add to session-specific logs if session_id provided
        if session_id:
            if session_id not in self.session_logs:
                self.session_logs[session_id] = deque(maxlen=200)
            self.session_logs[session_id].append(entry)

    def get_logs(self, session_id: Optional[str] = None, last_n: int = 100) -> List[Dict]:
        """Get recent logs"""
        if session_id and session_id in self.session_logs:
            logs = list(self.session_logs[session_id])
        else:
            logs = list(self.logs)

        # Return last N logs
        return logs[-last_n:]

    def clear_session(self, session_id: str):
        """Clear logs for a specific session"""
        if session_id in self.session_logs:
            del self.session_logs[session_id]

    def format_for_display(self, logs: List[Dict]) -> str:
        """Format logs for console display"""
        formatted = []
        for log in logs:
            timestamp = log['timestamp'].split('T')[1].split('.')[0]  # Just time
            level = log['level'].ljust(5)

            # Color coding for different levels
            if log['level'] == 'ERROR':
                formatted.append(f"❌ [{timestamp}] {log['message']}")
            elif log['level'] == 'WARNING':
                formatted.append(f"⚠️ [{timestamp}] {log['message']}")
            elif log['level'] == 'SUCCESS':
                formatted.append(f"✅ [{timestamp}] {log['message']}")
            elif log['level'] == 'DEBUG':
                formatted.append(f"🔍 [{timestamp}] {log['message']}")
            else:
                formatted.append(f"ℹ️ [{timestamp}] {log['message']}")

        return '\n'.join(formatted)

# Global console logger instance
console = ConsoleLogger()


def log_transcription(segments: List[Dict], speakers: List[Dict], session_id: str):
    """Log transcription results to console"""
    console.log("="*60, session_id=session_id)
    console.log("TRANSCRIPTION COMPLETE", level="SUCCESS", session_id=session_id)
    console.log(f"Segments: {len(segments)}", session_id=session_id)
    console.log(f"Speakers: {len(speakers)}", session_id=session_id)

    # Log first few segments
    for i, seg in enumerate(segments[:3]):
        console.log(
            f"Segment {i+1}: [{seg.get('start', 0):.1f}-{seg.get('end', 0):.1f}s] "
            f"Speaker {seg.get('speaker', '?')}: {seg.get('text', '')[:80]}...",
            session_id=session_id
        )

    if len(segments) > 3:
        console.log(f"... and {len(segments) - 3} more segments", session_id=session_id)

    # Log speaker info
    for speaker in speakers:
        console.log(
            f"Speaker {speaker.get('id')}: {speaker.get('gender', '?')}/{speaker.get('age', '?')}",
            session_id=session_id
        )
    console.log("="*60, session_id=session_id)


def log_translation(original: str, translated: str, speaker: str, session_id: str):
    """Log translation to console"""
    console.log(f"TRANSLATING [{speaker}]:", level="INFO", session_id=session_id)
    console.log(f"  EN: {original[:100]}...", session_id=session_id)
    console.log(f"  GE: {translated[:100]}...", session_id=session_id)


def log_tts(text: str, speaker: str, provider: str, session_id: str):
    """Log TTS generation to console"""
    console.log(
        f"TTS [{provider}] for {speaker}: {text[:80]}...",
        level="INFO",
        session_id=session_id
    )


def log_error(error: str, session_id: Optional[str] = None):
    """Log error to console"""
    console.log(f"ERROR: {error}", level="ERROR", session_id=session_id)


def log_api_call(endpoint: str, status: int, response_preview: str, session_id: str):
    """Log API call details"""
    if status in [200, 201, 202]:
        level = "SUCCESS"
    elif status >= 400:
        level = "ERROR"
    else:
        level = "WARNING"

    console.log(
        f"API {endpoint}: Status {status} - {response_preview[:100]}...",
        level=level,
        session_id=session_id
    )