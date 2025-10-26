#!/usr/bin/env zsh
#
# test_network.zsh
# Test if systemctl --user has internet access

echo "Testing network access from systemctl --user..."

# Test HTTP request to a public API
if curl -s --max-time 10 https://httpbin.org/ip > /dev/null 2>&1; then
    echo "✅ Internet access OK"
    curl -s https://httpbin.org/ip
else
    echo "❌ No internet access"
fi

# Test HTTP request to Polygon API (demo endpoint)
if curl -s --max-time 10 "https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/2023-01-01/2023-01-02?apiKey=demo" > /dev/null 2>&1; then
    echo "✅ Polygon API access OK"
else
    echo "❌ Polygon API access failed"
fi