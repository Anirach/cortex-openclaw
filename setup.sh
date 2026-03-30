#!/bin/bash
set -euo pipefail

echo "🧠 CORTEX + OpenClaw Setup"
echo "=========================="

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ npm is required but not installed."; exit 1; }

# Ensure cortex-memory is available
if [ ! -d "../cortex-memory/cortex" ]; then
    echo "⚠️  cortex-memory not found at ../cortex-memory/"
    echo "   Clone it: git clone https://github.com/Anirach/cortex-memory.git ../cortex-memory"
    exit 1
fi

# Copy cortex-memory for Docker build context
echo "📦 Preparing CORTEX source..."
if [ ! -d "./cortex-memory" ]; then
    cp -r ../cortex-memory ./cortex-memory
fi

# Build and start CORTEX server
echo "🐳 Building and starting CORTEX server..."
docker compose up -d --build

# Wait for health
echo "⏳ Waiting for CORTEX server..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8900/health > /dev/null 2>&1; then
        echo "✅ CORTEX server is healthy!"
        break
    fi
    sleep 1
done

# Build OpenClaw plugin
echo "🔧 Building OpenClaw plugin..."
cd plugin
npm install
npm run build
cd ..

echo ""
echo "✅ CORTEX + OpenClaw setup complete!"
echo ""
echo "Add to your openclaw.json:"
echo '  "plugins": {'
echo '    "slots": { "contextEngine": "cortex" },'
echo '    "entries": {'
echo '      "cortex-memory": {'
echo '        "enabled": true,'
echo '        "path": "./cortex-openclaw/plugin",'
echo '        "config": {'
echo '          "serverUrl": "http://localhost:8900",'
echo '          "autoConsolidate": true,'
echo '          "enablePromptAssembly": true'
echo '        }'
echo '      }'
echo '    }'
echo '  }'
echo ""
echo "Then restart OpenClaw to activate CORTEX memory."
