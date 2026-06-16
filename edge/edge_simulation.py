"""
Edge Node Simulation
Simulate edge computing scenarios for disaster response
"""

import asyncio
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

from .offline_storage import EdgeNode


@dataclass
class DisasterScenario:
    """Disaster scenario configuration"""
    name: str
    event_types: List[str]
    severity_distribution: Dict[str, float]
    location_center: Dict[str, float]
    radius_km: float
    duration_hours: int
    event_frequency: float  # events per minute


class EventGenerator:
    """Generate realistic disaster events for simulation"""
    
    def __init__(self):
        self.event_templates = {
            'earthquake': [
                "Magnitude {magnitude} earthquake detected near {location}",
                "Strong tremors felt in {location}",
                "Building collapse reported in {location} after earthquake",
                "Emergency services responding to earthquake in {location}"
            ],
            'flood': [
                "Flash flooding reported in {location}",
                "River levels rising rapidly in {location}",
                "Evacuation orders issued for {location} due to flooding",
                "Rescue operations underway in flooded {location}"
            ],
            'hurricane': [
                "Hurricane {name} approaching {location}",
                "Strong winds and heavy rain in {location}",
                "Power outages reported in {location} during hurricane",
                "Emergency shelters opened in {location}"
            ],
            'wildfire': [
                "Wildfire spreading near {location}",
                "Mandatory evacuation for {location} due to wildfire",
                "Firefighters battling blaze in {location}",
                "Air quality alerts issued for {location}"
            ]
        }
        
        self.locations = [
            "downtown area", "residential district", "industrial zone",
            "shopping center", "hospital district", "school area",
            "highway intersection", "coastal region", "mountain area"
        ]
        
        self.sources = [
            "emergency_services", "news_reporter", "eyewitness", 
            "weather_station", "social_media", "official_government"
        ]
    
    def generate_event(self, event_type: str, location: Dict[str, float]) -> Dict[str, Any]:
        """Generate a realistic disaster event"""
        template = random.choice(self.event_templates.get(event_type, ["Disaster in {location}"]))
        location_name = random.choice(self.locations)
        
        content = template.format(
            location=location_name,
            magnitude=random.uniform(4.0, 8.0) if event_type == 'earthquake' else '',
            name=random.choice(['Alpha', 'Beta', 'Gamma', 'Delta']) if event_type == 'hurricane' else ''
        )
        
        # Add some variation to location
        lat_offset = random.uniform(-0.1, 0.1)
        lon_offset = random.uniform(-0.1, 0.1)
        
        event = {
            'id': f"sim_{datetime.utcnow().timestamp()}_{random.randint(1000, 9999)}",
            'event_type': event_type,
            'severity': self._generate_severity(event_type),
            'title': content[:100] + "..." if len(content) > 100 else content,
            'content': content,
            'location': {
                'lat': location['lat'] + lat_offset,
                'lon': location['lon'] + lon_offset
            },
            'timestamp': datetime.utcnow().isoformat(),
            'source': random.choice(self.sources),
            'verified': random.random() > 0.7,  # 30% verified
            'confidence_score': random.uniform(0.3, 0.9)
        }
        
        return event
    
    def _generate_severity(self, event_type: str) -> str:
        """Generate severity based on event type"""
        severity_weights = {
            'earthquake': {'low': 0.2, 'medium': 0.3, 'high': 0.4, 'critical': 0.1},
            'flood': {'low': 0.3, 'medium': 0.4, 'high': 0.2, 'critical': 0.1},
            'hurricane': {'low': 0.1, 'medium': 0.3, 'high': 0.4, 'critical': 0.2},
            'wildfire': {'low': 0.2, 'medium': 0.3, 'high': 0.3, 'critical': 0.2}
        }
        
        weights = severity_weights.get(event_type, {'low': 0.25, 'medium': 0.25, 'high': 0.25, 'critical': 0.25})
        return random.choices(['low', 'medium', 'high', 'critical'], weights=list(weights.values()))[0]


class NetworkSimulator:
    """Simulate network conditions for edge scenarios"""
    
    def __init__(self):
        self.is_connected = True
        self.latency_ms = 50
        self.packet_loss_rate = 0.0
        self.bandwidth_mbps = 100
    
    def set_network_conditions(self, is_connected: bool, latency_ms: int = 50, 
                             packet_loss_rate: float = 0.0, bandwidth_mbps: int = 100):
        """Set network simulation parameters"""
        self.is_connected = is_connected
        self.latency_ms = latency_ms
        self.packet_loss_rate = packet_loss_rate
        self.bandwidth_mbps = bandwidth_mbps
    
    async def simulate_request(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Simulate a network request with current conditions"""
        if not self.is_connected:
            return None
        
        # Simulate packet loss
        if random.random() < self.packet_loss_rate:
            return None
        
        # Simulate latency
        await asyncio.sleep(self.latency_ms / 1000.0)
        
        # Simulate bandwidth limitation
        data_size = len(json.dumps(data))
        if data_size > self.bandwidth_mbps * 1024 * 1024 / 8:  # Convert to bytes
            return None
        
        return {'status': 'success', 'data': data}


class EdgeSimulationManager:
    """Manage edge node simulations"""
    
    def __init__(self):
        self.edge_nodes: Dict[str, EdgeNode] = {}
        self.event_generator = EventGenerator()
        self.network_simulator = NetworkSimulator()
        self.scenarios: Dict[str, DisasterScenario] = {}
        self.running_simulations: Dict[str, asyncio.Task] = {}
    
    def create_edge_node(self, node_id: str, storage_path: str = None) -> EdgeNode:
        """Create a new edge node"""
        if storage_path is None:
            storage_path = f"./edge_storage/{node_id}"
        
        edge_node = EdgeNode(node_id, storage_path)
        self.edge_nodes[node_id] = edge_node
        return edge_node
    
    def create_scenario(self, scenario_id: str, scenario: DisasterScenario):
        """Create a disaster scenario"""
        self.scenarios[scenario_id] = scenario
    
    async def start_simulation(self, scenario_id: str, node_ids: List[str]) -> Dict[str, Any]:
        """Start a disaster simulation on specified edge nodes"""
        if scenario_id not in self.scenarios:
            return {'error': f'Scenario {scenario_id} not found'}
        
        scenario = self.scenarios[scenario_id]
        
        # Validate edge nodes
        for node_id in node_ids:
            if node_id not in self.edge_nodes:
                return {'error': f'Edge node {node_id} not found'}
        
        # Start simulation task
        task = asyncio.create_task(
            self._run_simulation(scenario_id, scenario, node_ids)
        )
        self.running_simulations[scenario_id] = task
        
        return {
            'scenario_id': scenario_id,
            'status': 'started',
            'nodes': node_ids,
            'duration_hours': scenario.duration_hours
        }
    
    async def _run_simulation(self, scenario_id: str, scenario: DisasterScenario, 
                            node_ids: List[str]):
        """Run the actual simulation"""
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=scenario.duration_hours)
        
        print(f"Starting simulation {scenario_id}: {scenario.name}")
        
        while datetime.utcnow() < end_time:
            # Generate events based on frequency
            if random.random() < scenario.event_frequency / 60.0:  # Convert to per-second probability
                event_type = random.choices(
                    scenario.event_types,
                    weights=list(scenario.severity_distribution.values())
                )[0]
                
                event = self.event_generator.generate_event(
                    event_type, 
                    scenario.location_center
                )
                
                # Store event on random edge node
                node_id = random.choice(node_ids)
                edge_node = self.edge_nodes[node_id]
                
                # Simulate network conditions
                if self.network_simulator.is_connected:
                    # Try to sync to central
                    try:
                        await edge_node.connect_to_central()
                    except Exception as e:
                        print(f"Network error for node {node_id}: {e}")
                        edge_node.disconnect_from_central()
                
                # Store offline
                event_id = edge_node.store_event_offline(event)
                print(f"Event {event_id} stored on node {node_id}")
            
            # Randomly change network conditions
            if random.random() < 0.1:  # 10% chance every iteration
                self._randomize_network_conditions()
            
            await asyncio.sleep(60)  # Check every minute
        
        print(f"Simulation {scenario_id} completed")
    
    def _randomize_network_conditions(self):
        """Randomly change network conditions to simulate disaster scenarios"""
        # Simulate network degradation during disasters
        network_states = [
            (True, 50, 0.0, 100),    # Good network
            (True, 200, 0.05, 50),   # Slow network with some packet loss
            (True, 500, 0.15, 10),   # Very slow network
            (False, 0, 1.0, 0),      # No connection
            (True, 100, 0.02, 75),   # Moderate network
        ]
        
        state = random.choice(network_states)
        self.network_simulator.set_network_conditions(*state)
        
        status = "connected" if state[0] else "disconnected"
        print(f"Network conditions changed: {status}, latency: {state[1]}ms, "
              f"packet loss: {state[2]*100:.1f}%, bandwidth: {state[3]}Mbps")
    
    async def stop_simulation(self, scenario_id: str):
        """Stop a running simulation"""
        if scenario_id in self.running_simulations:
            task = self.running_simulations[scenario_id]
            task.cancel()
            del self.running_simulations[scenario_id]
            return {'status': 'stopped', 'scenario_id': scenario_id}
        
        return {'error': f'Simulation {scenario_id} not found or not running'}
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """Get status of all simulations and edge nodes"""
        status = {
            'running_simulations': list(self.running_simulations.keys()),
            'edge_nodes': {},
            'network_conditions': {
                'connected': self.network_simulator.is_connected,
                'latency_ms': self.network_simulator.latency_ms,
                'packet_loss_rate': self.network_simulator.packet_loss_rate,
                'bandwidth_mbps': self.network_simulator.bandwidth_mbps
            }
        }
        
        for node_id, node in self.edge_nodes.items():
            status['edge_nodes'][node_id] = node.get_storage_stats()
        
        return status
    
    async def sync_all_nodes(self) -> Dict[str, Any]:
        """Attempt to sync all edge nodes to central storage"""
        results = {
            'total_nodes': len(self.edge_nodes),
            'successful_syncs': 0,
            'failed_syncs': 0,
            'node_results': {}
        }
        
        for node_id, node in self.edge_nodes.items():
            try:
                sync_result = await node.connect_to_central()
                results['node_results'][node_id] = sync_result
                results['successful_syncs'] += 1
            except Exception as e:
                results['node_results'][node_id] = {'error': str(e)}
                results['failed_syncs'] += 1
        
        return results


# Predefined disaster scenarios
EARTHQUAKE_SCENARIO = DisasterScenario(
    name="Major Earthquake",
    event_types=["earthquake"],
    severity_distribution={"low": 0.1, "medium": 0.2, "high": 0.5, "critical": 0.2},
    location_center={"lat": 37.7749, "lon": -122.4194},  # San Francisco
    radius_km=50,
    duration_hours=6,
    event_frequency=5.0  # 5 events per minute
)

HURRICANE_SCENARIO = DisasterScenario(
    name="Hurricane Landfall",
    event_types=["hurricane", "flood"],
    severity_distribution={"low": 0.2, "medium": 0.3, "high": 0.3, "critical": 0.2},
    location_center={"lat": 25.7617, "lon": -80.1918},  # Miami
    radius_km=100,
    duration_hours=12,
    event_frequency=3.0
)

WILDFIRE_SCENARIO = DisasterScenario(
    name="Wildfire Spread",
    event_types=["wildfire"],
    severity_distribution={"low": 0.3, "medium": 0.4, "high": 0.2, "critical": 0.1},
    location_center={"lat": 34.0522, "lon": -118.2437},  # Los Angeles
    radius_km=75,
    duration_hours=8,
    event_frequency=2.0
)
