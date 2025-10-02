#!/usr/bin/env python3
"""
Google Vision API OCR for Pharmacy Picker App
Direct implementation without Docling dependency
"""

import io
import os
from google.cloud import vision
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class GoogleVisionOCR:
    """Direct Google Vision API OCR implementation"""

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Google Vision client

        Args:
            credentials_path: Path to service account JSON file
                            If None, uses GOOGLE_APPLICATION_CREDENTIALS env var
        """
        if credentials_path and os.path.exists(credentials_path):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
            logger.info(f"Using credentials from: {credentials_path}")
        elif os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            logger.info(f"Using credentials from env var: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")
        else:
            logger.warning("No Google credentials found, will attempt default authentication")

        try:
            self.client = vision.ImageAnnotatorClient()
            logger.info("✓ Google Vision client initialized successfully")
        except Exception as e:
            logger.error(f"✗ Failed to initialize Google Vision client: {e}")
            self.client = None

    def extract_text_from_image(self, image_bytes: bytes) -> Dict:
        """
        Extract text from image using Google Vision API

        Args:
            image_bytes: Raw image bytes

        Returns:
            Dict with 'text', 'confidence', and 'success' keys
        """
        if not self.client:
            return {
                'success': False,
                'error': 'Google Vision client not initialized',
                'text': ''
            }

        try:
            # Create Vision API image object
            image = vision.Image(content=image_bytes)

            # Perform text detection
            logger.info("Sending image to Google Vision API...")
            response = self.client.text_detection(image=image)

            if response.error.message:
                logger.error(f"Google Vision API error: {response.error.message}")
                return {
                    'success': False,
                    'error': response.error.message,
                    'text': ''
                }

            # Extract text from response
            texts = response.text_annotations

            if not texts:
                logger.warning("No text detected in image")
                return {
                    'success': True,
                    'text': '',
                    'confidence': 0.0,
                    'word_count': 0
                }

            # First annotation contains full text
            full_text = texts[0].description

            # Calculate average confidence from individual words
            if len(texts) > 1:
                confidences = [word.confidence for word in texts[1:] if hasattr(word, 'confidence')]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.95
            else:
                avg_confidence = 0.95  # Default confidence for full text detection

            logger.info(f"✓ Extracted {len(full_text)} characters, {len(texts)-1} words")
            logger.info(f"  Confidence: {avg_confidence:.2%}")
            logger.info(f"  Preview: {full_text[:200]}...")

            return {
                'success': True,
                'text': full_text,
                'confidence': avg_confidence,
                'word_count': len(texts) - 1,
                'raw_response': texts
            }

        except Exception as e:
            logger.error(f"Error during text extraction: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }

    def extract_text_with_layout(self, image_bytes: bytes) -> Dict:
        """
        Extract text with layout information (useful for structured documents)

        Args:
            image_bytes: Raw image bytes

        Returns:
            Dict with structured text data
        """
        if not self.client:
            return {
                'success': False,
                'error': 'Google Vision client not initialized'
            }

        try:
            image = vision.Image(content=image_bytes)

            # Use document_text_detection for better structure
            response = self.client.document_text_detection(image=image)

            if response.error.message:
                return {
                    'success': False,
                    'error': response.error.message
                }

            document = response.full_text_annotation

            if not document.text:
                return {
                    'success': True,
                    'text': '',
                    'pages': []
                }

            # Extract structured information
            pages = []
            for page in document.pages:
                page_info = {
                    'width': page.width,
                    'height': page.height,
                    'blocks': []
                }

                for block in page.blocks:
                    block_text = []
                    for paragraph in block.paragraphs:
                        para_text = []
                        for word in paragraph.words:
                            word_text = ''.join([symbol.text for symbol in word.symbols])
                            para_text.append(word_text)
                        block_text.append(' '.join(para_text))

                    page_info['blocks'].append('\n'.join(block_text))

                pages.append(page_info)

            logger.info(f"✓ Extracted structured text: {len(pages)} pages, {len(document.text)} characters")

            return {
                'success': True,
                'text': document.text,
                'pages': pages,
                'confidence': 0.95
            }

        except Exception as e:
            logger.error(f"Error during document text extraction: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global instance
_vision_ocr = None


def get_vision_ocr(credentials_path: Optional[str] = None) -> GoogleVisionOCR:
    """Get or create Google Vision OCR instance"""
    global _vision_ocr
    if _vision_ocr is None:
        _vision_ocr = GoogleVisionOCR(credentials_path)
    return _vision_ocr


def extract_text(image_bytes: bytes, use_layout: bool = False) -> Dict:
    """
    Convenience function to extract text from image

    Args:
        image_bytes: Raw image bytes
        use_layout: If True, use document_text_detection for structured extraction

    Returns:
        Dict with extraction results
    """
    ocr = get_vision_ocr()
    if use_layout:
        return ocr.extract_text_with_layout(image_bytes)
    else:
        return ocr.extract_text_from_image(image_bytes)
