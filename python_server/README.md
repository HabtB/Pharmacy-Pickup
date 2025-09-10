# Docling OCR Server for Pharmacy Picker

This Python server provides advanced document parsing capabilities using Docling for the Pharmacy Picker Flutter app.

## Setup

1. **Install Python dependencies:**
```bash
cd python_server
pip install -r requirements.txt
```

2. **Start the server:**
```bash
python docling_server.py
```

The server will be available at `http://localhost:5000`

## API Endpoints

### Health Check
```
GET /health
```

### Parse Document
```
POST /parse-document
Content-Type: application/json

{
  "image_base64": "base64_encoded_image_data",
  "mode": "cart_fill" | "floor_stock"
}
```

**Response:**
```json
{
  "success": true,
  "medications": [
    {
      "name": "oxybutynin",
      "strength": "5 mg",
      "form": "tablet",
      "brand": "DITROPAN XL"
    }
  ],
  "raw_text": "markdown formatted text",
  "document_structure": {...}
}
```

## Features

- **Advanced OCR**: Uses Docling's document understanding capabilities
- **Table Recognition**: Automatically detects and parses tabular data (floor stock lists)
- **Layout Understanding**: Identifies medication labels vs other document elements
- **Structured Output**: Returns parsed medication data in consistent format
- **Two Modes**: Supports both floor stock and cart-fill parsing

## Integration with Flutter

The Flutter app will communicate with this server via HTTP requests, sending base64-encoded images and receiving structured medication data.
