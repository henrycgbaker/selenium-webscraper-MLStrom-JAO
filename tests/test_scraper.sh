#!/bin/bash
# Test script for JAO scraper

echo "Testing jao scraper with 2 days of data"
echo "will run in headed mode -> see what's happening."
echo ""

python main.py jao \
  --start-date 2024-11-19 \
  --end-date 2024-11-20 \
  --output-dir ./test_data \
  --verbose \
  --headed \
  --rate-limit 10

echo ""
echo "Test complete!"
echo " -> ./test_data for data."
echo " -> ./test_data/scraper_state.json for status."
