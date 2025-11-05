#!/bin/bash

# Test script for iMessage integration
# This script helps verify that the iMessage setup is working correctly

set -e

echo "🧪 Testing Alyn iMessage Integration"
echo "===================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check Node.js
echo "1️⃣  Checking Node.js installation..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓${NC} Node.js found: $NODE_VERSION"
else
    echo -e "${RED}✗${NC} Node.js not found. Please install Node.js first."
    exit 1
fi

echo ""

# Test 2: Check dependencies
echo "2️⃣  Checking npm dependencies..."
if [ -d "node_modules" ]; then
    if [ -d "node_modules/@photon-ai/imessage-kit" ]; then
        echo -e "${GREEN}✓${NC} imessage-kit installed"
    else
        echo -e "${RED}✗${NC} imessage-kit not found. Running npm install..."
        npm install
    fi
else
    echo -e "${YELLOW}!${NC} node_modules not found. Running npm install..."
    npm install
fi

echo ""

# Test 3: Check Python environment
echo "3️⃣  Checking Python environment..."
if [ -d ".venv" ]; then
    echo -e "${GREEN}✓${NC} Virtual environment found"

    # Check if we can import required modules
    .venv/bin/python -c "import sys; sys.path.insert(0, 'server'); from services.imessage import send_imessage" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Python imports working"
    else
        echo -e "${RED}✗${NC} Python imports failed. Check your Python setup."
    fi
else
    echo -e "${YELLOW}!${NC} Virtual environment not found at .venv"
fi

echo ""

# Test 4: Check file permissions
echo "4️⃣  Checking file permissions..."
if [ -x "start_imessage.sh" ]; then
    echo -e "${GREEN}✓${NC} start_imessage.sh is executable"
else
    echo -e "${YELLOW}!${NC} Making start_imessage.sh executable..."
    chmod +x start_imessage.sh
fi

if [ -x "server/services/imessage/imessage_watcher.js" ]; then
    echo -e "${GREEN}✓${NC} imessage_watcher.js is executable"
else
    echo -e "${YELLOW}!${NC} Making imessage_watcher.js executable..."
    chmod +x server/services/imessage/imessage_watcher.js
fi

echo ""

# Test 5: Prompt for send test
echo "5️⃣  Testing message send capability..."
echo ""
read -p "Enter a phone number or email to send a test message (or press Enter to skip): " RECIPIENT

if [ -n "$RECIPIENT" ]; then
    echo "Sending test message to $RECIPIENT..."
    node server/services/imessage/send_message.js "$RECIPIENT" "Test message from Alyn iMessage integration 🚀" 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Test message sent successfully!"
        echo "   Check your iMessage to verify it was received."
    else
        echo -e "${RED}✗${NC} Failed to send test message."
        echo ""
        echo -e "${YELLOW}Possible issues:${NC}"
        echo "   • Full Disk Access not granted to Terminal/IDE"
        echo "   • iMessage not configured on this Mac"
        echo "   • Invalid recipient address"
        echo ""
        echo "See IMESSAGE_SETUP.md for troubleshooting steps."
    fi
else
    echo -e "${YELLOW}!${NC} Skipping send test"
fi

echo ""
echo "===================================="
echo "✅ Setup check complete!"
echo ""
echo "📖 Next steps:"
echo "   1. Make sure Full Disk Access is granted (see IMESSAGE_SETUP.md)"
echo "   2. Start the watcher: ./start_imessage.sh"
echo "   3. Send an iMessage to this Mac to test"
echo ""
echo "📚 Documentation:"
echo "   • Quick start: IMESSAGE_SETUP.md"
echo "   • Detailed docs: server/services/imessage/README.md"
