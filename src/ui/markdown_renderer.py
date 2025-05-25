#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Markdown Renderer for LostMind AI Gemini Chat Assistant

This module implements markdown rendering for the chat display,
including code highlighting, tables, lists, and other formatting.
"""

import re
import logging
from typing import List, Dict, Tuple, Optional, Match

from PyQt6.QtWidgets import QTextEdit, QFrame
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import (
    QTextCursor, QTextCharFormat, QFont, QColor, 
    QTextBlockFormat, QTextListFormat, QTextTableFormat,
    QTextOption
)

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, TextLexer
    from pygments.formatters import HtmlFormatter
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

class MarkdownTextEdit(QTextEdit):
    """
    Text editor widget with markdown rendering capabilities.
    
    Features:
    - Code block syntax highlighting
    - Headers (h1, h2, h3)
    - Bold and italic text
    - Links
    - Lists (ordered and unordered)
    - Tables
    - Line breaks
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the markdown text edit."""
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
        
        # Basic styling
        self.setStyleSheet("""QTextEdit { 
            background: transparent;
            border: none;
            padding: 4px;
        }""")
        
        # Set default font and properties directly
        font = self.font()
        font.setFamily("Arial")
        font.setPointSize(10)
        self.setFont(font)
    
    def setMarkdown(self, markdown_text: str):
        """
        Set the content and render markdown.
        
        Args:
            markdown_text (str): Markdown text to render.
        """
        try:
            # Convert markdown to HTML
            html_content = self._markdown_to_html(markdown_text)
            
            # Set HTML content
            self.setHtml(html_content)
            
            # Adjust height to content
            self.document().adjustSize()
            content_height = self.document().size().height()
            # Set a fixed height that fits the content
            self.setFixedHeight(int(content_height + 5))
            
        except Exception as e:
            self.logger.error(f"Error rendering markdown: {str(e)}")
            # Fall back to plain text
            self.setPlainText(markdown_text)
    
    def _markdown_to_html(self, text: str) -> str:
        """
        Convert markdown to HTML.
        
        Args:
            text (str): Markdown text.
        
        Returns:
            str: HTML text.
        """
        # Escape HTML special characters
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Process code blocks with syntax highlighting
        text = self._process_code_blocks(text)
        
        # Process inline code
        text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
        
        # Process headers
        text = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        
        # Process bold and italic
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        
        # Process ordered lists
        def ordered_list_replace(match: Match) -> str:
            list_items = match.group(0).strip().split('\n')
            list_html = '<ol>'
            for item in list_items:
                item_text = re.sub(r'^\d+\.\s+(.*?)$', r'\1', item)
                list_html += f'<li>{item_text}</li>'
            list_html += '</ol>'
            return list_html
        
        text = re.sub(r'(^\d+\.\s+.*?$)(\n^\d+\.\s+.*?$)*', ordered_list_replace, text, flags=re.MULTILINE)
        
        # Process unordered lists
        def unordered_list_replace(match: Match) -> str:
            list_items = match.group(0).strip().split('\n')
            list_html = '<ul>'
            for item in list_items:
                item_text = re.sub(r'^\*\s+(.*?)$', r'\1', item)
                list_html += f'<li>{item_text}</li>'
            list_html += '</ul>'
            return list_html
        
        text = re.sub(r'(^\*\s+.*?$)(\n^\*\s+.*?$)*', unordered_list_replace, text, flags=re.MULTILINE)
        
        # Process tables
        def table_replace(match: Match) -> str:
            table_text = match.group(0).strip()
            rows = table_text.split('\n')
            
            # Check if it's a table with at least header and separator rows
            if len(rows) < 2:
                return table_text
            
            # Check if the second row is a separator
            if not re.match(r'^\|[\s\-:]+\|$', rows[1]):
                return table_text
            
            table_html = '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">'
            
            # Process header row
            header_cells = rows[0].strip('|').split('|')
            table_html += '<tr>'
            for cell in header_cells:
                table_html += f'<th>{cell.strip()}</th>'
            table_html += '</tr>'
            
            # Process data rows (skip the separator row)
            for row in rows[2:]:
                if not row.strip():
                    continue
                    
                cells = row.strip('|').split('|')
                table_html += '<tr>'
                for cell in cells:
                    table_html += f'<td>{cell.strip()}</td>'
                table_html += '</tr>'
            
            table_html += '</table>'
            return table_html
        
        # Find tables (they start with | and have at least one | separator row)
        text = re.sub(r'^\|.*\|\n\|[\s\-:]+\|\n(\|.*\|\n?)*', table_replace, text, flags=re.MULTILINE)
        
        # Process links
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
        
        # Process plain URLs (not already in links)
        text = re.sub(r'(https?://[^\s<>]+)', r'<a href="\1">\1</a>', text)
        
        # Process line breaks
        text = text.replace('\n', '<br>')
        
        # Basic styling
        text = f"""
        <html>
        <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.5;
            }}
            code {{
                font-family: Consolas, Monaco, 'Courier New', monospace;
                background-color: #f5f5f5;
                padding: 2px 4px;
                border-radius: 4px;
            }}
            pre {{
                background-color: #f5f5f5;
                padding: 10px;
                border-radius: 4px;
                overflow-x: auto;
            }}
            h1, h2, h3 {{
                margin-top: 0.5em;
                margin-bottom: 0.5em;
                color: #333;
            }}
            h1 {{ font-size: 1.5em; }}
            h2 {{ font-size: 1.3em; }}
            h3 {{ font-size: 1.1em; }}
            table {{
                border-collapse: collapse;
                width: 100%;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
            }}
            a {{
                color: #0066cc;
                text-decoration: none;
            }}
            ul, ol {{
                padding-left: 2em;
            }}
        </style>
        </head>
        <body>
        {text}
        </body>
        </html>
        """
        
        return text
    
    def _process_code_blocks(self, text: str) -> str:
        """
        Process code blocks with syntax highlighting.
        
        Args:
            text (str): Markdown text.
        
        Returns:
            str: Processed text with HTML code blocks.
        """
        def code_replace(match: Match) -> str:
            language = match.group(1).strip() or 'text'
            code = match.group(2)
            
            # Use Pygments for syntax highlighting if available
            if PYGMENTS_AVAILABLE:
                try:
                    lexer = get_lexer_by_name(language, stripall=True)
                except Exception:
                    lexer = TextLexer()
                
                formatter = HtmlFormatter(style='default', noclasses=True)
                highlighted_code = highlight(code, lexer, formatter)
                return highlighted_code
            else:
                # Basic code block without syntax highlighting
                return f'<pre><code>{code}</code></pre>'
        
        # Replace code blocks with syntax highlighting
        pattern = r'```(\w*)\n(.*?)```'
        text = re.sub(pattern, code_replace, text, flags=re.DOTALL)
        
        return text
