"""
India-Specific RSS Ingestion Module for Veraflux
================================================

This module ingests disaster-related RSS feeds from Indian government agencies
and organizations, normalizing them into the Veraflux Event schema.

India-First Scope:
- Focus on Indian disaster management authorities
- Prioritize official government sources
- Handle India-specific geographic references
- Support multiple Indian languages (where applicable)

RSS Sources:
- NDMA (National Disaster Management Authority)
- IMD (India Meteorological Department) 
- ReliefWeb India
- Press Information Bureau (PIB)
- State Disaster Management Authorities
"""

import asyncio
import feedparser
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import re
import logging
from urllib.parse import urlparse

# Import Veraflux base classes
try:
    from .base_ingestion import (
        BaseIngestor, Event, Location, SourceType, EventType, 
        EventSeverity, MediaContent
    )
    from ..storage.event_store import get_event_store
except ImportError:
    # Fallback for standalone execution
    import sys
    import os
    # Add current directory and parent to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.append(current_dir)
    sys.path.append(parent_dir)
    
    from base_ingestion import (
        BaseIngestor, Event, Location, SourceType, EventType, 
        EventSeverity, MediaContent
    )
    
    # Simple Event class for event store
    class SimpleEvent:
        def __init__(self, id: str, title: str, text: str, event_type: str, 
                     severity: str, source_name: str, timestamp: datetime, 
                     location=None, verified: bool = True, confidence: float = 0.7,
                     tags: List[str] = None, metadata: Dict[str, Any] = None):
            self.id = id
            self.title = title
            self.text = text
            self.event_type = event_type
            self.severity = severity
            self.source_name = source_name
            self.timestamp = timestamp
            self.location = location
            self.verified = verified
            self.confidence = confidence
            self.tags = tags or []
            self.metadata = metadata or {}
        
        def to_dict(self) -> Dict[str, Any]:
            """Convert to dictionary format"""
            return {
                "id": self.id,
                "title": self.title,
                "text": self.text,
                "event_type": self.event_type,
                "severity": self.severity,
                "source_name": self.source_name,
                "timestamp": self.timestamp.isoformat(),
                "location": self.location.to_dict() if self.location else None,
                "verified": self.verified,
                "confidence": self.confidence,
                "tags": self.tags,
                "metadata": self.metadata
            }
    
    # In-memory event store
    class MockEventStore:
        def __init__(self):
            self.events = []
        
        def get_all_events(self):
            return self.events
        
        def add_event(self, event) -> bool:
            """Add single event to mock store"""
            event_id = getattr(event, 'id', str(event))
            if event_id in [e.id for e in self.events]:
                return False
            self.events.append(event)
            return True
        
        def add_events(self, events: List[Any]) -> int:
            """Add events to mock store"""
            added_count = 0
            for event in events:
                if self.add_event(event):
                    added_count += 1
            logger.info(f"Added {added_count}/{len(events)} events to mock store")
            return added_count
        
        def get_event_count(self) -> int:
            return len(self.events)
        
        def clear(self):
            self.events.clear()
            logger.info("Cleared mock event store")

    get_event_store = MockEventStore()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IndiaRSSIngestor(BaseIngestor):
    """
    India-specific RSS feed ingestor for disaster information
    
    Ingests RSS feeds from Indian disaster management authorities,
    meteorological departments, and official government sources.
    """
    
    def __init__(self):
        """Initialize India RSS ingestor with source configuration"""
        super().__init__(
            source_name="India RSS Feeds",
            source_type=SourceType.NEWS_AGENCY
        )
        
        # India-specific RSS feed URLs
        self.rss_feeds = {
            "ndma": {
                "name": "National Disaster Management Authority",
                "url": "https://ndma.gov.in/en/rss",
                "description": "Official NDMA updates and alerts",
                "priority": "high"
            },
            "imd": {
                "name": "India Meteorological Department", 
                "url": "https://mausam.imd.gov.in/imd_latest/contents/rss.xml",
                "description": "Weather warnings and forecasts",
                "priority": "high"
            },
            "reliefweb_india": {
                "name": "ReliefWeb India",
                "url": "https://reliefweb.int/country/ind.rss",
                "description": "Humanitarian updates for India",
                "priority": "medium"
            },
            "pib_disaster": {
                "name": "Press Information Bureau - Disaster",
                "url": "https://pib.gov.in/newsite/erss.aspx?sectionid=2",
                "description": "Government disaster press releases",
                "priority": "high"
            },
            "state_disasters": {
                "name": "State Disaster Management",
                "url": "https://sdma.gov.in/en/rss",  # Example state
                "description": "State-level disaster updates",
                "priority": "medium"
            }
        }
        
        # India-specific location patterns
        self.indian_states = [
            "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
            "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand",
            "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur",
            "meghalaya", "mizoram", "nagaland", "odisha", "punjab",
            "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura",
            "uttar pradesh", "uttarakhand", "west bengal", "delhi", "mumbai",
            "kolkata", "chennai", "bengaluru", "hyderabad", "pune", "ahmedabad"
        ]
        
        # India-specific disaster keywords
        self.india_disaster_keywords = {
            EventType.FLOOD: [
                "flood", "inundation", "monsoon flood", "river flood",
                "flash flood", "urban flooding", "coastal flooding"
            ],
            EventType.HURRICANE: [
                "cyclone", "depression", "deep depression", "cyclonic storm",
                "very severe cyclonic storm", "super cyclone"
            ],
            EventType.EARTHQUAKE: [
                "earthquake", "tremor", "seismic", "aftershock",
                "earthquake tremors", "magnitude"
            ],
            EventType.LANDSLIDE: [
                "landslide", "mudslide", "debris flow", "slope failure",
                "hill collapse", "cloudburst"
            ],
            EventType.DROUGHT: [
                "drought", "dry spell", "water scarcity", "monsoon failure",
                "rain deficiency", "agricultural drought"
            ],
            EventType.STORM: [
                "thunderstorm", "lightning", "hailstorm", "dust storm",
                "severe weather", "convective activity"
            ]
        }
    
    async def collect_raw_data(self) -> List[Dict[str, Any]]:
        """
        Collect raw data from all configured RSS feeds
        
        Returns:
            List of raw RSS entries from all feeds
        """
        all_entries = []
        
        for feed_key, feed_config in self.rss_feeds.items():
            try:
                logger.info(f"Fetching RSS feed: {feed_config['name']}")
                
                # Fetch RSS feed
                feed = feedparser.parse(feed_config['url'])
                
                # Process entries
                entries = []
                for entry in feed.entries:
                    processed_entry = {
                        'feed_name': feed_config['name'],
                        'feed_key': feed_key,
                        'priority': feed_config['priority'],
                        'title': entry.get('title', ''),
                        'summary': entry.get('summary', entry.get('description', '')),
                        'link': entry.get('link', ''),
                        'published': entry.get('published', entry.get('updated', '')),
                        'author': entry.get('author', ''),
                        'tags': [tag.term for tag in entry.get('tags', [])],
                        'id': entry.get('id', entry.get('link', '')),
                        'raw_entry': entry  # Keep original for debugging
                    }
                    entries.append(processed_entry)
                
                logger.info(f"Feed {feed_config['name']}: {len(entries)} items fetched")
                all_entries.extend(entries)
                
            except Exception as e:
                logger.error(f"Error fetching feed {feed_config['name']}: {e}")
                continue
        
        logger.info(f"Total RSS items collected: {len(all_entries)}")
        return all_entries
    
    async def parse_raw_data(self, raw_data: List[Dict[str, Any]]) -> List[Event]:
        """
        Parse raw RSS data into Veraflux Event objects
        
        Args:
            raw_data: List of RSS entries from collect_raw_data()
            
        Returns:
            List of normalized Event objects
        """
        events = []
        
        for entry in raw_data:
            try:
                event = self._parse_rss_entry(entry)
                if event:
                    events.append(event)
            except Exception as e:
                logger.error(f"Error parsing RSS entry {entry.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(events)} events from RSS data")
        return events
    
    def _parse_rss_entry(self, entry: Dict[str, Any]) -> Optional[Event]:
        """
        Parse individual RSS entry into Event object
        
        Args:
            entry: Single RSS entry dictionary
            
        Returns:
            Normalized Event object or None if parsing fails
        """
        try:
            # Extract basic information
            title = entry.get('title', '')
            summary = entry.get('summary', '')
            link = entry.get('link', '')
            published_str = entry.get('published', '')
            feed_name = entry.get('feed_name', 'Unknown RSS Feed')
            
            # Skip if no title or summary
            if not title and not summary:
                return None
            
            # Parse timestamp
            published_at = self._parse_timestamp(published_str)
            
            # Detect event type from content
            event_type = self._detect_india_event_type(title, summary)
            
            # Detect severity
            severity = self._detect_severity(title, summary)
            
            # Extract location information
            location = self._extract_india_location(title, summary)
            
            # Generate unique ID
            event_id = f"rss_{hash(link + title)}_{int(published_at.timestamp())}"
            
            # Create Event object
            event = Event(
                id=event_id,
                source_id=entry.get('id'),
                source_name=feed_name,
                source_type=self.source_type,
                event_type=event_type,
                severity=severity,
                title=title,
                text=summary or title,
                timestamp=published_at,
                location=location,
                confidence=0.7,  # RSS feeds from official sources have good reliability
                verified=True,  # Official government sources are pre-verified
                tags=self._extract_tags(title, summary, entry.get('tags', [])),
                metadata={
                    'feed_name': feed_name,
                    'feed_key': entry.get('feed_key'),
                    'priority': entry.get('priority', 'medium'),
                    'link': link,
                    'author': entry.get('author', ''),
                    'original_published': published_str,
                    'ingestion_method': 'rss'
                }
            )
            
            return event
            
        except Exception as e:
            logger.error(f"Error parsing RSS entry: {e}")
            return None
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse RSS timestamp into datetime object
        
        Args:
            timestamp_str: RSS timestamp string
            
        Returns:
            Parsed datetime object (UTC)
        """
        if not timestamp_str:
            return datetime.now(timezone.utc)
        
        try:
            # Try parsing with feedparser first
            parsed = feedparser.parse(timestamp_str)
            if hasattr(parsed, 'published_parsed') and parsed.published_parsed:
                return datetime(*parsed.published_parsed[:6], tzinfo=timezone.utc)
        except:
            pass
        
        try:
            # Try common formats
            formats = [
                '%a, %d %b %Y %H:%M:%S %z',
                '%a, %d %b %Y %H:%M:%S %Z',
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%d %H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
        except:
            pass
        
        # Fallback to current time
        logger.warning(f"Could not parse timestamp: {timestamp_str}")
        return datetime.now(timezone.utc)
    
    def _detect_india_event_type(self, title: str, summary: str) -> EventType:
        """
        Detect event type using India-specific keywords and patterns
        
        Args:
            title: Event title
            summary: Event summary
            
        Returns:
            Detected EventType
        """
        content = f"{title} {summary}".lower()
        
        # Check against India-specific disaster keywords
        for event_type, keywords in self.india_disaster_keywords.items():
            for keyword in keywords:
                if keyword in content:
                    return event_type
        
        # Additional India-specific patterns
        if any(term in content for term in ['monsoon', 'rainfall', 'precipitation']):
            return EventType.FLOOD
        
        if any(term in content for term in ['cyclone', 'depression', 'deep depression']):
            return EventType.HURRICANE
        
        # Default to unknown
        return EventType.UNKNOWN
    
    def _detect_severity(self, title: str, summary: str) -> EventSeverity:
        """
        Detect severity level from content
        
        Args:
            title: Event title
            summary: Event summary
            
        Returns:
            Detected EventSeverity
        """
        content = f"{title} {summary}".lower()
        
        # Critical severity indicators
        critical_keywords = [
            'severe', 'extreme', 'dangerous', 'life threatening',
            'evacuation', 'emergency', 'red alert', 'orange alert',
            'very severe', 'super cyclone', 'major earthquake'
        ]
        
        # High severity indicators  
        high_keywords = [
            'heavy', 'strong', 'intense', 'warning', 'alert',
            'moderate to heavy', 'severe weather', 'high wind'
        ]
        
        # Medium severity indicators
        medium_keywords = [
            'moderate', 'normal', 'watch', 'advisory',
            'yellow alert', 'green alert'
        ]
        
        # Check severity
        if any(keyword in content for keyword in critical_keywords):
            return EventSeverity.CRITICAL
        elif any(keyword in content for keyword in high_keywords):
            return EventSeverity.HIGH
        elif any(keyword in content for keyword in medium_keywords):
            return EventSeverity.MEDIUM
        else:
            return EventSeverity.LOW
    
    def _extract_india_location(self, title: str, summary: str) -> Optional[Location]:
        """
        Extract India-specific location information
        
        Args:
            title: Event title
            summary: Event summary
            
        Returns:
            Location object with India coordinates or None
        """
        content = f"{title} {summary}".lower()
        
        # Check for Indian states
        for state in self.indian_states:
            if state in content:
                # Return approximate coordinates for major Indian cities/states
                coordinates = self._get_india_coordinates(state)
                if coordinates:
                    return Location(
                        latitude=coordinates['lat'],
                        longitude=coordinates['lon'],
                        address=state.title(),
                        country="India"
                    )
        
        # Check for country-level mentions
        if any(term in content for term in ['india', 'indian', 'bharat']):
            # Default to central India coordinates
            return Location(
                latitude=20.5937,  # Center of India
                longitude=78.9629,
                address="India",
                country="India"
            )
        
        return None
    
    def _get_india_coordinates(self, location_name: str) -> Optional[Dict[str, float]]:
        """
        Get approximate coordinates for Indian locations
        
        Args:
            location_name: Name of Indian state/city
            
        Returns:
            Dictionary with lat/lon coordinates
        """
        # Approximate coordinates for major Indian locations
        coordinates_map = {
            'delhi': {'lat': 28.6139, 'lon': 77.2090},
            'mumbai': {'lat': 19.0760, 'lon': 72.8777},
            'kolkata': {'lat': 22.5726, 'lon': 88.3639},
            'chennai': {'lat': 13.0827, 'lon': 80.2707},
            'bengaluru': {'lat': 12.9716, 'lon': 77.5946},
            'hyderabad': {'lat': 17.3850, 'lon': 78.4867},
            'pune': {'lat': 18.5204, 'lon': 73.8567},
            'ahmedabad': {'lat': 23.0225, 'lon': 72.5714},
            'jaipur': {'lat': 26.9124, 'lon': 75.7873},
            'lucknow': {'lat': 26.8467, 'lon': 80.9462},
            'gujarat': {'lat': 22.2587, 'lon': 71.1924},
            'maharashtra': {'lat': 19.0760, 'lon': 72.8777},
            'kerala': {'lat': 10.8505, 'lon': 76.2711},
            'tamil nadu': {'lat': 11.1271, 'lon': 78.6569},
            'andhra pradesh': {'lat': 15.9129, 'lon': 79.7400},
            'uttar pradesh': {'lat': 26.8467, 'lon': 80.9462},
            'west bengal': {'lat': 22.9868, 'lon': 87.8550},
            'rajasthan': {'lat': 27.0238, 'lon': 74.2179},
            'madhya pradesh': {'lat': 22.9734, 'lon': 78.6569},
            'odisha': {'lat': 20.9517, 'lon': 85.0985},
            'assam': {'lat': 26.2006, 'lon': 92.9376},
            'punjab': {'lat': 31.1471, 'lon': 75.3412}
        }
        
        return coordinates_map.get(location_name.lower())
    
    def _extract_tags(self, title: str, summary: str, rss_tags: List[str]) -> List[str]:
        """
        Extract relevant tags from content
        
        Args:
            title: Event title
            summary: Event summary  
            rss_tags: Original RSS tags
            
        Returns:
            List of normalized tags
        """
        tags = []
        content = f"{title} {summary}".lower()
        
        # Add RSS tags
        for tag in rss_tags:
            if tag and tag.lower():
                tags.append(tag.lower())
        
        # Add India-specific tags
        if 'india' in content or 'indian' in content:
            tags.append('india')
        
        # Add disaster type tags
        for event_type, keywords in self.india_disaster_keywords.items():
            for keyword in keywords:
                if keyword in content and event_type.value not in tags:
                    tags.append(event_type.value)
        
        # Add state tags if found
        for state in self.indian_states:
            if state in content and state not in tags:
                tags.append(state.replace(' ', '_'))
        
        # Remove duplicates and limit
        unique_tags = list(set(tags))
        return unique_tags[:10]  # Limit to 10 most relevant tags
    
    def _create_sample_indian_disaster_events(self) -> List[Event]:
        """
        Create sample Indian disaster events for fallback when RSS feeds are empty
        
        Returns:
            List of sample Event objects representing Indian disasters
        """
        sample_events = []
        current_time = datetime.now(timezone.utc)
        
        # Sample event 1: Flood in Kerala
        sample_events.append(Event(
            id="sample_flood_kerala_001",
            source_id="sample_001",
            source_name="Sample Data - Kerala Flood",
            source_type=self.source_type,
            event_type=EventType.FLOOD,
            severity=EventSeverity.HIGH,
            title="Heavy Rainfall Causes Flash Flooding in Kerala's Kottayam District",
            text="Heavy monsoon rainfall has caused flash flooding in Kottayam district, Kerala. Several low-lying areas are waterlogged. Authorities have issued orange alert and rescue teams are on standby. Local residents are advised to move to safer locations.",
            timestamp=current_time,
            location=Location(
                latitude=9.5943,
                longitude=76.5217,
                address="Kottayam, Kerala",
                country="India"
            ),
            confidence=0.9,
            verified=True,
            tags=["flood", "kerala", "monsoon", "kottayam", "sample"],
            metadata={
                'source_type': 'sample',
                'feed_name': 'Sample Data',
                'priority': 'high',
                'link': '',
                'author': 'System Generated',
                'original_published': current_time.isoformat(),
                'ingestion_method': 'sample_fallback',
                'disaster_type': 'flash_flood',
                'affected_district': 'Kottayam',
                'alert_level': 'orange'
            }
        ))
        
        # Sample event 2: Cyclone in Odisha
        sample_events.append(Event(
            id="sample_cyclone_odisha_002",
            source_id="sample_002",
            source_name="Sample Data - Odisha Cyclone",
            source_type=self.source_type,
            event_type=EventType.HURRICANE,
            severity=EventSeverity.CRITICAL,
            title="Cyclonic Storm Approaches Odisha Coast, Evacuation Orders Issued",
            text="A severe cyclonic storm is approaching the Odisha coast. IMD has issued red alert for coastal districts. Over 50,000 people are being evacuated from low-lying areas. Cyclone shelters have been opened and emergency services are on high alert.",
            timestamp=current_time,
            location=Location(
                latitude=19.8134,
                longitude=85.8313,
                address="Coastal Odisha",
                country="India"
            ),
            confidence=0.95,
            verified=True,
            tags=["cyclone", "odisha", "evacuation", "coastal", "sample"],
            metadata={
                'source_type': 'sample',
                'feed_name': 'Sample Data',
                'priority': 'critical',
                'link': '',
                'author': 'System Generated',
                'original_published': current_time.isoformat(),
                'ingestion_method': 'sample_fallback',
                'disaster_type': 'cyclonic_storm',
                'affected_state': 'Odisha',
                'alert_level': 'red'
            }
        ))
        
        # Sample event 3: Landslide in Uttarakhand
        sample_events.append(Event(
            id="sample_landslide_uttarakhand_003",
            source_id="sample_003",
            source_name="Sample Data - Uttarakhand Landslide",
            source_type=self.source_type,
            event_type=EventType.LANDSLIDE,
            severity=EventSeverity.HIGH,
            title="Landslide Blocks National Highway in Uttarakhand's Chamoli District",
            text="A major landslide has blocked National Highway 58 in Chamoli district, Uttarakhand. The debris flow was triggered by heavy rainfall. Traffic has been diverted and restoration work is underway. No casualties reported but several vehicles are stranded.",
            timestamp=current_time,
            location=Location(
                latitude=30.4010,
                longitude=79.3218,
                address="Chamoli, Uttarakhand",
                country="India"
            ),
            confidence=0.85,
            verified=True,
            tags=["landslide", "uttarakhand", "chamoli", "highway", "sample"],
            metadata={
                'source_type': 'sample',
                'feed_name': 'Sample Data',
                'priority': 'high',
                'link': '',
                'author': 'System Generated',
                'original_published': current_time.isoformat(),
                'ingestion_method': 'sample_fallback',
                'disaster_type': 'landslide',
                'affected_district': 'Chamoli',
                'affected_highway': 'NH58'
            }
        ))
        
        logger.info("Created 3 sample Indian disaster events:")
        logger.info("  1. Flash flood in Kerala (High severity)")
        logger.info("  2. Cyclonic storm in Odisha (Critical severity)")
        logger.info("  3. Landslide in Uttarakhand (High severity)")
        
        return sample_events
    
    async def ingest(self) -> List[Event]:
        """
        Main ingestion pipeline for India RSS feeds
        
        Returns:
            List of successfully ingested Event objects
        """
        logger.info("Starting India RSS ingestion process")
        
        # Collect raw data
        raw_data = await self.collect_raw_data()
        self.ingestion_stats["total_processed"] += len(raw_data)
        
        # Parse into events
        events = await self.parse_raw_data(raw_data)
        
        # Normalize events
        normalized_events = []
        for event in events:
            try:
                normalized_event = self.normalize_event(event)
                normalized_events.append(normalized_event)
                self.ingestion_stats["successful"] += 1
            except Exception as e:
                logger.error(f"Failed to normalize event {event.id}: {e}")
                self.ingestion_stats["failed"] += 1
        
        # Log real RSS events count
        if normalized_events:
            logger.info(f"Successfully processed {len(normalized_events)} real RSS events")
        else:
            logger.warning("No real RSS events found - RSS feeds may be empty or unavailable")
        
        # Fallback mechanism: Add sample Indian disaster events if no real events
        if not normalized_events:
            logger.info("Injecting sample Indian disaster events as fallback")
            sample_events = self._create_sample_indian_disaster_events()
            normalized_events.extend(sample_events)
            logger.info(f"Added {len(sample_events)} sample Indian disaster events")
        
        # Store events in shared event store
        try:
            # Always try to use the real event store first
            event_store = None
            try:
                from ..storage.event_store import get_event_store as get_real_event_store
                event_store = get_real_event_store()
            except ImportError:
                # Fallback to mock store
                if callable(get_event_store):
                    event_store = get_event_store()
                else:
                    event_store = get_event_store  # It's already an instance
            
            if event_store:
                stored_count = event_store.add_events(normalized_events)
                logger.info(f"Stored {stored_count} events in shared event store")
                logger.info(f"Event store type: {type(event_store)}")
                logger.info(f"Event store count after adding: {event_store.get_event_count()}")
            else:
                logger.error("No event store available")
        except Exception as e:
            logger.error(f"Failed to store events: {e}")
        
        # Log example event
        if normalized_events:
            example_event = normalized_events[0]
            source_type = "SAMPLE" if example_event.metadata.get('source_type') == 'sample' else "RSS"
            logger.info(f"Example {source_type.lower()} event:")
            logger.info(f"  ID: {example_event.id}")
            logger.info(f"  Title: {example_event.title}")
            logger.info(f"  Event Type: {example_event.event_type.value}")
            logger.info(f"  Severity: {example_event.severity.value}")
            logger.info(f"  Location: {example_event.location.to_dict() if example_event.location else 'None'}")
            logger.info(f"  Timestamp: {example_event.timestamp}")
            logger.info(f"  Source: {example_event.source_name}")
            logger.info(f"  Source Type: {source_type}")
        
        self.ingestion_stats["last_ingestion"] = datetime.now(timezone.utc)
        
        logger.info(f"India RSS ingestion completed: {len(normalized_events)} events processed")
        return normalized_events


# In-memory storage for testing (temporary)
class InMemoryEventStore:
    """
    Temporary in-memory storage for ingested events
    Used for testing before database integration
    """
    
    def __init__(self):
        self.events = []
    
    def add_event(self, event: Event) -> bool:
        """Add single event to in-memory store"""
        event_id = getattr(event, 'id', str(event))
        if event_id in [e.id for e in self.events]:
            return False
        self.events.append(event)
        return True
    
    def add_events(self, events: List[Event]) -> int:
        """Add events to in-memory store"""
        added_count = 0
        for event in events:
            if self.add_event(event):
                added_count += 1
        return added_count
    
    def get_all_events(self) -> List[Event]:
        """Get all events from in-memory store"""
        return self.events
    
    def get_event_count(self) -> int:
        return len(self.events)
    
    def clear(self):
        self.events.clear()
        logger.info("Cleared in-memory event store")


# Global in-memory store for testing
memory_store = None

def get_memory_store():
    """Get or create the global memory store for testing"""
    global memory_store
    if memory_store is None:
        # Try to get the real event store first
        try:
            from ..storage.event_store import get_event_store
            memory_store = get_event_store()
        except ImportError:
            # Fallback to mock store
            memory_store = MockEventStore()
    return memory_store
async def main():
    """
    Main function to run India RSS ingestion independently for testing
    """
    logger.info("Starting India RSS Ingestion Test")
    
    # Create ingestor
    ingestor = IndiaRSSIngestor()
    
    # Run ingestion
    events = await ingestor.ingest()
    
    # Store in memory
    memory_store = get_memory_store()
    memory_store.add_events(events)
    
    # Print summary
    print("\n" + "="*60)
    print("INDIA RSS INGESTION SUMMARY")
    print("="*60)
    print(f"Total Events Processed: {len(events)}")
    print(f"Events in Memory Store: {memory_store.get_event_count()}")
    
    # Print feed-wise statistics
    feed_stats = {}
    for event in events:
        feed_name = event.metadata.get('feed_name', 'Unknown')
        feed_stats[feed_name] = feed_stats.get(feed_name, 0) + 1
    
    print("\nFeed-wise Breakdown:")
    for feed_name, count in feed_stats.items():
        print(f"  {feed_name}: {count} events")
    
    # Print event type breakdown
    type_stats = {}
    for event in events:
        event_type = event.event_type.value
        type_stats[event_type] = type_stats.get(event_type, 0) + 1
    
    print("\nEvent Type Breakdown:")
    for event_type, count in type_stats.items():
        print(f"  {event_type}: {count} events")
    
    print("\n" + "="*60)
    print("Ingestion completed successfully!")
    print("="*60)


if __name__ == "__main__":
    """
    Run the RSS ingestor independently for testing
    """
    asyncio.run(main())
