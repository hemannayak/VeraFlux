"""
Offline Storage
Local storage and synchronization for edge computing scenarios
"""

import json
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import threading


@dataclass
class OfflineEvent:
    """Offline disaster event storage"""
    id: str
    event_type: str
    severity: str
    title: str
    content: str
    location: Dict[str, float]
    timestamp: str
    source: str
    verified: bool = False
    confidence_score: float = 0.0
    synced: bool = False
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


class OfflineDatabase:
    """Local SQLite database for offline storage"""
    
    def __init__(self, db_path: str = "edge_storage.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS offline_events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    location_lat REAL,
                    location_lon REAL,
                    timestamp TEXT NOT NULL,
                    source TEXT,
                    verified BOOLEAN DEFAULT FALSE,
                    confidence_score REAL DEFAULT 0.0,
                    synced BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    data TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    last_attempt TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.commit()
    
    def store_event(self, event: OfflineEvent) -> bool:
        """Store an event locally"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO offline_events 
                        (id, event_type, severity, title, content, location_lat, location_lon,
                         timestamp, source, verified, confidence_score, synced, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.id,
                        event.event_type,
                        event.severity,
                        event.title,
                        event.content,
                        event.location.get('lat'),
                        event.location.get('lon'),
                        event.timestamp,
                        event.source,
                        event.verified,
                        event.confidence_score,
                        event.synced,
                        event.created_at
                    ))
                    conn.commit()
            return True
        except Exception as e:
            print(f"Error storing event: {e}")
            return False
    
    def get_event(self, event_id: str) -> Optional[OfflineEvent]:
        """Retrieve an event by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM offline_events WHERE id = ?",
                    (event_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return OfflineEvent(
                        id=row['id'],
                        event_type=row['event_type'],
                        severity=row['severity'],
                        title=row['title'],
                        content=row['content'],
                        location={'lat': row['location_lat'], 'lon': row['location_lon']},
                        timestamp=row['timestamp'],
                        source=row['source'],
                        verified=bool(row['verified']),
                        confidence_score=row['confidence_score'],
                        synced=bool(row['synced']),
                        created_at=row['created_at']
                    )
        except Exception as e:
            print(f"Error retrieving event: {e}")
        
        return None
    
    def get_unsynced_events(self) -> List[OfflineEvent]:
        """Get all events that haven't been synced"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM offline_events WHERE synced = FALSE ORDER BY created_at"
                )
                rows = cursor.fetchall()
                
                events = []
                for row in rows:
                    event = OfflineEvent(
                        id=row['id'],
                        event_type=row['event_type'],
                        severity=row['severity'],
                        title=row['title'],
                        content=row['content'],
                        location={'lat': row['location_lat'], 'lon': row['location_lon']},
                        timestamp=row['timestamp'],
                        source=row['source'],
                        verified=bool(row['verified']),
                        confidence_score=row['confidence_score'],
                        synced=bool(row['synced']),
                        created_at=row['created_at']
                    )
                    events.append(event)
                
                return events
        except Exception as e:
            print(f"Error getting unsynced events: {e}")
            return []
    
    def mark_synced(self, event_id: str) -> bool:
        """Mark an event as synced"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "UPDATE offline_events SET synced = TRUE WHERE id = ?",
                        (event_id,)
                    )
                    conn.commit()
            return True
        except Exception as e:
            print(f"Error marking event as synced: {e}")
            return False
    
    def get_recent_events(self, hours: int = 24) -> List[OfflineEvent]:
        """Get recent events from local storage"""
        try:
            cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM offline_events WHERE timestamp >= ? ORDER BY timestamp DESC",
                    (cutoff_time,)
                )
                rows = cursor.fetchall()
                
                events = []
                for row in rows:
                    event = OfflineEvent(
                        id=row['id'],
                        event_type=row['event_type'],
                        severity=row['severity'],
                        title=row['title'],
                        content=row['content'],
                        location={'lat': row['location_lat'], 'lon': row['location_lon']},
                        timestamp=row['timestamp'],
                        source=row['source'],
                        verified=bool(row['verified']),
                        confidence_score=row['confidence_score'],
                        synced=bool(row['synced']),
                        created_at=row['created_at']
                    )
                    events.append(event)
                
                return events
        except Exception as e:
            print(f"Error getting recent events: {e}")
            return []


class SyncManager:
    """Manage synchronization between edge and central storage"""
    
    def __init__(self, offline_db: OfflineDatabase, central_api_url: str):
        self.offline_db = offline_db
        self.central_api_url = central_api_url
        self.sync_interval = 300  # 5 minutes
        self.max_retries = 3
    
    def queue_for_sync(self, event_id: str, operation: str = "create") -> bool:
        """Queue an event for synchronization"""
        try:
            with sqlite3.connect(self.offline_db.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO sync_queue 
                    (id, operation, data, retry_count, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    event_id,
                    operation,
                    json.dumps({'event_id': event_id}),
                    0,
                    datetime.utcnow().isoformat()
                ))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error queuing for sync: {e}")
            return False
    
    async def sync_to_central(self) -> Dict[str, Any]:
        """Synchronize pending events to central storage"""
        unsynced_events = self.offline_db.get_unsynced_events()
        
        sync_results = {
            'total': len(unsynced_events),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for event in unsynced_events:
            try:
                # TODO: Implement actual API call to central storage
                success = await self._send_to_central(event)
                
                if success:
                    self.offline_db.mark_synced(event.id)
                    sync_results['successful'] += 1
                else:
                    sync_results['failed'] += 1
                    sync_results['errors'].append(f"Failed to sync event {event.id}")
                    
            except Exception as e:
                sync_results['failed'] += 1
                sync_results['errors'].append(f"Error syncing event {event.id}: {str(e)}")
        
        return sync_results
    
    async def _send_to_central(self, event: OfflineEvent) -> bool:
        """Send event to central storage"""
        # TODO: Implement actual HTTP request to central API
        # For now, simulate success
        import asyncio
        await asyncio.sleep(0.1)  # Simulate network delay
        return True
    
    async def start_sync_loop(self):
        """Start the automatic synchronization loop"""
        while True:
            try:
                results = await self.sync_to_central()
                print(f"Sync completed: {results['successful']}/{results['total']} events synced")
                
                if results['failed'] > 0:
                    print(f"Sync errors: {results['errors']}")
                
            except Exception as e:
                print(f"Error in sync loop: {e}")
            
            await asyncio.sleep(self.sync_interval)


class EdgeNode:
    """Main edge node functionality"""
    
    def __init__(self, node_id: str, storage_path: str = "./edge_storage"):
        self.node_id = node_id
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Initialize offline database
        db_path = self.storage_path / f"{node_id}_offline.db"
        self.offline_db = OfflineDatabase(str(db_path))
        
        # Initialize sync manager
        self.sync_manager = SyncManager(
            self.offline_db,
            "https://api.veraflux.com/v1/events"
        )
        
        self.is_online = False
    
    def store_event_offline(self, event_data: Dict[str, Any]) -> str:
        """Store an event when offline"""
        event = OfflineEvent(
            id=event_data.get('id', f"offline_{datetime.utcnow().timestamp()}"),
            event_type=event_data.get('event_type', 'unknown'),
            severity=event_data.get('severity', 'unknown'),
            title=event_data.get('title', ''),
            content=event_data.get('content', ''),
            location=event_data.get('location', {}),
            timestamp=event_data.get('timestamp', datetime.utcnow().isoformat()),
            source=event_data.get('source', 'edge_node'),
            verified=event_data.get('verified', False),
            confidence_score=event_data.get('confidence_score', 0.0)
        )
        
        if self.offline_db.store_event(event):
            # Queue for sync when online
            self.sync_manager.queue_for_sync(event.id)
            return event.id
        
        return None
    
    def get_local_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get events from local storage"""
        events = self.offline_db.get_recent_events(hours)
        return [asdict(event) for event in events]
    
    async def connect_to_central(self):
        """Connect to central storage and sync"""
        self.is_online = True
        results = await self.sync_manager.sync_to_central()
        return results
    
    def disconnect_from_central(self):
        """Disconnect from central storage"""
        self.is_online = False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            with sqlite3.connect(self.offline_db.db_path) as conn:
                total_events = conn.execute(
                    "SELECT COUNT(*) FROM offline_events"
                ).fetchone()[0]
                
                unsynced_events = conn.execute(
                    "SELECT COUNT(*) FROM offline_events WHERE synced = FALSE"
                ).fetchone()[0]
                
                return {
                    'node_id': self.node_id,
                    'total_events': total_events,
                    'unsynced_events': unsynced_events,
                    'is_online': self.is_online,
                    'storage_path': str(self.storage_path)
                }
        except Exception as e:
            return {'error': str(e)}
