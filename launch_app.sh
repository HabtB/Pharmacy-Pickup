#!/bin/bash

# Flutter app launcher script with robust error handling
# Usage: ./launch_app.sh

DEVICE_ID="00008101-00012DD01A99001E"
PROJECT_DIR="/Users/habtamu/Documents/pharmacy_pickup_app"

echo "🚀 Starting Flutter app launcher..."

# Step 1: Kill any existing Flutter/Dart processes
echo "📱 Cleaning up existing processes..."
killall -9 Flutter dart idevicesyslog iproxy 2>/dev/null
sleep 2

# Step 2: Verify device connection
echo "🔍 Checking device connection..."
if ! flutter devices | grep -q "$DEVICE_ID"; then
    echo "❌ Device not found. Please check USB connection."
    exit 1
fi
echo "✅ Device connected"

# Step 3: Navigate to project directory
cd "$PROJECT_DIR" || exit 1

# Step 4: Clean build if needed (uncomment if you have build issues)
# echo "🧹 Cleaning build..."
# flutter clean
# flutter pub get

# Step 5: Launch app with retry logic
MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "🎯 Launching app (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)..."

    # Try flutter run with timeout
    timeout 180 flutter run -d "$DEVICE_ID" &
    FLUTTER_PID=$!

    # Wait and check if app launched
    sleep 45

    if ps -p $FLUTTER_PID > /dev/null 2>&1; then
        echo "✅ App launched successfully!"
        echo "📊 Monitoring logs... (Press Ctrl+C to stop)"
        wait $FLUTTER_PID
        exit 0
    else
        echo "⚠️  Launch attempt failed, retrying..."
        RETRY_COUNT=$((RETRY_COUNT + 1))
        killall -9 Flutter dart idevicesyslog iproxy 2>/dev/null
        sleep 3
    fi
done

echo "❌ Failed to launch app after $MAX_RETRIES attempts"
echo "💡 Try these manual steps:"
echo "   1. Disconnect and reconnect USB cable"
echo "   2. Unlock your iPhone"
echo "   3. Trust this computer if prompted"
echo "   4. Run: flutter clean && flutter pub get"
echo "   5. Try running: flutter run -d $DEVICE_ID"
exit 1
