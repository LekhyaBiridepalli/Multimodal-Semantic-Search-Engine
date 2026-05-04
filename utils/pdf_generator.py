"""
PDF Generator for TKAG-RAG Web Application
"""

import os
from datetime import datetime
from typing import Dict, Any, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

class PDFGenerator:
    """Generate PDF reports from knowledge data"""
    
    @staticmethod
    def generate_knowledge_pdf(knowledge: Dict[str, Any], output_path: str):
        """Generate a beautiful PDF from knowledge data"""
        
        # Create the document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
            title=f"TKAG-RAG Knowledge Report: {knowledge.get('topic', 'Unknown')}",
            author="TKAG-RAG System"
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=30,
            alignment=TA_CENTER,
            leading=32,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontSize=18,
            textColor=colors.HexColor('#764ba2'),
            spaceBefore=20,
            spaceAfter=10,
            alignment=TA_LEFT,
            leading=22,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='SubHeader',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#4a5568'),
            spaceBefore=10,
            spaceAfter=5,
            alignment=TA_LEFT,
            leading=18,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='Content',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            leading=16,
            fontName='Helvetica'
        ))
        
        styles.add(ParagraphStyle(
            name='Caption',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#718096'),
            alignment=TA_CENTER,
            leading=12,
            fontName='Helvetica-Oblique'
        ))
        
        styles.add(ParagraphStyle(
            name='Stats',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#667eea'),
            alignment=TA_CENTER,
            leading=14,
            fontName='Helvetica-Bold'
        ))
        
        # Build story
        story = []
        
        # Title
        title = f"📚 Knowledge Report: {knowledge.get('topic', 'Unknown')}"
        story.append(Paragraph(title, styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Metadata
        meta_data = f"""
        <para align="center">
            <font color="#718096" size="10">
                Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br/>
                Sources: {knowledge.get('metadata', {}).get('sources', {}).get('videos', 0)} videos, 
                {knowledge.get('metadata', {}).get('sources', {}).get('books', 0)} books, 
                {knowledge.get('metadata', {}).get('sources', {}).get('papers', 0)} papers<br/>
                Time: {knowledge.get('metadata', {}).get('execution_time', 0)} seconds
            </font>
        </para>
        """
        story.append(Paragraph(meta_data, styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Complete Knowledge Summary
        story.append(Paragraph("📋 Complete Knowledge Summary", styles['SectionHeader']))
        story.append(Spacer(1, 10))
        
        summary = knowledge.get('complete_summary', 'No summary available.')
        for paragraph in summary.split('\n\n'):
            story.append(Paragraph(paragraph, styles['Content']))
            story.append(Spacer(1, 10))
        
        story.append(Spacer(1, 20))
        
        # Statistics Cards
        stats_data = [
            ['Videos Analyzed', 'Books Analyzed', 'Papers Analyzed'],
            [
                str(knowledge.get('metadata', {}).get('sources', {}).get('videos', 0)),
                str(knowledge.get('metadata', {}).get('sources', {}).get('books', 0)),
                str(knowledge.get('metadata', {}).get('sources', {}).get('papers', 0))
            ]
        ]
        
        stats_table = Table(stats_data, colWidths=[2*inch, 2*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 24),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#667eea')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        story.append(stats_table)
        story.append(Spacer(1, 30))
        
        # Videos Section
        story.append(Paragraph("🎥 Top Videos", styles['SectionHeader']))
        story.append(Spacer(1, 10))
        
        videos = knowledge.get('videos', [])
        for i, video in enumerate(videos[:5], 1):
            video_content = f"""
            <para>
                <b>{i}. {video.get('title', 'Unknown')}</b><br/>
                <font color="#718096">Channel: {video.get('channel', 'Unknown')}</font><br/>
                {video.get('description', '')[:200]}...
            </para>
            """
            story.append(Paragraph(video_content, styles['Content']))
            story.append(Spacer(1, 10))
        
        story.append(PageBreak())
        
        # Books Section
        story.append(Paragraph("📚 Top Books", styles['SectionHeader']))
        story.append(Spacer(1, 10))
        
        books = knowledge.get('books', [])
        for i, book in enumerate(books[:5], 1):
            authors = ', '.join(book.get('authors', ['Unknown'])[:2])
            book_content = f"""
            <para>
                <b>{i}. {book.get('title', 'Unknown')}</b><br/>
                <font color="#718096">By: {authors} | Rating: {book.get('rating', 'N/A')}</font><br/>
                {book.get('description', '')[:200]}...
            </para>
            """
            story.append(Paragraph(book_content, styles['Content']))
            story.append(Spacer(1, 10))
        
        # Papers Section
        story.append(Paragraph("📄 Top Research Papers", styles['SectionHeader']))
        story.append(Spacer(1, 10))
        
        papers = knowledge.get('papers', [])
        for i, paper in enumerate(papers[:5], 1):
            authors = ', '.join(paper.get('authors', ['Unknown'])[:2])
            paper_content = f"""
            <para>
                <b>{i}. {paper.get('title', 'Unknown')}</b><br/>
                <font color="#718096">By: {authors} ({paper.get('year', 'Unknown')}) | Citations: {paper.get('citations', 0)}</font><br/>
                {paper.get('abstract', '')[:200]}...
            </para>
            """
            story.append(Paragraph(paper_content, styles['Content']))
            story.append(Spacer(1, 10))
        
        # Footer
        story.append(Spacer(1, 30))
        footer = f"""
        <para align="center">
            <font color="#718096" size="8">
                Generated by TKAG-RAG Knowledge System • Page 1 of ?<br/>
                © {datetime.now().year} TKAG-RAG. All rights reserved.
            </font>
        </para>
        """
        story.append(Paragraph(footer, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        return output_path