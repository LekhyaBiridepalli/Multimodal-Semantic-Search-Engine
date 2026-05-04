"""
LLM Summarizer Module for TKAG-RAG
Uses Google Gemini API to generate high-quality, contextual summaries
from semantically-ranked content. Falls back to extractive methods on failure.
"""

import time
import re
from typing import List, Dict, Any, Optional


class LLMSummarizer:
    """
    LLM-powered summarizer using Google Gemini API.
    Generates intelligent, contextual summaries from retrieved content.
    Falls back gracefully to extractive methods if the API is unavailable.
    """
    
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.client = None
        self.model_name = "gemini-2.5-flash"
        self._initialized = False
        
        if api_key and api_key != "your-gemini-api-key-here":
            try:
                from google import genai
                self.client = genai.Client(api_key=api_key)
                self._initialized = True
                self._log("[OK] LLM Summarizer initialized (Gemini 2.5 Flash)")
            except ImportError:
                self._log("[WARN] google-genai package not installed. LLM summaries disabled.")
                self._log("[TIP] Install with: pip install google-genai")
            except Exception as e:
                self._log(f"[WARN] LLM Summarizer init error: {e}")
        else:
            self._log("[WARN] No Gemini API key provided. LLM summaries disabled (using extractive fallback).")
    
    @staticmethod
    def _log(message: str):
        """Safe print that handles encoding issues on Windows consoles"""
        try:
            print(f"   {message}")
        except UnicodeEncodeError:
            # Fallback: strip non-ASCII characters for Windows cp1252 consoles
            safe_msg = message.encode('ascii', errors='replace').decode('ascii')
            print(f"   {safe_msg}")
    
    @property
    def is_available(self) -> bool:
        """Check if the LLM is ready to use"""
        return self._initialized and self.client is not None
    
    def _call_gemini(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """
        Call Gemini API with retry logic and exponential backoff.
        Returns the generated text, or None on failure.
        """
        if not self.is_available:
            return None
        
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                
                # Extract text from response
                if response and response.text:
                    return response.text.strip()
                
                # Check if response was blocked
                if response and hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                        self._log(f"[WARN] Gemini response blocked: {candidate.finish_reason}")
                
                return None
                    
            except Exception as e:
                error_str = str(e)
                
                # Rate limit handling (429)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    wait_time = (2 ** attempt) + 1  # 2s, 5s, 9s
                    self._log(f"[WAIT] Gemini rate limited (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                # Other errors - don't retry
                self._log(f"[WARN] Gemini API error: {error_str[:200]}")
                return None
        
        self._log("[WARN] Gemini API: Max retries exceeded. Falling back to extractive summary.")
        return None
    
    def generate_complete_summary(
        self, 
        topic: str, 
        videos: List[Dict], 
        books: List[Dict], 
        papers: List[Dict],
        is_title: bool = False,
        exact_match: bool = True
    ) -> Optional[str]:
        """
        Generate a comprehensive knowledge summary using the LLM.
        Returns None on failure (caller should use fallback).
        """
        
        # Build content sections for the prompt
        video_content = self._format_sources(videos, 'video')
        book_content = self._format_sources(books, 'book')
        paper_content = self._format_sources(papers, 'paper')
        
        warning_text = ""
        if is_title and not exact_match:
            warning_text = "\nIMPORTANT: The exact paper title was NOT found. Mention this clearly at the start with a warning that results are for similar papers instead."
        
        prompt = f"""You are a knowledge synthesis expert. Generate a comprehensive, well-structured summary about "{topic}" based on the following semantically-ranked sources.

CRITICAL INSTRUCTIONS:
- Write in clear, professional academic language
- Synthesize insights across sources - do NOT just list or repeat source descriptions verbatim
- Extract the UNIQUE contribution or key takeaway from each source
- For video sources: Focus on what specific knowledge, technique, or skill a learner would gain - NOT what the video "covers" or "discusses". Write about the actual content insights, not meta-descriptions of the video.
- For book sources: Highlight the core methodology, unique perspective, or practical value the book offers
- For research papers: Focus on the key findings, methods, and contributions to the field
- In the Synthesized Understanding section: Identify cross-cutting THEMES and PATTERNS across all sources. What consensus emerges? What are the most important takeaways? This should read like an original analytical paragraph, NOT a copy-paste of earlier content.
- Be specific and informative - avoid filler phrases like "comprehensive coverage" or "in-depth analysis"
- Use markdown formatting{warning_text}

OUTPUT FORMAT (follow this EXACTLY):
## Complete Knowledge Summary: {topic}

Based on comprehensive analysis of {len(videos)} videos, {len(books)} books, and {len(papers)} research papers.

### Key Research Insights

* **(Paper Title)**: (Substantive insight describing its actual findings or contributions)
* **(Paper Title)**: (Substantive insight describing its actual findings or contributions)
* **(Paper Title)**: (Substantive insight describing its actual findings or contributions)

### Key Book Insights

* **(Book Title)**: (Substantive insight describing its practical value or unique perspective)
* **(Book Title)**: (Substantive insight describing its practical value or unique perspective)
* **(Book Title)**: (Substantive insight describing its practical value or unique perspective)

### Key Video Insights

* **(Video Title)**: (Substantive insight describing the actual knowledge or techniques taught - NOT just that the video "covers" or "introduces" a topic)
* **(Video Title)**: (Substantive insight describing the actual knowledge or techniques taught - NOT just that the video "covers" or "introduces" a topic)
* **(Video Title)**: (Substantive insight describing the actual knowledge or techniques taught - NOT just that the video "covers" or "introduces" a topic)

### Synthesized Understanding
(Write a 4-6 sentence analytical paragraph that connects themes across ALL source types. What consensus emerges from the research, books, and videos together? What are the most important patterns? What should a learner take away from this body of knowledge?)

===== SOURCE CONTENT =====

RESEARCH PAPER SOURCES:
{paper_content}

BOOK SOURCES:
{book_content}

VIDEO SOURCES:
{video_content}
"""
        
        result = self._call_gemini(prompt)
        if result:
            self._log("[OK] LLM generated complete summary")
        return result
    
    def generate_executive_summary(
        self,
        topic: str,
        videos: List[Dict],
        books: List[Dict],
        papers: List[Dict]
    ) -> Optional[str]:
        """
        Generate a concise executive summary using the LLM.
        Returns None on failure (caller should use fallback).
        """
        
        # Build compact source descriptions
        top_video = videos[0] if videos else None
        top_book = books[0] if books else None
        top_paper = papers[0] if papers else None
        
        sources_text = ""
        if top_paper:
            content = top_paper.get('abstract', top_paper.get('summary', ''))[:500]
            sources_text += f"\nTOP PAPER: \"{top_paper['title']}\" (URL: {top_paper.get('url', '#')})\nContent: {content}\n"
        if top_book:
            content = top_book.get('description', top_book.get('summary', ''))[:500]
            authors = ', '.join(top_book.get('authors', ['Unknown'])[:2])
            sources_text += f"\nTOP BOOK: \"{top_book['title']}\" by {authors} (URL: {top_book.get('url', '#')})\nContent: {content}\n"
        if top_video:
            content = top_video.get('transcript', top_video.get('description', ''))[:500]
            sources_text += f"\nTOP VIDEO: \"{top_video['title']}\" (URL: {top_video.get('url', '#')})\nContent: {content}\n"
        
        prompt = f"""Write a concise executive summary about "{topic}" based on the top sources below.

INSTRUCTIONS:
- Keep it brief but insightful (under 200 words total for the summaries)
- Each source summary should be 1-2 sentences of genuine insight about what the source TEACHES or CONTRIBUTES - not just what it "covers"
- Use markdown formatting

OUTPUT FORMAT (follow EXACTLY):
## Executive Summary: {topic}

**Top Research Paper:** [{top_paper['title'] if top_paper else 'N/A'}]({top_paper.get('url', '#') if top_paper else '#'})
*(1-2 sentence insight about the paper's key findings)*

**Top Book:** [{top_book['title'] if top_book else 'N/A'}]({top_book.get('url', '#') if top_book else '#'}) by {', '.join(top_book.get('authors', ['Unknown'])[:2]) if top_book else 'Unknown'}
*(1-2 sentence insight about the book's practical value)*

**Top Video Resource:** [{top_video['title'] if top_video else 'N/A'}]({top_video.get('url', '#') if top_video else '#'})
*(1-2 sentence insight about what the video teaches)*

===== SOURCE CONTENT =====
{sources_text}
"""
        
        result = self._call_gemini(prompt)
        if result:
            self._log("[OK] LLM generated executive summary")
        return result
    
    def generate_source_summaries(
        self,
        items: List[Dict],
        source_type: str,
        topic: str
    ) -> Optional[List[str]]:
        """
        Generate individual summaries for a list of sources (videos/books/papers).
        Returns a list of summary strings, or None on failure.
        """
        if not items:
            return []
        
        # Build items text
        items_text = ""
        for i, item in enumerate(items):
            title = item.get('title', 'Unknown')
            if source_type == 'video':
                content = item.get('transcript', item.get('description', ''))[:400]
            elif source_type == 'book':
                content = item.get('description', item.get('summary', ''))[:400]
            else:  # paper
                content = item.get('abstract', item.get('summary', ''))[:400]
            
            items_text += f"\n[{i+1}] Title: {title}\nContent: {content}\n"
        
        type_instruction = ""
        if source_type == 'video':
            type_instruction = "For each video, describe the specific knowledge or technique taught - NOT just that it 'covers' or 'introduces' a topic."
        elif source_type == 'book':
            type_instruction = "For each book, describe its unique perspective, methodology, or practical value."
        else:
            type_instruction = "For each paper, describe its key findings or scientific contribution."
        
        prompt = f"""Generate a brief, insightful summary for each of the following {source_type}s related to "{topic}".

INSTRUCTIONS:
- Each summary should be exactly 1-2 sentences (max 150 characters)
- {type_instruction}
- Do NOT just rephrase the title - provide actual content insight
- Do NOT use generic phrases like "comprehensive coverage", "in-depth analysis", or "thorough exploration"

OUTPUT FORMAT:
Return ONLY the summaries, one per line, numbered to match the input. Example:
1. [Actual insightful summary of item 1]
2. [Actual insightful summary of item 2]

===== SOURCES =====
{items_text}
"""
        
        result = self._call_gemini(prompt)
        if not result:
            return None
        
        # Parse numbered summaries from response
        summaries = []
        lines = result.strip().split('\n')
        for line in lines:
            # Remove numbering (e.g., "1. ", "1) ", "- ")
            cleaned = re.sub(r'^\s*\d+[\.\)]\s*', '', line).strip()
            cleaned = re.sub(r'^\s*[-\u2022]\s*', '', cleaned).strip()
            if cleaned and len(cleaned) > 10:
                summaries.append(cleaned)
        
        # Ensure we have the right number of summaries
        if len(summaries) >= len(items):
            self._log(f"[OK] LLM generated {len(items)} {source_type} summaries")
            return summaries[:len(items)]
        
        # If we got fewer than expected, signal partial failure
        self._log(f"[WARN] LLM returned {len(summaries)}/{len(items)} {source_type} summaries")
        return None
    
    def _format_sources(self, items: List[Dict], source_type: str) -> str:
        """Format a list of source items into a text block for the prompt"""
        if not items:
            return "(No sources available)"
        
        parts = []
        for i, item in enumerate(items[:5]):  # Max 5 per category
            title = item.get('title', 'Unknown')
            score = item.get('semantic_score', 'N/A')
            
            if source_type == 'video':
                content = item.get('transcript', item.get('description', ''))[:500]
                extra = f"Channel: {item.get('channel', 'Unknown')}"
            elif source_type == 'book':
                content = item.get('description', item.get('summary', ''))[:500]
                authors = ', '.join(item.get('authors', ['Unknown'])[:2])
                extra = f"Authors: {authors} | Rating: {item.get('rating', 'N/A')}"
            else:  # paper
                content = item.get('abstract', item.get('summary', ''))[:500]
                authors = ', '.join(item.get('authors', ['Unknown'])[:3])
                extra = f"Authors: {authors} | Year: {item.get('year', 'N/A')} | Venue: {item.get('venue', 'N/A')}"
            
            parts.append(f"[{i+1}] \"{title}\" (Relevance: {score})\n    {extra}\n    Content: {content}")
        
        return '\n\n'.join(parts)
