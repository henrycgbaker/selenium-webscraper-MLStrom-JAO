#!/bin/bash
# Test script for JAO scraper

echo "Testing JAO scraper with 2 days of data..."
echo "This will run in headed mode so you can see what's happening."
echo ""

python main.py jao \
  --start-date 2024-11-19 \
  --end-date 2024-11-20 \
  --output-dir ./test_data \
  --verbose \
  --headed \
  --rate-limit 10

echo ""
echo "Test complete! Check ./test_data for downloaded files."
echo "Check ./test_data/scraper_state.json for status."
