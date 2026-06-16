"""
Base Ingestion Module
Foundation for all data ingestion modules in Veraflux

This module defines the core data structures and base classes that all
ingestion modules should inherit from. It provides a standardized way
to handle disaster events from various sources with consistent formatting.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
import re


class EventSeverity(Enum):
    """Standardized severity levels for disaster events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(Enum):
    """Standardized event types for disaster classification"""
    EARTHQUAKE = "earthquake"
    FLOOD = "flood"
    HURRICANE = "hurricane"
    TORNADO = "tornado"
    WILDFIRE = "wildfire"
    TSUNAMI = "tsunami"
    VOLCANO = "volcano"
    LANDSLIDE = "landslide"
    DROUGHT = "drought"
    STORM = "storm"
    UNKNOWN = "unknown"


class IncidentType(Enum):
    """Incident types for early classification and emergency response"""
    FIRE = "fire"
    ROAD_ACCIDENT = "road_accident"
    MEDICAL = "medical"
    NATURAL_HAZARD = "natural_hazard"
    LAW_AND_ORDER = "law_and_order"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"


class Priority(Enum):
    """Priority levels for incident response"""
    P1 = "P1"  # Critical - Immediate response required
    P2 = "P2"  # High - Response within 1 hour
    P3 = "P3"  # Medium - Response within 4 hours


class VerificationStatus(Enum):
    """Verification status for incident reports"""
    UNVERIFIED = "unverified"
    PARTIALLY_VERIFIED = "partially_verified"
    VERIFIED = "verified"


class SourceType(Enum):
    """Standardized source types for data provenance"""
    SOCIAL_MEDIA = "social_media"
    NEWS_AGENCY = "news_agency"
    GOVERNMENT = "government"
    EMERGENCY_SERVICES = "emergency_services"
    SENSOR_NETWORK = "sensor_network"
    SATELLITE = "satellite"
    EYEWITNESS = "eyewitness"
    OFFICIAL_REPORT = "official_report"
    UNKNOWN = "unknown"


@dataclass
class Location:
    """
    Standardized location representation
    
    Provides a consistent way to represent geographic locations across
    all data sources with support for multiple coordinate formats.
    """
    
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy: Optional[float] = None  # Accuracy in meters
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    
    def __post_init__(self):
        """Validate coordinates after initialization"""
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {self.longitude}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "lat": self.latitude,
            "lon": self.longitude,
            "alt": self.altitude,
            "accuracy": self.accuracy,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "timezone": self.timezone
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Location":
        """Create Location from dictionary"""
        # Handle different coordinate naming conventions
        lat = data.get("lat") or data.get("latitude") or data.get("lat")
        lon = data.get("lon") or data.get("longitude") or data.get("lng")
        
        if lat is None or lon is None:
            raise ValueError("Location must contain latitude and longitude")
        
        return cls(
            latitude=float(lat),
            longitude=float(lon),
            altitude=data.get("alt") or data.get("altitude"),
            accuracy=data.get("accuracy"),
            address=data.get("address"),
            city=data.get("city"),
            state=data.get("state"),
            country=data.get("country"),
            timezone=data.get("timezone")
        )


@dataclass
class MediaContent:
    """
    Standardized media content representation
    
    Handles various types of media content associated with disaster events
    including images, videos, and audio files.
    """
    
    url: str
    media_type: str  # image, video, audio
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None  # For video/audio
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "url": self.url,
            "media_type": self.media_type,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "width": self.width,
            "height": self.height,
            "duration_seconds": self.duration_seconds,
            "description": self.description,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MediaContent":
        """Create MediaContent from dictionary"""
        return cls(
            url=data["url"],
            media_type=data["media_type"],
            mime_type=data.get("mime_type"),
            size_bytes=data.get("size_bytes"),
            width=data.get("width"),
            height=data.get("height"),
            duration_seconds=data.get("duration_seconds"),
            description=data.get("description"),
            metadata=data.get("metadata", {})
        )


@dataclass
class Event:
    """
    Normalized disaster event schema
    
    This is the core data structure that all ingestion modules should
    produce. It provides a consistent format for disaster events
    regardless of the source.
    """
    
    # Core identification
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: Optional[str] = None  # Original ID from source system
    source_type: SourceType = SourceType.UNKNOWN
    source_name: str = "unknown"
    
    # Event classification
    event_type: EventType = EventType.UNKNOWN
    incident_type: IncidentType = IncidentType.UNKNOWN
    severity: EventSeverity = EventSeverity.MEDIUM
    priority: Priority = Priority.P3
    title: Optional[str] = None
    text: str = ""
    
    # Verification and response
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    recommended_services: List[str] = field(default_factory=list)
    
    # Temporal information
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reported_at: Optional[datetime] = None  # When the event was reported
    
    # Geographic information
    location: Optional[Location] = None
    
    # Media content
    media: List[MediaContent] = field(default_factory=list)
    
    # Metadata and provenance
    confidence: float = 0.0  # Confidence score (0.0-1.0)
    verified: bool = False
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Processing information
    ingested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processing_status: str = "pending"  # pending, processing, completed, failed
    
    def __post_init__(self):
        """Validate event data after initialization"""
        if not self.text and not self.title:
            raise ValueError("Event must have either text or title")
        
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for storage and API responses"""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "source_name": self.source_name,
            "event_type": self.event_type.value,
            "incident_type": self.incident_type.value,
            "severity": self.severity.value,
            "priority": self.priority.value,
            "title": self.title,
            "text": self.text,
            "verification_status": self.verification_status.value,
            "recommended_services": self.recommended_services,
            "timestamp": self.timestamp.isoformat(),
            "reported_at": self.reported_at.isoformat() if self.reported_at else None,
            "location": self.location.to_dict() if self.location else None,
            "media": [media.to_dict() for media in self.media],
            "confidence": self.confidence,
            "verified": self.verified,
            "tags": self.tags,
            "metadata": self.metadata,
            "ingested_at": self.ingested_at.isoformat(),
            "processing_status": self.processing_status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create Event from dictionary"""
        # Parse timestamps
        timestamp = datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(timezone.utc)
        reported_at = datetime.fromisoformat(data["reported_at"]) if data.get("reported_at") else None
        ingested_at = datetime.fromisoformat(data["ingested_at"]) if data.get("ingested_at") else datetime.now(timezone.utc)
        
        # Parse location
        location = None
        if data.get("location"):
            location = Location.from_dict(data["location"])
        
        # Parse media
        media = []
        for media_data in data.get("media", []):
            media.append(MediaContent.from_dict(media_data))
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            source_id=data.get("source_id"),
            source_type=SourceType(data.get("source_type", "unknown")),
            source_name=data.get("source_name", "unknown"),
            event_type=EventType(data.get("event_type", "unknown")),
            incident_type=IncidentType(data.get("incident_type", "unknown")),
            severity=EventSeverity(data.get("severity", "medium")),
            priority=Priority(data.get("priority", "P3")),
            title=data.get("title"),
            text=data.get("text", ""),
            verification_status=VerificationStatus(data.get("verification_status", "unverified")),
            recommended_services=data.get("recommended_services", []),
            timestamp=timestamp,
            reported_at=reported_at,
            location=location,
            media=media,
            confidence=data.get("confidence", 0.0),
            verified=data.get("verified", False),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            ingested_at=ingested_at,
            processing_status=data.get("processing_status", "pending")
        )


class BaseIngestor(ABC):
    """
    Base class for all data ingestion modules
    
    This abstract class defines the interface that all ingestion modules
    must implement. It provides common functionality for event
    normalization and processing.
    """
    
    def __init__(self, source_name: str, source_type: SourceType):
        """
        Initialize the base ingestor
        
        Args:
            source_name: Human-readable name of the data source
            source_type: Type of data source (social_media, news, etc.)
        """
        self.source_name = source_name
        self.source_type = source_type
        self.ingestion_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "last_ingestion": None
        }
    
    @abstractmethod
    async def collect_raw_data(self) -> List[Dict[str, Any]]:
        """
        Collect raw data from the source
        
        This method must be implemented by each ingestor to fetch
        data from their specific source (API, database, file, etc.)
        
        Returns:
            List of raw data items from the source
        """
        pass
    
    @abstractmethod
    async def parse_raw_data(self, raw_data: List[Dict[str, Any]]) -> List[Event]:
        """
        Parse raw data into Event objects
        
        This method must be implemented by each ingestor to convert
        their source-specific data format into standardized Event objects.
        
        Args:
            raw_data: Raw data collected from the source
            
        Returns:
            List of normalized Event objects
        """
        pass
    
    async def ingest(self) -> List[Event]:
        """
        Main ingestion pipeline
        
        Orchestrates the complete ingestion process from data collection
        to normalization and returns the final Event objects.
        
        Returns:
            List of successfully ingested Event objects
        """
        try:
            # Collect raw data
            raw_data = await self.collect_raw_data()
            self.ingestion_stats["total_processed"] += len(raw_data)
            
            # Parse and normalize events
            events = await self.parse_raw_data(raw_data)
            
            # Normalize events
            normalized_events = []
            for event in events:
                try:
                    normalized_event = self.normalize_event(event)
                    normalized_events.append(normalized_event)
                    self.ingestion_stats["successful"] += 1
                except Exception as e:
                    print(f"Failed to normalize event {event.id}: {e}")
                    self.ingestion_stats["failed"] += 1
            
            self.ingestion_stats["last_ingestion"] = datetime.now(timezone.utc)
            return normalized_events
            
        except Exception as e:
            print(f"Ingestion failed for {self.source_name}: {e}")
            self.ingestion_stats["failed"] += 1
            return []
    
    def normalize_event(self, event: Event) -> Event:
        """
        Normalize and validate an event
        
        Applies standard normalization rules to ensure consistency
        across all data sources. This method can be overridden by
        subclasses to add source-specific normalization logic.
        
        Args:
            event: Event to normalize
            
        Returns:
            Normalized Event object
        """
        # Set source information
        event.source_name = self.source_name
        event.source_type = self.source_type
        
        # Normalize text content
        if event.text:
            event.text = self.normalize_text(event.text)
        
        # Normalize title
        if event.title:
            event.title = self.normalize_text(event.title)
        
        # Extract and normalize event type
        if event.event_type == EventType.UNKNOWN:
            event.event_type = self.detect_event_type(event.text, event.title)
        
        # Normalize severity
        if event.severity == EventSeverity.MEDIUM and event.text:
            event.severity = self.detect_severity(event.text)
        
        # Extract tags from content
        if not event.tags:
            event.tags = self.extract_tags(event.text, event.title)
        
        # Validate confidence score
        event.confidence = max(0.0, min(1.0, event.confidence))
        
        return event
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text content
        
        Applies standard text normalization including whitespace cleanup,
        character encoding fixes, and basic sanitization.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text string
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common problematic characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        return text.strip()
    
    def detect_event_type(self, text: str, title: str = None) -> EventType:
        """
        Detect event type from text content
        
        Uses keyword matching to determine the type of disaster event.
        This is a simple implementation that can be enhanced with
        machine learning models.
        
        Args:
            text: Event text content
            title: Event title (optional)
            
        Returns:
            Detected EventType
        """
        content = f"{title or ''} {text}".lower()
        
        # Define keyword patterns for each event type
        event_keywords = {
            EventType.EARTHQUAKE: [
                'earthquake', 'quake', 'tremor', 'seismic', 'aftershock',
                'magnitude', 'richter', 'epicenter'
            ],
            EventType.FLOOD: [
                'flood', 'flooding', 'inundation', 'overflow', 'flash flood',
                'water level', 'river overflow', 'dam break'
            ],
            EventType.HURRICANE: [
                'hurricane', 'typhoon', 'cyclone', 'storm surge',
                'tropical storm', 'eye wall', 'wind speed'
            ],
            EventType.TORNADO: [
                'tornado', 'twister', 'funnel cloud', 'touchdown',
                'supercell', 'debris cloud'
            ],
            EventType.WILDFIRE: [
                'wildfire', 'forest fire', 'bushfire', 'brush fire',
                'wildfire', 'burning', 'evacuation', 'smoke'
            ],
            EventType.TSUNAMI: [
                'tsunami', 'tidal wave', 'seismic sea wave',
                'ocean surge', 'coastal flooding'
            ],
            EventType.VOLCANO: [
                'volcano', 'volcanic', 'eruption', 'lava',
                'ash cloud', 'pyroclastic'
            ],
            EventType.LANDSLIDE: [
                'landslide', 'mudslide', 'rockslide', 'debris flow',
                'slope failure', 'hill collapse'
            ],
            EventType.DROUGHT: [
                'drought', 'dry spell', 'water shortage',
                'famine', 'crop failure'
            ],
            EventType.STORM: [
                'storm', 'thunderstorm', 'lightning', 'hail',
                'severe weather', 'wind damage'
            ]
        }
        
        # Count keyword matches for each event type
        event_scores = {}
        for event_type, keywords in event_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content)
            if score > 0:
                event_scores[event_type] = score
        
        # Return event type with highest score
        if event_scores:
            return max(event_scores, key=event_scores.get)
        
        return EventType.UNKNOWN
    
    def detect_severity(self, text: str) -> EventSeverity:
        """
        Detect severity level from text content
        
        Uses keyword analysis to determine the severity of an event.
        This is a simple heuristic approach that can be enhanced.
        
        Args:
            text: Event text content
            
        Returns:
            Detected EventSeverity
        """
        text_lower = text.lower()
        
        # Define severity keywords
        severity_keywords = {
            EventSeverity.CRITICAL: [
                'catastrophic', 'devastating', 'mass casualties', 'multiple deaths',
                'complete destruction', 'unprecedented', 'emergency', 'critical'
            ],
            EventSeverity.HIGH: [
                'major', 'severe', 'significant', 'injuries', 'deaths',
                'widespread damage', 'evacuation', 'dangerous'
            ],
            EventSeverity.MEDIUM: [
                'moderate', 'some damage', 'minor injuries', 'disruption',
                'warning', 'watch', 'advisory'
            ],
            EventSeverity.LOW: [
                'minor', 'small', 'limited', 'no injuries', 'monitoring',
                'observation', 'report'
            ]
        }
        
        # Calculate severity scores
        severity_scores = {}
        for severity, keywords in severity_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                severity_scores[severity] = score
        
        # Return severity with highest score
        if severity_scores:
            return max(severity_scores, key=severity_scores.get)
        
        return EventSeverity.MEDIUM
    
    def extract_tags(self, text: str, title: str = None) -> List[str]:
        """
        Extract relevant tags from content
        
        Extracts keywords and hashtags that can be used for categorization
        and search functionality.
        
        Args:
            text: Event text content
            title: Event title (optional)
            
        Returns:
            List of extracted tags
        """
        content = f"{title or ''} {text}".lower()
        tags = []
        
        # Extract hashtags
        hashtags = re.findall(r'#(\w+)', content)
        tags.extend(hashtags)
        
        # Extract common disaster-related keywords
        disaster_keywords = [
            'emergency', 'disaster', 'alert', 'warning', 'evacuation',
            'rescue', 'damage', 'injury', 'casualty', 'safety',
            'response', 'recovery', 'aid', 'shelter', 'power outage'
        ]
        
        for keyword in disaster_keywords:
            if keyword in content and keyword not in tags:
                tags.append(keyword)
        
        # Extract location indicators
        location_patterns = [
            r'\b(\w+city)\b', r'\b(\w+county)\b', r'\b(\w+state)\b',
            r'\b(\w+area)\b', r'\b(\w+region)\b'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, content)
            tags.extend(matches)
        
        # Remove duplicates and limit to reasonable number
        unique_tags = list(set(tags))
        return unique_tags[:10]  # Limit to 10 most relevant tags
    
    def get_ingestion_stats(self) -> Dict[str, Any]:
        """
        Get ingestion statistics
        
        Returns:
            Dictionary containing ingestion performance metrics
        """
        return {
            "source_name": self.source_name,
            "source_type": self.source_type.value,
            **self.ingestion_stats
        }
    
    def reset_stats(self):
        """Reset ingestion statistics"""
        self.ingestion_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "last_ingestion": None
        }


# Utility functions for common ingestion tasks

def create_event_from_raw(
    source_id: str,
    source_name: str,
    source_type: SourceType,
    text: str,
    title: str = None,
    location: Location = None,
    media_urls: List[str] = None,
    timestamp: datetime = None,
    **kwargs
) -> Event:
    """
    Utility function to create Event objects from raw data
    
    Provides a convenient way to create Event objects with common
    parameters while maintaining type safety and validation.
    
    Args:
        source_id: Original ID from source
        source_name: Name of the source
        source_type: Type of source
        text: Event text content
        title: Event title (optional)
        location: Event location (optional)
        media_urls: List of media URLs (optional)
        timestamp: Event timestamp (optional)
        **kwargs: Additional event parameters
        
    Returns:
        Created Event object
    """
    # Create media objects from URLs
    media = []
    if media_urls:
        for url in media_urls:
            # Simple media type detection from URL
            media_type = "image" if any(ext in url.lower() for ext in ['.jpg', '.png', '.gif']) else "video"
            media.append(MediaContent(url=url, media_type=media_type))
    
    return Event(
        source_id=source_id,
        source_name=source_name,
        source_type=source_type,
        text=text,
        title=title,
        location=location,
        media=media,
        timestamp=timestamp or datetime.now(timezone.utc),
        **kwargs
    )


def validate_event_schema(event_data: Dict[str, Any]) -> bool:
    """
    Validate event data against the expected schema
    
    Args:
        event_data: Event data to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["text"]  # Only text is strictly required
    
    for field in required_fields:
        if field not in event_data or not event_data[field]:
            return False
    
    # Validate timestamp format if present
    if "timestamp" in event_data:
        try:
            datetime.fromisoformat(event_data["timestamp"])
        except (ValueError, TypeError):
            return False
    
    # Validate location if present
    if "location" in event_data:
        location = event_data["location"]
        if not isinstance(location, dict):
            return False
        
        if "lat" in location and "lon" in location:
            try:
                lat = float(location["lat"])
                lon = float(location["lon"])
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    return False
            except (ValueError, TypeError):
                return False
    
    return True
