"""
Image conversion utilities.
"""
import os
import io
import tempfile
import logging
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

logger = logging.getLogger(__name__)


def convert_image_to_pdf(image_data):
    """Convert image bytes to PDF file for Docling processing"""
    try:
        logger.info(f"Converting image to PDF, input size: {len(image_data)} bytes")

        # Open image from bytes
        image = Image.open(io.BytesIO(image_data))
        logger.info(f"Original image: {image.size} pixels, mode: {image.mode}")

        # Handle PNG with transparency
        if image.mode in ('RGBA', 'LA', 'P'):
            logger.info(f"Converting {image.mode} to RGB with white background")
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            logger.info(f"Converting {image.mode} to RGB")
            image = image.convert('RGB')

        # Auto-rotate image based on EXIF data (important for mobile photos)
        try:
            image = ImageOps.exif_transpose(image)
            logger.info("Applied EXIF rotation correction")
        except Exception as e:
            logger.warning(f"Could not apply EXIF rotation: {e}")

        # Enhance image for better OCR
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)

        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.3)

        # Apply slight denoising
        image = image.filter(ImageFilter.MedianFilter(size=3))

        # Ensure minimum resolution for OCR
        min_width, min_height = 1200, 1600
        if image.size[0] < min_width or image.size[1] < min_height:
            scale_x = min_width / image.size[0] if image.size[0] < min_width else 1
            scale_y = min_height / image.size[1] if image.size[1] < min_height else 1
            scale = max(scale_x, scale_y)

            new_size = (int(image.size[0] * scale), int(image.size[1] * scale))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"Upscaled image to {new_size} for better OCR")

        logger.info(f"Final processed image: {image.size} pixels")

        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            pdf_path = temp_pdf.name

        # Create PDF with image
        c = canvas.Canvas(pdf_path, pagesize=letter)

        # Get image dimensions and scale to fit page
        img_width, img_height = image.size
        page_width, page_height = letter

        # Calculate scaling to fit page while maintaining aspect ratio
        scale_x = page_width / img_width
        scale_y = page_height / img_height
        scale = min(scale_x, scale_y) * 0.9  # 90% of page to leave margins

        new_width = img_width * scale
        new_height = img_height * scale

        # Center image on page
        x = (page_width - new_width) / 2
        y = (page_height - new_height) / 2

        # Save image to temporary file for PDF creation
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_img:
            image.save(temp_img.name, 'PNG')
            temp_img_path = temp_img.name

        try:
            c.drawImage(temp_img_path, x, y, width=new_width, height=new_height)
            c.save()
        finally:
            os.unlink(temp_img_path)

        return pdf_path

    except Exception as e:
        logger.error(f"Error converting image to PDF: {str(e)}")
        raise
