# Backup of Unused/Redundant Code Files

This folder contains code files that were removed during codebase cleanup:

## Files Backed Up:
- enhanced_parsing_service.dart - Duplicate parsing logic (replaced by parsing_service.dart)
- text_parser.dart - Complex regex parser not being used
- medication_cleaner.dart - OCR cleaning logic (functionality moved to parsing_service.dart)

## Reason for Removal:
These files contained duplicate or unused functionality that was making the codebase harder to maintain.

## Current Active Parsing:
The app now uses a single, streamlined parsing_service.dart with:
- Grok-4 LLM integration
- Simple regex fallback
- Clean validation logic

Backup created on: Thu Aug 21 19:30:19 EDT 2025
