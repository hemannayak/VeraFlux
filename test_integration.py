#!/usr/bin/env python3
"""
Test script to verify RSS ingestion -> event store integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.ingestion.rss_ingestor import IndiaRSSIngestor
from backend.storage.event_store import get_event_store
import asyncio

async def test_integration():
    """Test the complete RSS ingestion to event store pipeline"""
    print("Testing RSS ingestion -> event store integration...")
    
    # Get the shared event store
    event_store = get_event_store()
    print(f"Initial event count: {event_store.get_event_count()}")
    
    # Run RSS ingestion
    ingestor = IndiaRSSIngestor()
    events = await ingestor.ingest()
    
    # Check events in store
    final_count = event_store.get_event_count()
    print(f"Final event count: {final_count}")
    
    # Get all events and display
    all_events = event_store.get_all_events()
    print(f"\nEvents in store:")
    for i, event in enumerate(all_events, 1):
        source_type = "SAMPLE" if event.metadata.get('source_type') == 'sample' else "RSS"
        print(f"{i}. [{source_type}] {event.title}")
        print(f"   Type: {event.event_type.value}, Severity: {event.severity.value}")
        print(f"   Location: {event.location.address if event.location else 'None'}")
        print()
    
    return len(all_events) > 0

if __name__ == "__main__":
    success = asyncio.run(test_integration())
    if success:
        print("✅ Integration test PASSED - Events are properly stored")
    else:
        print("❌ Integration test FAILED - No events found in store")
    sys.exit(0 if success else 1)
