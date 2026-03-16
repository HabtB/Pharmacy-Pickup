"""
Parsing routes — /parse-document and /parse-documents-parallel endpoints.
"""
import base64
import time
import logging
import concurrent.futures
from datetime import datetime
from collections import defaultdict

from flask import Blueprint, request, jsonify

from google_vision_ocr import GoogleVisionOCR
from medication_location_lookup import get_location_lookup

logger = logging.getLogger(__name__)

parsing_bp = Blueprint('parsing', __name__)

# Shared Google Vision instance (initialized by app.py and injected here)
google_vision = None


def init_google_vision(gv_instance):
    """Called by app.py to share the GoogleVisionOCR singleton."""
    global google_vision
    google_vision = gv_instance


# ---------------------------------------------------------------------------
# Helper: enrich medications with pick-location data
# ---------------------------------------------------------------------------
def _enrich_with_locations(medications):
    """Add pick_location, pick_location_desc, and pick_image to each med dict."""
    location_lookup = get_location_lookup()
    locations_found = 0
    missing_meds = []

    for med in medications:
        med_name = med.get('name', '')
        strength = med.get('strength', '') if 'strength' in med else med.get('dose', '')
        form = med.get('form', '')

        location_info = location_lookup.find_location(med_name, strength, form)

        if location_info:
            med['pick_location'] = location_info['location_code']
            med['pick_location_desc'] = location_lookup.get_location_description(location_info['location_code'])
            med['pick_image'] = location_info.get('image_file', '')
            locations_found += 1
        else:
            med['pick_location'] = 'UNKNOWN'
            med['pick_location_desc'] = 'Location not found'
            med['pick_image'] = ''
            missing_meds.append(f"{med_name} {strength} {form}".strip())

    logger.info(f"✓ Locations found: {locations_found}/{len(medications)}")
    if missing_meds:
        logger.info(f"⚠ Locations not found: {len(missing_meds)}")
        for missing in missing_meds:
            logger.info(f"  ✗ Missing: {missing}")


# ---------------------------------------------------------------------------
# /parse-document
# ---------------------------------------------------------------------------
@parsing_bp.route('/parse-document', methods=['POST'])
def parse_document():
    """
    Parse medication documents using Enhanced Medication Parser.
    Accepts multipart form-data (preferred) or legacy JSON with base64 image.
    """
    start_total = time.time()

    try:
        # --- MULTIPART FORM-DATA (preferred — no base64 overhead) ---
        if request.content_type and 'multipart/form-data' in request.content_type:
            if 'image' not in request.files:
                return jsonify({'error': 'No image file in multipart request'}), 400

            image_file = request.files['image']
            image_data = image_file.read()
            mode = request.form.get('mode', 'cart_fill')
            strategy = request.form.get('strategy', 'google_vision')

            logger.info(f"=== MULTIPART UPLOAD ===")
            logger.info(f"Mode: {mode}, Image size: {len(image_data)} bytes, Filename: {image_file.filename}")

            # Process floor_stock mode with Gemini Vision
            if mode.strip() == 'floor_stock':
                logger.info("=== FLOOR STOCK MODE: Trying Gemini Vision ===")
                from floor_stock_parser import FloorStockParser
                parser = FloorStockParser()

                start_gemini = time.time()
                validated_medications = parser.parse_with_gemini_vision(image_data)
                gemini_time = (time.time() - start_gemini) * 1000
                total_time = (time.time() - start_total) * 1000

                if validated_medications and len(validated_medications) > 0:
                    logger.info(f"✓ Gemini Vision successful: {len(validated_medications)} medications found in {gemini_time:.2f} ms")
                    _enrich_with_locations(validated_medications)

                    return jsonify({
                        'success': True,
                        'medications': validated_medications,
                        'raw_text': '',
                        'method': 'gemini_vision_primary',
                        'ocr_confidence': 0.95,
                        'performance': {
                            'ocr_time_ms': 0,
                            'parse_time_ms': round(gemini_time, 2),
                            'total_time_ms': round(total_time, 2),
                            'medications_found': len(validated_medications)
                        }
                    })
                else:
                    logger.error("Gemini Vision returned no results")
                    return jsonify({
                        'success': False,
                        'error': "Gemini Vision failed",
                        'medications': [],
                        'raw_text': ''
                    }), 500

            # Process cart_fill or other modes with Enhanced Parser
            logger.info(f"=== {mode.upper()} MODE: Using Enhanced Parser ===")
            from enhanced_medication_parser import EnhancedMedicationParser
            parser = EnhancedMedicationParser()

            start_parse = time.time()
            parse_result = parser.parse_medication_label(image_data, mode)
            parse_time = (time.time() - start_parse) * 1000
            total_time = (time.time() - start_total) * 1000

            medications = parse_result.get('medications', [])
            raw_text = parse_result.get('raw_text', '')

            logger.info(f"✓ Parsing complete: {len(medications)} medications found in {parse_time:.2f} ms")

            if mode == 'floor_stock' and medications:
                _enrich_with_locations(medications)

            return jsonify({
                'success': True,
                'medications': medications,
                'raw_text': raw_text,
                'method': 'enhanced_parser',
                'ocr_confidence': 0.95,
                'performance': {
                    'parse_time_ms': round(parse_time, 2),
                    'total_time_ms': round(total_time, 2),
                    'medications_found': len(medications)
                }
            })

        # --- LEGACY JSON BASE64 (backward compatibility) ---
        else:
            data = request.get_json()

            if not data:
                return jsonify({'error': 'No data provided'}), 400

            if 'image_base64' not in data:
                return jsonify({'error': 'No image_base64 provided'}), 400

            image_data = base64.b64decode(data['image_base64'])
            mode = data.get('mode', 'cart_fill')
            strategy = data.get('strategy', 'google_vision')

            logger.info(f"=== STARTING PARSING ===")
            logger.info(f"Mode: {mode}, Image size: {len(image_data)} bytes")

            # For floor_stock mode, try Gemini Vision FIRST
            logger.info(f"DEBUG CHECK: mode='{mode}', type={type(mode)}")
            if mode.strip() == 'floor_stock':
                logger.info("=== FLOOR STOCK MODE: Trying Gemini Vision first (OCR + Parsing in one call) ===")
                from floor_stock_parser import FloorStockParser
                parser = FloorStockParser()

                start_gemini = time.time()
                validated_medications = parser.parse_with_gemini_vision(image_data)
                gemini_time = (time.time() - start_gemini) * 1000
                total_time = (time.time() - start_total) * 1000

                if validated_medications and len(validated_medications) > 0:
                    logger.info(f"✓ Gemini Vision successful: {len(validated_medications)} medications found in {gemini_time:.2f} ms")

                    for i, med in enumerate(validated_medications):
                        floor_info = f" - Floor: {med.get('floor', 'N/A')}" if 'floor' in med else ""
                        logger.info(f"  {i+1}. {med.get('name', 'Unknown')} - {med.get('strength', '')} - {med.get('form', '')} - Pick: {med.get('pick_amount', 'N/A')}{floor_info}")

                    _enrich_with_locations(validated_medications)

                    return jsonify({
                        'success': True,
                        'medications': validated_medications,
                        'raw_text': '',
                        'method': 'gemini_vision_primary',
                        'ocr_confidence': 0.95,
                        'word_count': 0,
                        'performance': {
                            'ocr_time_ms': 0,
                            'parse_time_ms': round(gemini_time, 2),
                            'total_time_ms': round(total_time, 2),
                            'accuracy_percent': 100.0,
                            'medications_found': len(validated_medications),
                            'medications_expected': len(validated_medications)
                        }
                    })
                else:
                    logger.error(f"Gemini Vision returned no results. OCR FALLBACK IS DISABLED BY USER REQUEST.")
                    return jsonify({
                        'success': False,
                        'error': "Gemini Vision failed and OCR fallback is disabled.",
                        'medications': [],
                        'raw_text': ''
                    }), 500

            # EXCLUSIVE GEMINI VISION PATH
            logger.info(f"=== STARTING PARSING WITH GEMINI VISION (EXCLUSIVE) ===")
            start_parse = time.time()
            ocr_time = 0

            from enhanced_medication_parser import EnhancedMedicationParser
            parser = EnhancedMedicationParser()

            parse_result = parser.parse_medication_label(image_data, mode)

            medications = parse_result.get('medications', [])
            validated_medications = medications
            raw_text = parse_result.get('raw_text', '')

            parse_time = (time.time() - start_parse) * 1000
            total_time = (time.time() - start_total) * 1000

            logger.info(f"✓ Gemini Vision complete: {len(validated_medications)} medications found")

            expected_count = data.get('expected_count', len(validated_medications))
            accuracy = (len(validated_medications) / max(expected_count, 1)) * 100 if expected_count > 0 else 100.0

            logger.info(f"✓ Parsing complete: {len(validated_medications)} medications found in {parse_time:.2f} ms")

            if validated_medications:
                for i, med in enumerate(validated_medications):
                    floor_info = f" - Floor: {med.get('floor', 'N/A')}" if 'floor' in med else ""
                    logger.info(f"  {i+1}. {med.get('name', 'Unknown')} - {med.get('strength', '')} - {med.get('form', '')} - Pick: {med.get('pick_amount', 'N/A')}{floor_info}")

            if mode == 'floor_stock' and validated_medications:
                _enrich_with_locations(validated_medications)

            return jsonify({
                'success': True,
                'medications': validated_medications,
                'raw_text': raw_text,
                'method': 'google_vision',
                'ocr_confidence': 0.95,
                'word_count': 0,
                'performance': {
                    'ocr_time_ms': round(ocr_time, 2),
                    'parse_time_ms': round(parse_time, 2),
                    'total_time_ms': round(total_time, 2),
                    'accuracy_percent': round(accuracy, 1),
                    'medications_found': len(validated_medications),
                    'medications_expected': expected_count
                }
            })

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# /parse-documents-parallel
# ---------------------------------------------------------------------------
@parsing_bp.route('/parse-documents-parallel', methods=['POST'])
def parse_documents_parallel():
    """
    Parse multiple medication documents in parallel.
    Accepts multipart form-data (preferred) or legacy JSON with base64 images.
    """
    try:
        # --- MULTIPART FORM-DATA ---
        if request.content_type and 'multipart/form-data' in request.content_type:
            image_data_list = []
            idx = 0
            while f'image_{idx}' in request.files:
                image_data_list.append(request.files[f'image_{idx}'].read())
                idx += 1

            if not image_data_list:
                return jsonify({'error': 'No image files in multipart request'}), 400

            mode = request.form.get('mode', 'cart_fill')
            logger.info(f"=== MULTIPART PARALLEL UPLOAD: {len(image_data_list)} images ===")

            images = [base64.b64encode(raw).decode('utf-8') for raw in image_data_list]

        # --- LEGACY JSON BASE64 ---
        else:
            data = request.get_json()

            if not data:
                return jsonify({'error': 'No data provided'}), 400

            images = data.get('images', [])
            if not images or len(images) == 0:
                return jsonify({'error': 'No images provided'}), 400

            mode = data.get('mode', 'cart_fill')

        # Session banner
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("\n" + "#" * 80)
        logger.info(f"### NEW SCAN SESSION: {timestamp}")
        logger.info(f"### Client: {request.remote_addr}")
        logger.info(f"### Images: {len(images)}")
        logger.info("#" * 80 + "\n")

        logger.info(f"=== PARALLEL PROCESSING: {len(images)} images ===")

        # ---- Inner function: process a single image ----
        def process_single_image(image_base64, index):
            try:
                logger.info(f"[Image {index+1}] Starting processing...")

                img_data = base64.b64decode(image_base64)

                if mode == 'floor_stock':
                    logger.info(f"[Image {index+1}] FLOOR STOCK MODE: Trying Gemini Vision first")
                    from floor_stock_parser import FloorStockParser
                    parser = FloorStockParser()

                    validated_medications = parser.parse_with_gemini_vision(img_data)

                    if validated_medications and len(validated_medications) > 0:
                        logger.info(f"[Image {index+1}] ✓ Gemini Vision successful: {len(validated_medications)} medications")
                        return {
                            'success': True,
                            'medications': validated_medications,
                            'raw_text': '',
                            'method': 'gemini_vision_primary',
                            'index': index
                        }
                    else:
                        logger.error(f"[Image {index+1}] Gemini Vision returned no results. Backup OCR is disabled.")
                        return {
                            'success': False,
                            'error': "Gemini Vision failed and backup OCR is disabled",
                            'medications': [],
                            'index': index
                        }

                # Non-floor-stock: Google Vision OCR
                logger.info(f"[Image {index+1}] Using Google Vision OCR...")
                ocr_result = google_vision.extract_text_from_image(img_data)

                if not ocr_result['success']:
                    logger.error(f"[Image {index+1}] Google Vision OCR failed: {ocr_result.get('error', 'Unknown error')}")
                    return {
                        'success': False,
                        'error': f"OCR failed: {ocr_result.get('error', 'Unknown error')}",
                        'medications': [],
                        'raw_text': '',
                        'index': index
                    }

                raw_text = ocr_result['text']
                logger.info(f"[Image {index+1}] ✓ OCR extracted {len(raw_text)} characters")

                if mode == 'floor_stock':
                    logger.info(f"[Image {index+1}] Using hybrid parser (Google OCR + coordinates + LLM)...")
                    from floor_stock_parser import FloorStockParser
                    parser = FloorStockParser()
                    validated_medications = parser.parse(raw_text, ocr_result.get('raw_response'))

                    if not validated_medications:
                        logger.warning(f"[Image {index+1}] Hybrid parser found 0 medications. Retrying with Gemini Vision...")
                        gemini_meds = parser.parse_with_gemini_vision(img_data)
                        if gemini_meds:
                            logger.info(f"[Image {index+1}] ✓ Gemini Vision fallback successful: {len(gemini_meds)} medications")
                            validated_medications = gemini_meds
                            ocr_result['method'] = 'gemini_vision_fallback'
                else:
                    from enhanced_medication_parser import EnhancedMedicationParser
                    parser = EnhancedMedicationParser()

                    medications = parser._parse_with_best_llm(raw_text, mode)

                    if not medications:
                        logger.info(f"[Image {index+1}] LLM parsing returned no results, trying regex fallback")
                        medications = parser._parse_with_regex_fallback(raw_text, mode)

                    validated_medications = parser._validate_and_enhance(medications, raw_text)

                logger.info(f"[Image {index+1}] ✓ Parsing complete: {len(validated_medications)} medications found")

                # Enrich with locations
                _enrich_with_locations(validated_medications)

                return {
                    'success': True,
                    'medications': validated_medications,
                    'raw_text': raw_text,
                    'method': 'google_vision',
                    'ocr_confidence': ocr_result.get('confidence', 0.95),
                    'word_count': ocr_result.get('word_count', 0),
                    'index': index
                }

            except Exception as e:
                logger.error(f"[Image {index+1}] Error processing: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'medications': [],
                    'index': index
                }

        # ---- Execute in parallel ----
        max_workers = min(len(images), 5)
        logger.info(f"Using {max_workers} parallel workers")

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(process_single_image, img, i): i
                for i, img in enumerate(images)
            }

            completed_count = 0
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                completed_count += 1
                try:
                    result = future.result()
                    results.append(result)
                    med_count = len(result.get('medications', []))
                    logger.info(f"[Image {index+1}/{len(images)}] Completed ({completed_count}/{len(images)}) - Found {med_count} medications")
                except Exception as e:
                    logger.error(f"[Image {index+1}/{len(images)}] Exception: {str(e)}")
                    results.append({
                        'success': False,
                        'error': str(e),
                        'medications': [],
                        'index': index
                    })

        # Sort by original index
        results.sort(key=lambda x: x['index'])

        # ---- DEDUPLICATION for floor_stock mode ----
        if mode == 'floor_stock':
            logger.info(f"=== DEDUPLICATION: Merging medications across {len(results)} pages ===")

            all_meds = []
            for result in results:
                if result.get('success'):
                    all_meds.extend(result.get('medications', []))

            logger.info(f"Total medications before dedup: {len(all_meds)}")

            med_groups = defaultdict(list)
            for med in all_meds:
                name = med.get('name', '').lower().strip()
                strength = med.get('strength', '').lower().strip()
                form = med.get('form', '').lower().strip()
                key = f"{name}|{strength}|{form}"
                med_groups[key].append(med)

            deduplicated = []
            duplicates_found = []

            for key, group in med_groups.items():
                if len(group) == 1:
                    med = group[0]
                    med['floor_breakdown'] = [{'floor': med.get('floor', 'Unknown'), 'amount': med.get('pick_amount', 0)}]
                    deduplicated.append(med)
                else:
                    merged = group[0].copy()
                    total_pick = 0
                    floor_counts = defaultdict(int)

                    for m in group:
                        amt = m.get('pick_amount', 0)
                        total_pick += amt
                        fl = m.get('floor', 'Unknown')
                        floor_counts[fl] += amt

                    merged['pick_amount'] = total_pick
                    merged['notes'] = f"Combined from {len(group)} entries"

                    breakdown_list = [{'floor': fl, 'amount': amt} for fl, amt in floor_counts.items()]

                    if len(floor_counts) > 1:
                        unique_floors = sorted(list(floor_counts.keys()))
                        merged['floor'] = ", ".join(unique_floors)

                    merged['floor_breakdown'] = breakdown_list
                    deduplicated.append(merged)

                    duplicates_found.append({
                        'name': group[0].get('name'),
                        'strength': group[0].get('strength'),
                        'form': group[0].get('form'),
                        'floor': "Multiple",
                        'instances': len(group),
                        'total_pick_amount': total_pick,
                        'breakdown': breakdown_list
                    })

            logger.info(f"Total medications after dedup: {len(deduplicated)}")

            if duplicates_found:
                logger.info(f"🔄 DUPLICATES FOUND: {len(duplicates_found)} medications appeared multiple times")
                for dup in duplicates_found:
                    logger.info(f"  • {dup['name']} | {dup['strength']} | {dup['form']} → {dup['instances']} times, total: {dup['total_pick_amount']}")


            # Enrich deduplicated list with locations
            logger.info("=== ADDING PICK LOCATIONS ===")
            _enrich_with_locations(deduplicated)

            results = [{
                'success': True,
                'medications': deduplicated,
                'index': 0
            }]

        # Summary
        total_medications = sum(len(r.get('medications', [])) for r in results)
        successful = sum(1 for r in results if r.get('success', False))

        logger.info(f"=== PARALLEL PROCESSING COMPLETE ===")
        logger.info(f"  Total images: {len(images)}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Total medications: {total_medications}")

        return jsonify({
            'success': True,
            'results': results,
            'summary': {
                'total_images': len(images),
                'successful': successful,
                'failed': len(images) - successful,
                'total_medications': total_medications
            }
        })

    except Exception as e:
        logger.error(f"Error in parallel processing: {str(e)}")
        return jsonify({'error': str(e)}), 500
