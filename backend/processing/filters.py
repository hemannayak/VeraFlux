"""
Data Filters
Various filtering mechanisms for disaster data
"""

import re
from typing import List, Dict, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class FilterCriteria:
    """Filter criteria for disaster events"""
    event_types: Set[str] = None
    severity_levels: Set[str] = None
    time_window: timedelta = None
    location_bounds: Dict[str, float] = None  # lat_min, lat_max, lon_min, lon_max
    keywords: Set[str] = None
    languages: Set[str] = None


class DisasterFilter:
    """Main disaster event filter"""
    
    def __init__(self):
        self.disaster_keywords = {
            'earthquake', 'flood', 'hurricane', 'tornado', 'wildfire',
            'tsunami', 'volcano', 'landslide', 'drought', 'storm'
        }
        self.severity_levels = {'low', 'medium', 'high', 'critical'}
    
    def filter_by_relevance(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter events by disaster relevance"""
        relevant_events = []
        
        for event in events:
            content = event.get('content', '').lower()
            if any(keyword in content for keyword in self.disaster_keywords):
                relevant_events.append(event)
        
        return relevant_events
    
    def filter_by_criteria(self, events: List[Dict[str, Any]], 
                          criteria: FilterCriteria) -> List[Dict[str, Any]]:
        """Filter events based on specified criteria"""
        filtered_events = events
        
        # Filter by event type
        if criteria.event_types:
            filtered_events = [
                e for e in filtered_events 
                if e.get('event_type') in criteria.event_types
            ]
        
        # Filter by severity
        if criteria.severity_levels:
            filtered_events = [
                e for e in filtered_events 
                if e.get('severity') in criteria.severity_levels
            ]
        
        # Filter by time window
        if criteria.time_window:
            cutoff_time = datetime.now() - criteria.time_window
            filtered_events = [
                e for e in filtered_events 
                if datetime.fromisoformat(e.get('timestamp', '')) >= cutoff_time
            ]
        
        # Filter by location bounds
        if criteria.location_bounds:
            bounds = criteria.location_bounds
            filtered_events = [
                e for e in filtered_events 
                if self._is_within_bounds(e.get('location', {}), bounds)
            ]
        
        # Filter by keywords
        if criteria.keywords:
            filtered_events = [
                e for e in filtered_events 
                if any(keyword in e.get('content', '').lower() 
                      for keyword in criteria.keywords)
            ]
        
        return filtered_events
    
    def _is_within_bounds(self, location: Dict[str, float], 
                         bounds: Dict[str, float]) -> bool:
        """Check if location is within specified bounds"""
        lat = location.get('lat', 0)
        lon = location.get('lon', 0)
        
        return (bounds.get('lat_min', -90) <= lat <= bounds.get('lat_max', 90) and
                bounds.get('lon_min', -180) <= lon <= bounds.get('lon_max', 180))


class SpamFilter:
    """Spam and noise filter"""
    
    def __init__(self):
        self.spam_patterns = [
            r'click here',
            r'buy now',
            r'free.*money',
            r'urgent.*action',
            r'limited.*time'
        ]
    
    def filter_spam(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove spam events"""
        legitimate_events = []
        
        for event in events:
            content = event.get('content', '').lower()
            if not any(re.search(pattern, content) for pattern in self.spam_patterns):
                legitimate_events.append(event)
        
        return legitimate_events
