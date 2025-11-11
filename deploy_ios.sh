#!/bin/bash

# iOS Deployment Script for Pharmacy Picker
# Handles code signing and deployment to AneBaeley device

DEVICE_ID="00008101-00012DD01A99001E"
DEVICE_NAME="AneBaeley"
BUNDLE_ID="com.example.pharmacyPickupApp"

echo "🚀 Starting iOS deployment to $DEVICE_NAME..."

# Check if device is connected using Flutter's device detection
echo "📱 Checking device connection..."
if ! flutter devices | grep -q "$DEVICE_ID"; then
    echo "❌ Device $DEVICE_NAME not found! Please connect your iPhone."
    echo "Available devices:"
    flutter devices
    exit 1
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
flutter clean
rm -rf build/

# Get dependencies
echo "📦 Getting Flutter dependencies..."
flutter pub get

# Configure automatic code signing in Xcode project
echo "🔐 Configuring automatic code signing..."
/usr/libexec/PlistBuddy -c "Set :objects:97C146E61CF9000F007C117D:attributes:TargetAttributes:97C146ED1CF9000F007C117D:DevelopmentTeam $(security find-identity -v -p codesigning | grep 'Developer' | head -1 | cut -d'"' -f2 | cut -d'(' -f2 | cut -d')' -f1)" ios/Runner.xcodeproj/project.pbxproj 2>/dev/null || true

# Build and deploy using Flutter with proper signing
echo "🔨 Building and deploying iOS app..."
flutter build ios --release

# Deploy directly using Flutter
echo "📲 Deploying to device..."
flutter install --device-id=$DEVICE_ID

if [ $? -eq 0 ]; then
    echo "🎉 App successfully deployed to $DEVICE_NAME!"
    echo "💡 The app should launch automatically. If not:"
    echo "   1. Go to Settings > General > VPN & Device Management"
    echo "   2. Trust the developer certificate"
    echo "   3. Launch the Pharmacy Picker app"
    
    # Try to launch the app
    echo "🚀 Attempting to launch app..."
    xcrun devicectl device process launch --device $DEVICE_ID $BUNDLE_ID || echo "⚠️  Manual launch required - check device settings"
    
else
    echo "❌ Deployment failed!"
    echo "🔧 Trying alternative deployment method..."
    
    # Alternative: Use Xcode command line
    xcodebuild \
        -workspace ios/Runner.xcworkspace \
        -scheme Runner \
        -configuration Release \
        -destination "id=$DEVICE_ID" \
        -allowProvisioningUpdates \
        build install
        
    if [ $? -eq 0 ]; then
        echo "✅ Alternative deployment successful!"
    else
        echo "❌ All deployment methods failed. Please use Xcode manually."
        echo "🔧 Run: open ios/Runner.xcworkspace"
        exit 1
    fi
fi

echo ""
echo "🔄 To run with hot reload, use:"
echo "   flutter run -d \"$DEVICE_ID\" --release"
