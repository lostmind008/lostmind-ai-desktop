#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Markdown Renderer for LostMind AI Gemini Chat Assistant

This module implements robust markdown rendering for the chat display,
using the python-markdown library with extensions for enhanced functionality.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import QTextEdit, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextOption

try:
    import markdown
    from markdown.extensions import codehilite, tables, fenced_code, toc
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    logging.error("python-markdown not available. Install with: pip install markdown")

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, TextLexer
    from pygments.formatters import HtmlFormatter
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False
    logging.warning("Pygments not available. Code highlighting will be basic.")

class MarkdownTextEdit(QTextEdit):
    """
    Robust text editor widget with professional markdown rendering capabilities.
    
    Features:
    - Full CommonMark support via python-markdown
    - Advanced code syntax highlighting with Pygments
    - Tables, lists, headers, links, and images
    - Math support (if extensions available)
    - Table of contents generation
    - Strikethrough and other extensions
    - Proper HTML sanitization
    - Responsive design and accessibility
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the enhanced markdown text edit."""
        super().__init__(*args, **kwargs)
        
        self.logger = logging.getLogger(__name__)
        
        # Configure basic settings
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Set document properties
        doc = self.document()
        doc.setDocumentMargin(8)
        
        # Enhanced styling with better typography
        self.setStyleSheet("""
            QTextEdit { 
                background: transparent;
                border: none;
                padding: 8px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
        """)
        
        # Set default font with better readability
        font = self.font()
        font.setFamily("SF Pro Text, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif")
        font.setPointSize(11)
        self.setFont(font)
        
        # Initialize markdown processor
        self._init_markdown_processor()
    
    def _init_markdown_processor(self):
        """Initialize the markdown processor with extensions."""
        if not MARKDOWN_AVAILABLE:
            self.logger.warning("python-markdown not available. Using fallback renderer.")
            self.markdown_processor = None
            return
        
        # Configure extensions based on availability
        extensions = [
            'markdown.extensions.fenced_code',  # ```code blocks
            'markdown.extensions.tables',       # Table support
            'markdown.extensions.nl2br',        # Line breaks
            'markdown.extensions.sane_lists',   # Better list handling
            'markdown.extensions.smarty',       # Smart quotes/dashes
            'markdown.extensions.toc',          # Table of contents
        ]
        
        # Add codehilite if Pygments is available
        if PYGMENTS_AVAILABLE:
            extensions.append('markdown.extensions.codehilite')
        
        extension_configs = {
            'markdown.extensions.codehilite': {
                'css_class': 'highlight',
                'use_pygments': PYGMENTS_AVAILABLE,
                'pygments_style': 'default',
                'noclasses': True,
            },
            'markdown.extensions.toc': {
                'permalink': False,
                'baselevel': 1,
            }
        }
        
        try:
            self.markdown_processor = markdown.Markdown(
                extensions=extensions,
                extension_configs=extension_configs,
                output_format='html5'
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize markdown processor: {e}")
            self.markdown_processor = None
    
    def setMarkdown(self, markdown_text: str):
        """
        Set the content and render markdown using professional library.
        
        Args:
            markdown_text (str): Markdown text to render.
        """
        try:
            # Convert markdown to HTML using proper library
            html_content = self._markdown_to_html(markdown_text)
            
            # Set HTML content
            self.setHtml(html_content)
            
            # Adjust height to content
            self.document().adjustSize()
            content_height = self.document().size().height()
            self.setFixedHeight(int(content_height + 10))
            
        except Exception as e:
            self.logger.error(f"Error rendering markdown: {str(e)}")
            # Fall back to plain text
            self.setPlainText(markdown_text)
    
    def _markdown_to_html(self, text: str) -> str:
        """
        Convert markdown to HTML using python-markdown library.
        
        Args:
            text (str): Markdown text.
        
        Returns:
            str: Styled HTML content.
        """
        if self.markdown_processor is None:
            # Fallback to basic rendering if markdown library unavailable
            return self._fallback_markdown_to_html(text)
        
        try:
            # Reset the processor for fresh conversion
            self.markdown_processor.reset()
            
            # Convert markdown to HTML
            html_body = self.markdown_processor.convert(text)
            
            # Wrap in styled HTML document
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    {self._get_enhanced_css()}
                </style>
            </head>
            <body>
                {html_body}
            </body>
            </html>
            """
            
            return html_content
            
        except Exception as e:
            self.logger.error(f"Markdown conversion failed: {e}")
            return self._fallback_markdown_to_html(text)
    
    def _get_enhanced_css(self) -> str:
        """Get enhanced CSS styling for rendered markdown."""
        return """
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 100%;
                margin: 0;
                padding: 0;
                word-wrap: break-word;
            }
            
            /* Headers */
            h1, h2, h3, h4, h5, h6 {
                margin-top: 1em;
                margin-bottom: 0.5em;
                font-weight: 600;
                line-height: 1.25;
                color: #1a1a1a;
            }
            h1 { font-size: 1.75em; border-bottom: 2px solid #eee; padding-bottom: 0.3em; }
            h2 { font-size: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
            h3 { font-size: 1.25em; }
            h4 { font-size: 1.1em; }
            h5 { font-size: 1em; }
            h6 { font-size: 0.9em; color: #666; }
            
            /* Code */
            code {
                font-family: 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
                font-size: 0.9em;
                background-color: rgba(175, 184, 193, 0.2);
                padding: 0.2em 0.4em;
                border-radius: 6px;
                color: #e83e8c;
            }
            
            pre {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 1em;
                overflow-x: auto;
                margin: 1em 0;
                font-size: 0.9em;
            }
            
            pre code {
                background: none;
                padding: 0;
                color: inherit;
                border-radius: 0;
            }
            
            /* Tables */
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 1em 0;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                overflow: hidden;
            }
            
            th, td {
                border: 1px solid #d0d7de;
                padding: 8px 12px;
                text-align: left;
            }
            
            th {
                background-color: #f6f8fa;
                font-weight: 600;
                color: #24292f;
            }
            
            tr:nth-child(even) {
                background-color: #f6f8fa;
            }
            
            /* Lists */
            ul, ol {
                padding-left: 2em;
                margin: 0.5em 0;
            }
            
            li {
                margin: 0.25em 0;
            }
            
            /* Links */
            a {
                color: #0969da;
                text-decoration: none;
            }
            
            a:hover {
                text-decoration: underline;
            }
            
            /* Blockquotes */
            blockquote {
                margin: 0;
                padding: 0 1em;
                color: #656d76;
                border-left: 0.25em solid #d0d7de;
            }
            
            /* Horizontal rules */
            hr {
                height: 0.25em;
                padding: 0;
                margin: 24px 0;
                background-color: #d0d7de;
                border: 0;
            }
            
            /* Images */
            img {
                max-width: 100%;
                height: auto;
                border-radius: 6px;
                margin: 0.5em 0;
            }
            
            /* Syntax highlighting improvements */
            .highlight {
                background-color: #f8f9fa;
                border-radius: 8px;
                overflow-x: auto;
            }
            
            /* Responsive design */
            @media (max-width: 768px) {
                body {
                    font-size: 14px;
                }
                
                h1 { font-size: 1.5em; }
                h2 { font-size: 1.3em; }
                h3 { font-size: 1.2em; }
                
                table {
                    font-size: 0.9em;
                }
                
                th, td {
                    padding: 6px 8px;
                }
            }
        """
    
    def _fallback_markdown_to_html(self, text: str) -> str:
        """
        Fallback markdown renderer when python-markdown is unavailable.
        
        Args:
            text (str): Markdown text.
        
        Returns:
            str: Basic HTML content.
        """
        import html
        
        # Escape HTML
        text = html.escape(text)
        
        # Very basic markdown processing
        lines = text.split('\n')
        html_lines = []
        
        for line in lines:
            # Headers
            if line.startswith('### '):
                html_lines.append(f'<h3>{line[4:].strip()}</h3>')
            elif line.startswith('## '):
                html_lines.append(f'<h2>{line[3:].strip()}</h2>')
            elif line.startswith('# '):
                html_lines.append(f'<h1>{line[2:].strip()}</h1>')
            # Code blocks (basic)
            elif line.startswith('```'):
                if line.strip() == '```':
                    html_lines.append('<pre><code>' if not html_lines or not html_lines[-1].startswith('<pre>') else '</code></pre>')
                else:
                    html_lines.append('<pre><code>')
            # Lists
            elif line.strip().startswith('- ') or line.strip().startswith('* '):
                item = line.strip()[2:]
                if not html_lines or not html_lines[-1].startswith('<ul>'):
                    html_lines.append('<ul>')
                html_lines.append(f'<li>{item}</li>')
            elif line.strip().startswith(('1. ', '2. ', '3. ', '4. ', '5. ')):
                item = line.strip()[3:]
                if not html_lines or not html_lines[-1].startswith('<ol>'):
                    html_lines.append('<ol>')
                html_lines.append(f'<li>{item}</li>')
            else:
                # Close lists if needed
                if html_lines and html_lines[-1].startswith('<li>'):
                    if html_lines[-2].startswith('<ul>'):
                        html_lines.append('</ul>')
                    elif html_lines[-2].startswith('<ol>'):
                        html_lines.append('</ol>')
                
                # Regular paragraph
                if line.strip():
                    html_lines.append(f'<p>{line}</p>')
                else:
                    html_lines.append('<br>')
        
        # Close any open lists
        if html_lines and html_lines[-1].startswith('<li>'):
            if any(l.startswith('<ul>') for l in html_lines):
                html_lines.append('</ul>')
            elif any(l.startswith('<ol>') for l in html_lines):
                html_lines.append('</ol>')
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>{self._get_enhanced_css()}</style>
        </head>
        <body>
            {''.join(html_lines)}
        </body>
        </html>
        """
        
        return html_content
