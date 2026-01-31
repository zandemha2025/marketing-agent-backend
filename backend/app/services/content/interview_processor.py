"""
Interview Processing Service

Handles:
- Audio transcription using Whisper API
- Text interview input processing
- Content extraction and structuring
- Key insight identification
- Quote extraction with attribution
- Theme identification for content structure
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import re

from ..ai.openrouter import OpenRouterService
from ...core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Quote:
    """A notable quote extracted from an interview."""
    text: str
    speaker: str
    context: str = ""
    importance: float = 0.5  # 0-1 scale
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "speaker": self.speaker,
            "context": self.context,
            "importance": self.importance
        }


@dataclass
class Theme:
    """A theme or topic identified in the interview."""
    name: str
    description: str
    related_quotes: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "related_quotes": self.related_quotes,
            "keywords": self.keywords
        }


@dataclass
class InterviewSegment:
    """A segment of an interview (speaker turn)."""
    speaker: str
    text: str
    timestamp: Optional[float] = None  # Seconds from start
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "speaker": self.speaker,
            "text": self.text,
            "timestamp": self.timestamp
        }


@dataclass
class InterviewInsight:
    """An insight extracted from an interview."""
    category: str  # "story", "statistic", "quote", "idea", "pain_point", "solution"
    content: str
    context: str = ""  # Surrounding context
    importance: int = 5  # 1-10
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "content": self.content,
            "context": self.context,
            "importance": self.importance
        }


@dataclass
class ProcessedInterview:
    """A fully processed interview with all extracted data."""
    summary: str
    quotes: List[Quote] = field(default_factory=list)
    themes: List[Theme] = field(default_factory=list)
    key_insights: List[str] = field(default_factory=list)
    suggested_headlines: List[str] = field(default_factory=list)
    word_count: int = 0
    speakers: List[str] = field(default_factory=list)
    
    # Extended fields for internal use
    title: str = ""
    raw_text: str = ""
    segments: List[InterviewSegment] = field(default_factory=list)
    insights: List[InterviewInsight] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    duration_minutes: Optional[float] = None
    processed_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "quotes": [q.to_dict() for q in self.quotes],
            "themes": [t.to_dict() for t in self.themes],
            "key_insights": self.key_insights,
            "suggested_headlines": self.suggested_headlines,
            "word_count": self.word_count,
            "speakers": self.speakers,
            "title": self.title,
            "raw_text": self.raw_text,
            "segments": [s.to_dict() for s in self.segments],
            "insights": [i.to_dict() for i in self.insights],
            "topics": self.topics,
            "duration_minutes": self.duration_minutes,
            "processed_at": self.processed_at.isoformat()
        }


class InterviewProcessor:
    """
    Process interviews (audio or text) into structured content.
    
    Features:
    - Whisper API transcription
    - Speaker identification
    - Key insight extraction
    - Quote identification with attribution
    - Theme identification for content structure
    - Headline suggestions for articles
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.openrouter = None
        if self.settings.openrouter_api_key:
            self.openrouter = OpenRouterService(
                api_key=self.settings.openrouter_api_key,
                timeout=120.0
            )
    
    async def process_transcript(self, transcript: str, title: str = "Interview") -> ProcessedInterview:
        """
        Process raw interview transcript.
        
        Args:
            transcript: The raw interview transcript text
            title: Optional title for the interview
            
        Returns:
            ProcessedInterview with all extracted data
        """
        return await self.process_text_interview(transcript, title)
    
    async def extract_quotes(self, transcript: str) -> List[Quote]:
        """
        Extract notable quotes from interview.
        
        Args:
            transcript: The interview transcript
            
        Returns:
            List of Quote objects with speaker attribution
        """
        segments = self._parse_speaker_turns(transcript)
        
        if not self.openrouter:
            return self._basic_quote_extraction(transcript, segments)
        
        prompt = f"""
        Extract the 5-8 most notable and quotable statements from this interview.
        
        For each quote, identify:
        - The exact quote text
        - Who said it (speaker name)
        - Brief context (what was being discussed)
        - Importance score (0.0 to 1.0)
        
        Look for statements that are:
        - Memorable and impactful
        - Express strong opinions or unique insights
        - Would work well as pull quotes in articles
        - Capture key moments in the conversation
        
        INTERVIEW:
        {transcript[:4000]}
        
        Return as JSON array:
        [
            {{
                "text": "The exact quote",
                "speaker": "Speaker Name",
                "context": "Brief context",
                "importance": 0.85
            }}
        ]
        """
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You are an expert at identifying impactful quotes from interviews.",
                temperature=0.3,
                json_mode=True
            )
            
            data = json.loads(response)
            if isinstance(data, list):
                return [
                    Quote(
                        text=item.get("text", ""),
                        speaker=item.get("speaker", "Unknown"),
                        context=item.get("context", ""),
                        importance=float(item.get("importance", 0.5))
                    )
                    for item in data
                ]
            return []
            
        except Exception as e:
            logger.error(f"Quote extraction failed: {e}")
            return self._basic_quote_extraction(transcript, segments)
    
    async def identify_themes(self, transcript: str) -> List[Theme]:
        """
        Identify main themes and topics from interview.
        
        Args:
            transcript: The interview transcript
            
        Returns:
            List of Theme objects with related quotes and keywords
        """
        if not self.openrouter:
            return self._basic_theme_extraction(transcript)
        
        prompt = f"""
        Identify the 4-6 main themes discussed in this interview.
        
        For each theme, provide:
        - A concise name (2-4 words)
        - A brief description (1-2 sentences)
        - 2-3 related quotes from the interview
        - 3-5 relevant keywords
        
        INTERVIEW:
        {transcript[:4000]}
        
        Return as JSON array:
        [
            {{
                "name": "Theme Name",
                "description": "Brief description of the theme",
                "related_quotes": ["Quote 1", "Quote 2"],
                "keywords": ["keyword1", "keyword2", "keyword3"]
            }}
        ]
        """
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You are an expert at identifying themes and patterns in conversations.",
                temperature=0.3,
                json_mode=True
            )
            
            data = json.loads(response)
            if isinstance(data, list):
                return [
                    Theme(
                        name=item.get("name", ""),
                        description=item.get("description", ""),
                        related_quotes=item.get("related_quotes", []),
                        keywords=item.get("keywords", [])
                    )
                    for item in data
                ]
            return []
            
        except Exception as e:
            logger.error(f"Theme identification failed: {e}")
            return self._basic_theme_extraction(transcript)
    
    async def generate_summary(self, transcript: str) -> str:
        """
        Generate executive summary of interview.
        
        Args:
            transcript: The interview transcript
            
        Returns:
            Executive summary string
        """
        segments = self._parse_speaker_turns(transcript)
        return await self._generate_summary(transcript, segments)
    
    async def process_text_interview(
        self,
        text: str,
        title: str,
        speaker_names: Optional[List[str]] = None
    ) -> ProcessedInterview:
        """
        Process a text-based interview.
        
        Args:
            text: The interview text
            title: Interview title/subject
            speaker_names: Optional list of speaker names for identification
            
        Returns:
            ProcessedInterview with structured content
        """
        # Split into segments (speaker turns)
        segments = self._parse_speaker_turns(text, speaker_names)
        
        # Extract unique speakers
        speakers = list(set(s.speaker for s in segments if s.speaker != "Unknown"))
        
        # Calculate word count
        word_count = len(text.split())
        
        # Estimate duration (average 150 words per minute)
        duration_minutes = word_count / 150
        
        # Extract quotes with attribution
        quotes = await self.extract_quotes(text)
        
        # Identify themes
        themes = await self.identify_themes(text)
        
        # Extract insights using AI
        insights = await self._extract_insights(text, segments)
        
        # Extract key quotes (simple strings for backward compatibility)
        key_quotes = [q.text for q in quotes[:5]]
        
        # Extract topics
        topics = await self._extract_topics(text)
        
        # Generate summary
        summary = await self._generate_summary(text, segments)
        
        # Generate key insights as strings
        key_insights = [i.content for i in insights if i.importance >= 7][:5]
        
        # Generate suggested headlines
        suggested_headlines = await self._generate_headlines(text, summary, themes)
        
        return ProcessedInterview(
            summary=summary,
            quotes=quotes,
            themes=themes,
            key_insights=key_insights,
            suggested_headlines=suggested_headlines,
            word_count=word_count,
            speakers=speakers,
            title=title,
            raw_text=text,
            segments=segments,
            insights=insights,
            topics=topics,
            duration_minutes=duration_minutes
        )
    
    async def transcribe_audio(
        self,
        audio_path: str,
        title: str = "Interview",
        language: str = "en"
    ) -> ProcessedInterview:
        """
        Transcribe audio file using OpenAI Whisper API.
        
        Args:
            audio_path: Path to audio file (mp3, mp4, mpeg, mpga, m4a, wav, webm)
            title: Interview title
            language: Language code (default: en)
            
        Returns:
            ProcessedInterview with transcription and extracted content
        """
        import openai
        from pathlib import Path
        import os
        
        # Get API key from settings or environment
        api_key = self.settings.openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise NotImplementedError(
                "Audio transcription requires OPENAI_API_KEY environment variable. "
                "Get your API key from https://platform.openai.com/api-keys"
            )
        
        # Validate audio file exists
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Validate file extension
        valid_extensions = {'.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm'}
        if audio_file.suffix.lower() not in valid_extensions:
            raise ValueError(
                f"Unsupported audio format: {audio_file.suffix}. "
                f"Supported formats: {', '.join(valid_extensions)}"
            )
        
        # Create OpenAI client and transcribe
        client = openai.OpenAI(api_key=api_key)
        
        logger.info(f"Transcribing audio file: {audio_path}")
        
        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language=language,
                response_format="text"
            )
        
        logger.info(f"Transcription complete. Length: {len(transcript)} characters")
        
        # Process the transcription to extract structured content
        return await self.process_text_interview(transcript, title)
    
    def _parse_speaker_turns(
        self,
        text: str,
        speaker_names: Optional[List[str]] = None
    ) -> List[InterviewSegment]:
        """Parse text into speaker turns."""
        segments = []
        
        # Try to detect speaker patterns
        # Common patterns: "Name:", "Name -", "[Name]", "Name:", etc.
        patterns = [
            r'^([A-Z][a-zA-Z\s]+):\s*(.+)$',  # Name: text
            r'^([A-Z][a-zA-Z\s]+)\s*-\s*(.+)$',  # Name - text
            r'^\[([A-Z][a-zA-Z\s]+)\]\s*(.+)$',  # [Name] text
        ]
        
        lines = text.strip().split('\n')
        current_speaker = "Unknown"
        current_text = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            speaker_found = False
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    # Save previous segment if exists
                    if current_text:
                        segments.append(InterviewSegment(
                            speaker=current_speaker,
                            text=current_text.strip()
                        ))
                    
                    current_speaker = match.group(1).strip()
                    current_text = match.group(2).strip()
                    speaker_found = True
                    break
            
            if not speaker_found:
                current_text += " " + line
        
        # Add final segment
        if current_text:
            segments.append(InterviewSegment(
                speaker=current_speaker,
                text=current_text.strip()
            ))
        
        # If no segments found, treat entire text as one segment
        if not segments:
            segments = [InterviewSegment(
                speaker=speaker_names[0] if speaker_names else "Speaker",
                text=text.strip()
            )]
        
        return segments
    
    async def _extract_insights(
        self,
        text: str,
        segments: List[InterviewSegment]
    ) -> List[InterviewInsight]:
        """Extract key insights from the interview."""
        if not self.openrouter:
            return self._basic_insight_extraction(text)
        
        prompt = f"""
        Analyze this interview and extract key insights.
        
        INTERVIEW TEXT:
        {text[:4000]}  # Limit for token constraints
        
        Extract insights in these categories:
        - story: Personal anecdotes or experiences
        - statistic: Numbers, data, or research findings
        - quote: Memorable statements worth quoting
        - idea: New concepts or innovative thinking
        - pain_point: Problems or challenges mentioned
        - solution: Approaches to solving problems
        
        Return as JSON array:
        [
            {{
                "category": "story|statistic|quote|idea|pain_point|solution",
                "content": "The insight text",
                "context": "Brief surrounding context",
                "importance": 8
            }}
        ]
        
        Include 5-10 most important insights.
        """
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You are an expert interviewer who identifies the most valuable insights from conversations.",
                temperature=0.3,
                json_mode=True
            )
            
            data = json.loads(response)
            if isinstance(data, list):
                return [
                    InterviewInsight(
                        category=item.get("category", "idea"),
                        content=item.get("content", ""),
                        context=item.get("context", ""),
                        importance=item.get("importance", 5)
                    )
                    for item in data
                ]
            return []
            
        except Exception as e:
            logger.error(f"Insight extraction failed: {e}")
            return self._basic_insight_extraction(text)
    
    def _basic_insight_extraction(self, text: str) -> List[InterviewInsight]:
        """Basic insight extraction without AI."""
        insights = []
        
        # Look for sentences with numbers (potential statistics)
        stat_pattern = r'[^.]*\d+[^.]*\.'
        stats = re.findall(stat_pattern, text)
        for stat in stats[:3]:
            insights.append(InterviewInsight(
                category="statistic",
                content=stat.strip(),
                importance=7
            ))
        
        # Look for quotes (text in quotes)
        quote_pattern = r'"([^"]+)"'
        quotes = re.findall(quote_pattern, text)
        for quote in quotes[:3]:
            insights.append(InterviewInsight(
                category="quote",
                content=f'"{quote}"',
                importance=8
            ))
        
        return insights
    
    def _basic_quote_extraction(
        self,
        text: str,
        segments: List[InterviewSegment]
    ) -> List[Quote]:
        """Basic quote extraction without AI."""
        quotes = []
        
        # Extract segments that look like good quotes
        for segment in segments:
            if 50 < len(segment.text) < 300:
                quotes.append(Quote(
                    text=segment.text,
                    speaker=segment.speaker,
                    context="",
                    importance=0.5
                ))
        
        # Also look for text in quotation marks
        quote_pattern = r'"([^"]+)"'
        found_quotes = re.findall(quote_pattern, text)
        for q in found_quotes[:3]:
            if len(q) > 20:
                quotes.append(Quote(
                    text=q,
                    speaker="Unknown",
                    context="",
                    importance=0.6
                ))
        
        return quotes[:8]
    
    def _basic_theme_extraction(self, text: str) -> List[Theme]:
        """Basic theme extraction without AI."""
        themes = []
        
        # Look for frequently mentioned capitalized words as potential themes
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        word_freq = {}
        for word in words:
            if len(word) > 4:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Create themes from most frequent words
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        for word, count in sorted_words[:4]:
            if count >= 2:
                themes.append(Theme(
                    name=word,
                    description=f"Discussion around {word.lower()}",
                    related_quotes=[],
                    keywords=[word.lower()]
                ))
        
        return themes
    
    async def _extract_topics(self, text: str) -> List[str]:
        """Extract main topics discussed."""
        if not self.openrouter:
            # Basic topic extraction
            words = re.findall(r'\b[A-Z][a-z]+\b', text)
            word_freq = {}
            for word in words:
                if len(word) > 4:
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Return most frequent capitalized words
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            return [word for word, count in sorted_words[:5]]
        
        prompt = f"""
        Identify the 5-7 main topics discussed in this interview.
        
        INTERVIEW:
        {text[:3000]}
        
        Return as JSON array of topic names (2-3 words each):
        ["Topic 1", "Topic 2", "Topic 3"]
        """
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You identify the main themes and topics in conversations.",
                temperature=0.3,
                json_mode=True
            )
            
            topics = json.loads(response)
            if isinstance(topics, list):
                return topics
            return topics.get("topics", [])
            
        except Exception as e:
            logger.error(f"Topic extraction failed: {e}")
            return []
    
    async def _generate_summary(
        self,
        text: str,
        segments: List[InterviewSegment]
    ) -> str:
        """Generate a brief summary of the interview."""
        if not self.openrouter:
            # Basic summary: first 200 characters
            return text[:200] + "..." if len(text) > 200 else text
        
        prompt = f"""
        Summarize this interview in 2-3 sentences.
        
        INTERVIEW:
        {text[:3000]}
        
        Provide a concise summary that captures:
        - Who was interviewed (if mentioned)
        - The main subject
        - Key takeaways
        
        Return as a single paragraph.
        """
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You write concise, informative summaries.",
                temperature=0.3
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return text[:200] + "..." if len(text) > 200 else text
    
    async def _generate_headlines(
        self,
        text: str,
        summary: str,
        themes: List[Theme]
    ) -> List[str]:
        """Generate suggested headlines for articles based on the interview."""
        if not self.openrouter:
            # Basic headline generation
            theme_names = [t.name for t in themes[:3]]
            return [
                f"Insights on {theme_names[0]}" if theme_names else "Key Interview Insights",
                "Expert Perspectives: What We Learned",
                "Behind the Conversation: Key Takeaways"
            ]
        
        theme_context = ", ".join([t.name for t in themes[:5]]) if themes else "various topics"
        
        prompt = f"""
        Generate 5 compelling article headlines based on this interview.
        
        SUMMARY:
        {summary}
        
        MAIN THEMES: {theme_context}
        
        Create headlines that:
        - Are attention-grabbing and specific
        - Are under 70 characters each
        - Would work for blog posts or articles
        - Highlight the most interesting aspects
        - Use different headline styles (question, statement, how-to, etc.)
        
        Return as JSON array:
        ["Headline 1", "Headline 2", "Headline 3", "Headline 4", "Headline 5"]
        """
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You are an expert headline writer for digital content.",
                temperature=0.7,
                json_mode=True
            )
            
            headlines = json.loads(response)
            if isinstance(headlines, list):
                return headlines
            return headlines.get("headlines", [])
            
        except Exception as e:
            logger.error(f"Headline generation failed: {e}")
            return [
                "Key Insights from Our Latest Interview",
                "Expert Perspectives: What We Learned",
                "Behind the Conversation: Key Takeaways"
            ]


# Convenience function
async def process_interview(
    text: str,
    title: str,
    speaker_names: Optional[List[str]] = None
) -> ProcessedInterview:
    """Process an interview."""
    processor = InterviewProcessor()
    return await processor.process_text_interview(text, title, speaker_names)
