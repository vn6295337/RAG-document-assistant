import re
import html
import logging
from typing import Iterator, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class TextCleaner:
    """
    A memory-efficient text cleaner using regex and BeautifulSoup.
    Designed for production-grade RAG pipelines on hardware with strict RAM limits.
    """

    def __init__(self):
        # Pre-compile regex patterns for performance and memory efficiency
        
        # 1. Normalize unicode spaces (e.g., non-breaking spaces) to regular space
        self.re_space = re.compile(r'[ \t\f\v]+')
        
        # 2. Remove non-printable characters (control characters, etc)
        # Keeps basic whitespace (\n, \t, \r) but strips invisible control chars
        self.re_non_printable = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')
        
        # 3. Clean up excessive empty lines (3 or more -> 2)
        self.re_newlines = re.compile(r'\n{3,}')
        
        # 4. URL removal pattern (optional)
        self.re_urls = re.compile(r'https?://\S+|www\.\S+')
        
        # 5. Markdown specific patterns
        self.re_md_code_fences = re.compile(r"```.*?```", flags=re.DOTALL)
        self.re_md_images = re.compile(r"!\[([^\]]*)\]\([^\)]*\)")
        self.re_md_links = re.compile(r"\[([^\]]+)\]\([^\)]*\)")
        self.re_md_front_matter = re.compile(r"^---.*?---\s*", flags=re.DOTALL)

    def clean_html(self, raw_html: str) -> str:
        """
        Strips HTML tags using BeautifulSoup with the built-in html.parser.
        Low memory footprint, no external C-dependencies.
        """
        if not raw_html:
            return ""
        
        try:
            # Use html.parser which is built into standard library (lowest memory footprint)
            soup = BeautifulSoup(raw_html, "html.parser")
            
            # Remove script and style elements
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()
                
            # Get text, joining with space to prevent glued words
            text = soup.get_text(separator=' ')
            return text
        except Exception as e:
            logger.error(f"Error cleaning HTML: {e}")
            return raw_html # Fallback to raw if parser fails

    def clean_text(self, text: str, remove_urls: bool = False, is_markdown: bool = True) -> str:
        """
        Applies a fast regex pipeline to normalize text.
        """
        if not text:
            return ""
            
        # 1. Unescape HTML entities (e.g., &amp; -> &)
        text = html.unescape(text)
        
        # 2. If it looks like HTML, clean tags first
        if "<" in text and ">" in text:
            text = self.clean_html(text)
        
        # 3. Markdown specific cleaning
        if is_markdown:
            text = self.re_md_code_fences.sub(" ", text)
            text = self.re_md_front_matter.sub(" ", text)
            text = self.re_md_images.sub(r"\1", text)
            text = self.re_md_links.sub(r"\1", text)

        # 4. Optional URL removal
        if remove_urls:
            text = self.re_urls.sub('', text)

        # 5. Remove non-printable control characters
        text = self.re_non_printable.sub('', text)
        
        # 6. Normalize whitespace (replace multiple spaces/tabs with a single space)
        # Process line-by-line to preserve structural newlines
        lines = text.split('\n')
        cleaned_lines = [self.re_space.sub(' ', line).strip() for line in lines]
        
        # 7. Rejoin lines, then remove excessive blank lines
        text = '\n'.join(cleaned_lines)
        text = self.re_newlines.sub('\n\n', text)
        
        return text.strip()

    def clean_stream(self, text_stream: Iterator[str], **kwargs) -> Iterator[str]:
        """
        A memory-safe generator that cleans a stream of text chunks.
        Ideal for 0.5GB RAM constraints.
        """
        for chunk in text_stream:
            yield self.clean_text(chunk, **kwargs)

# Global singleton instance
cleaner = TextCleaner()

def get_cleaner() -> TextCleaner:
    return cleaner
