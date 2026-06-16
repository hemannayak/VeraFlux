"""
Text Verification
Verify authenticity and credibility of text-based disaster reports
"""

import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CredibilityScore:
    """Credibility score for a disaster report"""
    overall_score: float
    source_reliability: float
    content_consistency: float
    temporal_consistency: float
    location_consistency: float
    details: Dict[str, Any]


class TextVerifier:
    """Text-based disaster report verification"""
    
    def __init__(self):
        self.reliable_sources = {
            'official_government', 'emergency_services', 'news_agency',
            'weather_service', 'seismic_institute', 'red_cross'
        }
        self.suspicious_patterns = [
            r'click here',
            r'urgent.*donation',
            r'fake.*news',
            r'hoax',
            r'scam'
        ]
    
    def verify_report(self, report: Dict[str, Any]) -> CredibilityScore:
        """Verify a single disaster report"""
        scores = {
            'source_reliability': self._assess_source_reliability(report),
            'content_consistency': self._assess_content_consistency(report),
            'temporal_consistency': self._assess_temporal_consistency(report),
            'location_consistency': self._assess_location_consistency(report)
        }
        
        overall_score = sum(scores.values()) / len(scores)
        
        return CredibilityScore(
            overall_score=overall_score,
            details=scores,
            **scores
        )
    
    def _assess_source_reliability(self, report: Dict[str, Any]) -> float:
        """Assess the reliability of the source"""
        source = report.get('source', '').lower()
        
        # Check against known reliable sources
        if any(reliable in source for reliable in self.reliable_sources):
            return 0.9
        
        # Check for social media sources
        if any(platform in source for platform in ['twitter', 'facebook', 'instagram']):
            return 0.5
        
        # Unknown source
        return 0.3
    
    def _assess_content_consistency(self, report: Dict[str, Any]) -> float:
        """Assess the consistency of the content"""
        content = report.get('content', '').lower()
        
        # Check for suspicious patterns
        if any(re.search(pattern, content) for pattern in self.suspicious_patterns):
            return 0.2
        
        # Check for disaster-specific terminology
        disaster_terms = [
            'earthquake', 'flood', 'hurricane', 'evacuation',
            'emergency', 'damage', 'injuries', 'casualties'
        ]
        
        term_count = sum(1 for term in disaster_terms if term in content)
        if term_count >= 2:
            return 0.8
        elif term_count >= 1:
            return 0.6
        
        return 0.4
    
    def _assess_temporal_consistency(self, report: Dict[str, Any]) -> float:
        """Assess temporal consistency of the report"""
        try:
            report_time = datetime.fromisoformat(report.get('timestamp', ''))
            current_time = datetime.now()
            
            # Reports too far in the future are suspicious
            if report_time > current_time + timedelta(hours=1):
                return 0.1
            
            # Very recent reports are more credible
            if report_time > current_time - timedelta(hours=6):
                return 0.9
            elif report_time > current_time - timedelta(days=1):
                return 0.7
            else:
                return 0.5
                
        except (ValueError, TypeError):
            return 0.3
    
    def _assess_location_consistency(self, report: Dict[str, Any]) -> float:
        """Assess location consistency of the report"""
        location = report.get('location', {})
        content = report.get('content', '').lower()
        
        # Check if location is mentioned in content
        if 'location' in location:
            lat, lon = location.get('lat'), location.get('lon')
            if lat is not None and lon is not None:
                # Valid coordinates
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return 0.8
        
        # Check for location mentions in content
        location_words = ['street', 'avenue', 'road', 'city', 'county', 'state']
        if any(word in content for word in location_words):
            return 0.6
        
        return 0.3


class CrossReferenceVerifier:
    """Cross-reference verification across multiple sources"""
    
    def __init__(self):
        self.text_verifier = TextVerifier()
    
    def verify_multiple_sources(self, reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify multiple reports about the same event"""
        if not reports:
            return {'verified': False, 'confidence': 0.0}
        
        # Verify individual reports
        verified_reports = []
        for report in reports:
            score = self.text_verifier.verify_report(report)
            if score.overall_score >= 0.5:
                verified_reports.append((report, score))
        
        if not verified_reports:
            return {'verified': False, 'confidence': 0.0}
        
        # Calculate overall confidence
        avg_confidence = sum(score.overall_score for _, score in verified_reports) / len(verified_reports)
        
        # Check consistency across reports
        consistency_score = self._check_cross_consistency([r for r, _ in verified_reports])
        
        final_confidence = (avg_confidence + consistency_score) / 2
        
        return {
            'verified': final_confidence >= 0.6,
            'confidence': final_confidence,
            'source_count': len(verified_reports),
            'reports': verified_reports
        }
    
    def _check_cross_consistency(self, reports: List[Dict[str, Any]]) -> float:
        """Check consistency across multiple reports"""
        if len(reports) < 2:
            return 0.5
        
        # Check event type consistency
        event_types = [r.get('event_type') for r in reports]
        type_consistency = len(set(event_types)) / len(event_types)
        
        # Check location proximity
        locations = [r.get('location', {}) for r in reports]
        location_consistency = self._calculate_location_proximity(locations)
        
        # Check time proximity
        timestamps = [r.get('timestamp') for r in reports]
        time_consistency = self._calculate_time_proximity(timestamps)
        
        return (type_consistency + location_consistency + time_consistency) / 3
    
    def _calculate_location_proximity(self, locations: List[Dict[str, Any]]) -> float:
        """Calculate how close locations are to each other"""
        valid_locations = [loc for loc in locations if loc.get('lat') and loc.get('lon')]
        
        if len(valid_locations) < 2:
            return 0.5
        
        # Calculate average distance between all location pairs
        total_distance = 0
        pair_count = 0
        
        for i in range(len(valid_locations)):
            for j in range(i + 1, len(valid_locations)):
                loc1, loc2 = valid_locations[i], valid_locations[j]
                distance = ((loc1['lat'] - loc2['lat']) ** 2 + 
                           (loc1['lon'] - loc2['lon']) ** 2) ** 0.5
                total_distance += distance
                pair_count += 1
        
        avg_distance = total_distance / pair_count
        
        # Convert to consistency score (closer = higher score)
        return max(0, 1 - avg_distance / 10)  # Normalize by ~10 degrees
    
    def _calculate_time_proximity(self, timestamps: List[str]) -> float:
        """Calculate how close timestamps are to each other"""
        valid_times = []
        for ts in timestamps:
            try:
                valid_times.append(datetime.fromisoformat(ts))
            except (ValueError, TypeError):
                continue
        
        if len(valid_times) < 2:
            return 0.5
        
        # Calculate time span
        time_span = max(valid_times) - min(valid_times)
        hours_span = time_span.total_seconds() / 3600
        
        # Convert to consistency score (shorter span = higher score)
        return max(0, 1 - hours_span / 24)  # Normalize by 24 hours
