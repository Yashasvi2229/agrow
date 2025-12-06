"""
Conversation State Management Module

Tracks multi-turn conversations for AgroWise voice helpline.
Stores Q&A history, manages turn limits, and provides session lifecycle management.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """Represents a single Q&A turn in the conversation."""
    question: str
    answer: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConversationSession:
    """Manages a complete conversation session for a call."""
    call_sid: str
    language: str
    caller_number: str = ""
    turns: List[ConversationTurn] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    
    def add_turn(self, question: str, answer: str) -> None:
        """Add a new Q&A turn to the conversation."""
        self.turns.append(ConversationTurn(
            question=question,
            answer=answer,
            timestamp=datetime.now()
        ))
        logger.info(f"Added turn #{self.get_turn_count()} to conversation {self.call_sid}")
    
    def get_turn_count(self) -> int:
        """Get the number of turns in this conversation."""
        return len(self.turns)
    
    def should_end(self) -> bool:
        """
        Check if conversation should end based on limits.
        
        Returns:
            True if max turns (10) or max time (10 minutes) reached
        """
        # End after 10 Q&A turns
        if self.get_turn_count() >= 10:
            logger.info(f"Conversation {self.call_sid} reached max turns (10)")
            return True
        
        # End after 10 minutes total call duration
        duration_seconds = (datetime.now() - self.start_time).seconds
        if duration_seconds > 600:  # 10 minutes
            logger.info(f"Conversation {self.call_sid} reached max duration (10 min)")
            return True
        
        return False
    
    def get_summary(self) -> str:
        """
        Get a formatted summary of the conversation for WhatsApp.
        
        Returns:
            Formatted conversation summary
        """
        if not self.turns:
            return "No conversation history."
        
        summary_lines = [f"📞 AgroWise Conversation Summary ({self.start_time.strftime('%Y-%m-%d %H:%M')})\n"]
        
        for i, turn in enumerate(self.turns, 1):
            summary_lines.append(f"\n🌾 Question {i}:")
            summary_lines.append(turn.question)
            summary_lines.append(f"\n💡 Answer {i}:")
            summary_lines.append(turn.answer)
        
        return "\n".join(summary_lines)


# Global conversation store
# In production, use Redis or database for multi-server deployments
conversations: Dict[str, ConversationSession] = {}


def get_session(call_sid: str) -> Optional[ConversationSession]:
    """Get conversation session by CallSid."""
    return conversations.get(call_sid)


def create_session(call_sid: str, language: str, caller_number: str = "") -> ConversationSession:
    """Create a new conversation session."""
    session = ConversationSession(
        call_sid=call_sid,
        language=language,
        caller_number=caller_number
    )
    conversations[call_sid] = session
    logger.info(f"Created new conversation session for {call_sid} in language '{language}'")
    return session


def end_session(call_sid: str) -> Optional[str]:
    """
    End a conversation session and return summary.
    
    Returns:
        Conversation summary if session existed, None otherwise
    """
    session = conversations.pop(call_sid, None)
    if session:
        logger.info(f"Ended conversation session {call_sid} with {session.get_turn_count()} turns")
        return session.get_summary()
    return None
