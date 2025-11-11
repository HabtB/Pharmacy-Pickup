"""
Hybrid Row-Based Parsing Methods
Add these methods to the FloorStockParser class
"""

def _parse_with_row_clustering(self, text: str, word_annotations: List) -> List[Dict]:
    """
    Hybrid approach: Use coordinates to identify rows, LLM to interpret content

    Strategy:
    1. Cluster words by Y-coordinate into table rows
    2. Identify column X-positions from header row
    3. For each data row, extract words by column
    4. Give LLM structured row data to interpret
    5. Validate with formula: Pick = Max - Current
    """
    try:
        logger.info("=== HYBRID ROW-BASED PARSER: Starting ===")

        # Step 1: Extract words with coordinates from Google Vision
        words = self._extract_words_with_coordinates(word_annotations)
        if not words:
            logger.warning("No words with coordinates found")
            return []

        logger.info(f"Extracted {len(words)} words with coordinates")

        # Step 2: Cluster words into rows by Y-coordinate
        rows = self._cluster_words_into_rows(words)
        logger.info(f"Clustered into {len(rows)} rows")

        if len(rows) < 2:
            logger.warning("Not enough rows found (need at least header + 1 data row)")
            return []

        # Step 3: Identify column positions from header row
        columns = self._identify_columns_from_header(rows[0])
        if not columns:
            logger.warning("Could not identify table columns from header")
            return []

        logger.info(f"Identified columns: {list(columns.keys())}")

        # Step 4: Extract medications from data rows
        medications = []
        current_floor = None

        for i, row in enumerate(rows[1:], start=1):  # Skip header row
            # Check if this row contains a floor/device identifier
            floor = self._extract_floor_from_row(row)
            if floor:
                current_floor = floor
                logger.info(f"Row {i}: Found floor identifier: {floor}")
                continue

            # Extract medication data from row
            med_data = self._extract_medication_from_row(row, columns, current_floor)
            if med_data:
                # Validate with formula
                if med_data.get('pick_amount') and med_data.get('max') and med_data.get('current_amount'):
                    expected_pick = med_data['max'] - med_data['current_amount']
                    actual_pick = med_data['pick_amount']

                    if abs(actual_pick - expected_pick) <= 5:
                        logger.info(f"✓ {med_data['name']}: Formula validated pick={actual_pick}, max={med_data['max']}, current={med_data['current_amount']}")
                    else:
                        logger.warning(f"⚠ {med_data['name']}: Formula mismatch! pick={actual_pick}, expected={expected_pick} (max={med_data['max']}, current={med_data['current_amount']})")
                        med_data['warning'] = f"⚠ Formula mismatch! Found Pick={actual_pick}, Max={med_data['max']}, Current={med_data['current_amount']}. Expected Pick={expected_pick}. Please verify manually."

                medications.append(med_data)
                logger.info(f"Row {i}: Extracted {med_data['name']} - Pick: {med_data.get('pick_amount', 'N/A')}")

        logger.info(f"=== HYBRID PARSER: Found {len(medications)} medications ===")
        return medications

    except Exception as e:
        logger.error(f"Hybrid row-based parsing failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def _extract_words_with_coordinates(self, word_annotations: List) -> List[Dict]:
    """Extract words with their bounding box coordinates from Google Vision response"""
    words = []

    if not word_annotations:
        return words

    try:
        # Handle Google Vision response structure
        if isinstance(word_annotations, dict) and 'responses' in word_annotations:
            # Full API response
            responses = word_annotations['responses']
            if responses and len(responses) > 0:
                text_annotations = responses[0].get('textAnnotations', [])
                if len(text_annotations) > 1:  # Skip first (full text)
                    for annotation in text_annotations[1:]:
                        vertices = annotation.get('boundingPoly', {}).get('vertices', [])
                        if len(vertices) >= 2:
                            # Calculate center and bounds
                            x_coords = [v.get('x', 0) for v in vertices]
                            y_coords = [v.get('y', 0) for v in vertices]

                            words.append({
                                'text': annotation.get('description', ''),
                                'x': sum(x_coords) / len(x_coords),
                                'y': sum(y_coords) / len(y_coords),
                                'x_min': min(x_coords),
                                'x_max': max(x_coords),
                                'y_min': min(y_coords),
                                'y_max': max(y_coords),
                            })

        logger.info(f"Extracted {len(words)} words with coordinates")
        return words

    except Exception as e:
        logger.error(f"Error extracting words with coordinates: {str(e)}")
        return []


def _cluster_words_into_rows(self, words: List[Dict]) -> List[List[Dict]]:
    """Cluster words by Y-coordinate into table rows"""
    if not words:
        return []

    # Sort words by Y-coordinate
    sorted_words = sorted(words, key=lambda w: w['y'])

    # Cluster into rows with ±15px Y-tolerance
    rows = []
    current_row = [sorted_words[0]]
    current_y = sorted_words[0]['y']

    for word in sorted_words[1:]:
        if abs(word['y'] - current_y) <= 15:  # Same row
            current_row.append(word)
        else:  # New row
            # Sort current row by X-coordinate (left to right)
            current_row.sort(key=lambda w: w['x'])
            rows.append(current_row)

            # Start new row
            current_row = [word]
            current_y = word['y']

    # Add last row
    if current_row:
        current_row.sort(key=lambda w: w['x'])
        rows.append(current_row)

    logger.info(f"Clustered {len(words)} words into {len(rows)} rows")
    return rows


def _identify_columns_from_header(self, header_row: List[Dict]) -> Dict[str, tuple]:
    """Identify column X-position ranges from header row"""
    columns = {}

    # Find key headers
    for word in header_row:
        text_lower = word['text'].lower()

        if 'pick' in text_lower and 'amount' in text_lower:
            columns['pick_amount'] = (word['x_min'] - 30, word['x_max'] + 30)
        elif 'pick' in text_lower and 'actual' not in text_lower:
            if 'pick_amount' not in columns:  # Don't override "Pick Amount"
                columns['pick_amount'] = (word['x_min'] - 30, word['x_max'] + 30)
        elif text_lower == 'max':
            columns['max'] = (word['x_min'] - 30, word['x_max'] + 30)
        elif 'current' in text_lower:
            columns['current_amount'] = (word['x_min'] - 30, word['x_max'] + 30)
        elif 'med' in text_lower or 'description' in text_lower:
            columns['med_description'] = (word['x_min'] - 30, word['x_max'] + 100)
        elif 'device' in text_lower:
            columns['device'] = (word['x_min'] - 30, word['x_max'] + 30)

    # If we didn't find Pick Amount but found Max and Current, infer Pick Amount position
    if 'max' in columns and 'current_amount' in columns and 'pick_amount' not in columns:
        max_x = columns['max'][0]
        # Pick Amount is typically 80-150px to the left of Max
        columns['pick_amount'] = (max_x - 150, max_x - 50)
        logger.info(f"Inferred pick_amount column position: {columns['pick_amount']}")

    return columns


def _extract_floor_from_row(self, row: List[Dict]) -> Optional[str]:
    """Check if row contains a floor/device identifier (e.g., '9E-1', '9E-2')"""
    # Look for patterns like "9E-1", "9E-2", "6W-1", etc.
    for word in row:
        text = word['text'].strip()
        # Match floor pattern: number + letter(s) + dash + number
        if re.match(r'^\d+[A-Z]+-\d+$', text):
            return text
        # Also check for "9E" style (without the -1/-2)
        if re.match(r'^\d+[A-Z]+$', text) and len(text) <= 4:
            # Check if next word is a dash or number
            idx = row.index(word)
            if idx + 1 < len(row):
                next_text = row[idx + 1]['text'].strip()
                if next_text == '-' and idx + 2 < len(row):
                    floor_num = row[idx + 2]['text'].strip()
                    if floor_num.isdigit():
                        return f"{text}-{floor_num}"

    return None


def _extract_medication_from_row(self, row: List[Dict], columns: Dict[str, tuple], current_floor: Optional[str]) -> Optional[Dict]:
    """Extract medication data from a table row using column positions"""
    try:
        # Extract words in each column
        med_words = []
        pick_amount = None
        max_amount = None
        current_amount = None

        for word in row:
            x = word['x']
            text = word['text'].strip()

            # Skip empty words
            if not text:
                continue

            # Check which column this word belongs to
            if 'med_description' in columns:
                x_min, x_max = columns['med_description']
                if x_min <= x <= x_max:
                    # Skip if it's a number in strength (e.g., "650" in "650 mg")
                    if not (text.isdigit() and len(med_words) > 0 and 'mg' in ' '.join([w['text'] for w in row])):
                        med_words.append(text)

            if 'pick_amount' in columns:
                x_min, x_max = columns['pick_amount']
                if x_min <= x <= x_max and text.isdigit():
                    pick_amount = int(text)

            if 'max' in columns:
                x_min, x_max = columns['max']
                if x_min <= x <= x_max and text.isdigit():
                    max_amount = int(text)

            if 'current_amount' in columns:
                x_min, x_max = columns['current_amount']
                if x_min <= x <= x_max and text.isdigit():
                    current_amount = int(text)

        # Must have at least a medication name
        if not med_words:
            return None

        # Join medication words
        med_text = ' '.join(med_words)

        # Use LLM to parse medication name, strength, and form from the text
        med_data = self._parse_medication_text_with_llm(med_text)
        if not med_data:
            return None

        # Add the numbers we extracted from columns
        med_data['pick_amount'] = pick_amount
        med_data['max'] = max_amount
        med_data['current_amount'] = current_amount
        med_data['floor'] = current_floor

        return med_data

    except Exception as e:
        logger.error(f"Error extracting medication from row: {str(e)}")
        return None


def _parse_medication_text_with_llm(self, med_text: str) -> Optional[Dict]:
    """Use LLM to parse medication name, strength, and form from text"""
    try:
        if not self.api_key:
            return None

        prompt = f"""Extract medication information from this text and return ONLY valid JSON:

Text: "{med_text}"

Extract:
- name: generic medication name (lowercase first letter, e.g., "gabapentin", "acetaminophen")
- strength: dose with units (e.g., "325 mg", "100 mg")
- form: medication form (tablet, capsule, vial, bag, patch, etc.)

Return ONLY JSON in this exact format:
{{"name": "medication name", "strength": "dose with units", "form": "form"}}

No explanations, just the JSON:"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "messages": [
                {"role": "system", "content": "You are a medication extraction expert. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.1,
            "max_tokens": 200
        }

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content'].strip()

            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                med_data = json.loads(json_match.group())
                return med_data

        return None

    except Exception as e:
        logger.error(f"LLM parsing failed: {str(e)}")
        return None
