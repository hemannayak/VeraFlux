"""
Deduplication Module
Remove duplicate and similar disaster events
"""

import hashlib
from typing import List, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class SimilarityConfig:
    """Configuration for similarity detection"""
    content_threshold: float = 0.8
    time_threshold_minutes: int = 30
    location_threshold_km: float = 5.0


class EventDeduplicator:
    """Deduplicate disaster events based on various criteria"""
    
    def __init__(self, config: SimilarityConfig = None):
        self.config = config or SimilarityConfig()
        self.seen_hashes = set()
    
    def deduplicate(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate events from the list"""
        unique_events = []
        
        for event in events:
            if self._is_unique(event, unique_events):
                unique_events.append(event)
                self.seen_hashes.add(self._generate_hash(event))
        
        return unique_events
    
    def _is_unique(self, event: Dict[str, Any], 
                   existing_events: List[Dict[str, Any]]) -> bool:
        """Check if an event is unique compared to existing events"""
        event_hash = self._generate_hash(event)
        
        # Check exact hash match
        if event_hash in self.seen_hashes:
            return False
        
        # Check similarity with existing events
        for existing_event in existing_events:
            if self._are_similar(event, existing_event):
                return False
        
        return True
    
    def _generate_hash(self, event: Dict[str, Any]) -> str:
        """Generate a hash for the event"""
        content = event.get('content', '')
        location = event.get('location', {})
        event_type = event.get('event_type', '')
        
        hash_input = f"{content}_{location}_{event_type}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _are_similar(self, event1: Dict[str, Any], 
                    event2: Dict[str, Any]) -> bool:
        """Check if two events are similar"""
        # Content similarity
        content_sim = SequenceMatcher(
            None, 
            event1.get('content', ''), 
            event2.get('content', '')
        ).ratio()
        
        if content_sim >= self.config.content_threshold:
            # Check time proximity
            if self._are_times_close(event1, event2):
                # Check location proximity
                if self._are_locations_close(event1, event2):
                    return True
        
        return False
    
    def _are_times_close(self, event1: Dict[str, Any], 
                        event2: Dict[str, Any]) -> bool:
        """Check if two events occurred within time threshold"""
        try:
            time1 = datetime.fromisoformat(event1.get('timestamp', ''))
            time2 = datetime.fromisoformat(event2.get('timestamp', ''))
            
            time_diff = abs((time1 - time2).total_seconds())
            return time_diff <= self.config.time_threshold_minutes * 60
        except (ValueError, TypeError):
            return False
    
    def _are_locations_close(self, event1: Dict[str, Any], 
                           event2: Dict[str, Any]) -> bool:
        """Check if two events are within location threshold"""
        loc1 = event1.get('location', {})
        loc2 = event2.get('location', {})
        
        try:
            lat1, lon1 = loc1.get('lat', 0), loc1.get('lon', 0)
            lat2, lon2 = loc2.get('lat', 0), loc2.get('lon', 0)
            
            # Simple distance calculation (approximate)
            distance = ((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) ** 0.5
            return distance <= self.config.location_threshold_km / 111  # Convert km to degrees
        except (ValueError, TypeError):
            return False


class ClusterDeduplicator:
    """Cluster-based deduplication for large datasets"""
    
    def __init__(self, similarity_config: SimilarityConfig = None):
        self.config = similarity_config or SimilarityConfig()
        self.deduplicator = EventDeduplicator(self.config)
    
    def deduplicate_clusters(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate using clustering approach"""
        # Group events by basic criteria first
        clusters = self._create_clusters(events)
        
        # Deduplicate within each cluster
        unique_events = []
        for cluster in clusters:
            cluster_unique = self.deduplicator.deduplicate(cluster)
            unique_events.extend(cluster_unique)
        
        return unique_events
    
    def _create_clusters(self, events: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Create clusters of similar events"""
        clusters = []
        
        for event in events:
            placed = False
            for cluster in clusters:
                if self._should_cluster(event, cluster[0]):
                    cluster.append(event)
                    placed = True
                    break
            
            if not placed:
                clusters.append([event])
        
        return clusters
    
    def _should_cluster(self, event1: Dict[str, Any], 
                       event2: Dict[str, Any]) -> bool:
        """Determine if two events should be in the same cluster"""
        # Use event type and rough location for initial clustering
        return (event1.get('event_type') == event2.get('event_type') and
                self._rough_location_match(event1, event2))
    
    def _rough_location_match(self, event1: Dict[str, Any], 
                             event2: Dict[str, Any]) -> bool:
        """Rough location matching for clustering"""
        loc1 = event1.get('location', {})
        loc2 = event2.get('location', {})
        
        lat_diff = abs(loc1.get('lat', 0) - loc2.get('lat', 0))
        lon_diff = abs(loc1.get('lon', 0) - loc2.get('lon', 0))
        
        # Use larger threshold for initial clustering
        return lat_diff <= 1.0 and lon_diff <= 1.0  # ~100km
