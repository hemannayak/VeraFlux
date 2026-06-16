"""
Real-time Disaster Intelligence Dashboard
Interactive dashboard for visualizing disaster data and analytics
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import requests
import json
from typing import List, Dict, Any


class DisasterDashboard:
    """Main dashboard class for disaster intelligence visualization"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.setup_page_config()
    
    def setup_page_config(self):
        """Setup Streamlit page configuration"""
        st.set_page_config(
            page_title="Veraflux - Disaster Intelligence Dashboard",
            page_icon="🚨",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def run(self):
        """Run the main dashboard"""
        st.title("🚨 Veraflux Disaster Intelligence Dashboard")
        st.markdown("---")
        
        # Sidebar for controls
        self.render_sidebar()
        
        # Main content area
        self.render_main_content()
    
    def render_sidebar(self):
        """Render sidebar with controls"""
        st.sidebar.title("Dashboard Controls")
        
        # Time range selector
        st.sidebar.subheader("Time Range")
        time_range = st.sidebar.selectbox(
            "Select Time Range",
            ["Last Hour", "Last 6 Hours", "Last 24 Hours", "Last 7 Days"],
            index=2
        )
        
        # Event type filter
        st.sidebar.subheader("Event Types")
        event_types = st.sidebar.multiselect(
            "Filter by Event Type",
            ["earthquake", "flood", "hurricane", "wildfire", "tornado", "all"],
            default=["all"]
        )
        
        # Severity filter
        st.sidebar.subheader("Severity Level")
        severity_levels = st.sidebar.multiselect(
            "Filter by Severity",
            ["low", "medium", "high", "critical"],
            default=["medium", "high", "critical"]
        )
        
        # Location filter
        st.sidebar.subheader("Location Filter")
        use_location_filter = st.sidebar.checkbox("Filter by Location")
        if use_location_filter:
            lat_center = st.sidebar.number_input("Latitude Center", value=37.7749, format="%.4f")
            lon_center = st.sidebar.number_input("Longitude Center", value=-122.4194, format="%.4f")
            radius_km = st.sidebar.slider("Radius (km)", min_value=1, max_value=500, value=50)
        
        # Auto-refresh
        auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
        if auto_refresh:
            refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 10, 300, 30)
        
        # Store filters in session state
        st.session_state.filters = {
            'time_range': time_range,
            'event_types': event_types,
            'severity_levels': severity_levels,
            'use_location_filter': use_location_filter,
            'lat_center': lat_center if use_location_filter else None,
            'lon_center': lon_center if use_location_filter else None,
            'radius_km': radius_km if use_location_filter else None
        }
    
    def render_main_content(self):
        """Render main dashboard content"""
        # Create tabs for different views
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Overview", "🗺️ Map View", "📈 Analytics", 
            "🔍 Search", "⚙️ System Status"
        ])
        
        with tab1:
            self.render_overview_tab()
        
        with tab2:
            self.render_map_tab()
        
        with tab3:
            self.render_analytics_tab()
        
        with tab4:
            self.render_search_tab()
        
        with tab5:
            self.render_system_status_tab()
    
    def render_overview_tab(self):
        """Render overview dashboard"""
        st.header("📊 Disaster Overview")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_events = self.get_total_events()
            st.metric("Total Events", total_events)
        
        with col2:
            critical_events = self.get_critical_events()
            st.metric("Critical Events", critical_events, delta="🚨")
        
        with col3:
            verified_events = self.get_verified_events()
            st.metric("Verified Events", verified_events)
        
        with col4:
            active_locations = self.get_active_locations()
            st.metric("Active Locations", active_locations)
        
        st.markdown("---")
        
        # Recent events table
        st.subheader("Recent Events")
        recent_events = self.get_recent_events()
        
        if recent_events:
            df = pd.DataFrame(recent_events)
            
            # Format the dataframe for display
            display_columns = ['event_type', 'severity', 'title', 'timestamp', 'verified']
            if all(col in df.columns for col in display_columns):
                display_df = df[display_columns].copy()
                display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
                display_df['verified'] = display_df['verified'].map({True: '✅', False: '❌'})
                display_df.columns = ['Type', 'Severity', 'Title', 'Time', 'Verified']
                
                st.dataframe(display_df, use_container_width=True)
            else:
                st.json(recent_events[:5])  # Fallback to JSON
        else:
            st.info("No recent events found")
    
    def render_map_tab(self):
        """Render map visualization"""
        st.header("🗺️ Event Map View")
        
        events = self.get_events_with_location()
        
        if events:
            # Create map dataframe
            map_data = []
            for event in events:
                location = event.get('location', {})
                if location.get('lat') and location.get('lon'):
                    map_data.append({
                        'lat': location['lat'],
                        'lon': location['lon'],
                        'event_type': event.get('event_type', 'unknown'),
                        'severity': event.get('severity', 'unknown'),
                        'title': event.get('title', ''),
                        'timestamp': event.get('timestamp', ''),
                        'verified': event.get('verified', False)
                    })
            
            if map_data:
                df_map = pd.DataFrame(map_data)
                
                # Create color map for severity
                color_map = {
                    'low': 'blue',
                    'medium': 'yellow', 
                    'high': 'orange',
                    'critical': 'red'
                }
                df_map['color'] = df_map['severity'].map(color_map)
                
                # Create scatter mapbox
                fig = px.scatter_mapbox(
                    df_map,
                    lat="lat",
                    lon="lon",
                    color="severity",
                    color_discrete_map=color_map,
                    hover_name="title",
                    hover_data=["event_type", "timestamp", "verified"],
                    zoom=3,
                    height=600
                )
                
                fig.update_layout(
                    mapbox_style="open-street-map",
                    title="Disaster Events Map"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Event details below map
                st.subheader("Event Details")
                selected_event = st.selectbox(
                    "Select an event for details:",
                    options=df_map['title'].tolist(),
                    index=0
                )
                
                if selected_event:
                    event_details = next(
                        (e for e in events if e.get('title') == selected_event), 
                        None
                    )
                    if event_details:
                        st.json(event_details)
            else:
                st.warning("No events with location data found")
        else:
            st.info("No events found")
    
    def render_analytics_tab(self):
        """Render analytics and charts"""
        st.header("📈 Event Analytics")
        
        # Get analytics data
        events = self.get_recent_events(days=7)  # Last 7 days
        
        if events:
            df = pd.DataFrame(events)
            
            # Create subplots
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=("Events by Type", "Events by Severity", 
                              "Events Over Time", "Verification Status"),
                specs=[[{"type": "bar"}, {"type": "bar"}],
                       [{"type": "scatter"}, {"type": "pie"}]]
            )
            
            # Events by type
            event_type_counts = df['event_type'].value_counts()
            fig.add_trace(
                go.Bar(x=event_type_counts.index, y=event_type_counts.values,
                       name="Event Types"),
                row=1, col=1
            )
            
            # Events by severity
            severity_counts = df['severity'].value_counts()
            fig.add_trace(
                go.Bar(x=severity_counts.index, y=severity_counts.values,
                       name="Severity Levels"),
                row=1, col=2
            )
            
            # Events over time
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = df['timestamp'].dt.date
            time_counts = df.groupby('date').size()
            fig.add_trace(
                go.Scatter(x=time_counts.index, y=time_counts.values,
                          mode='lines+markers', name="Events Over Time"),
                row=2, col=1
            )
            
            # Verification status
            verified_counts = df['verified'].value_counts()
            fig.add_trace(
                go.Pie(labels=['Unverified', 'Verified'], 
                      values=[verified_counts.get(False, 0), verified_counts.get(True, 0)],
                      name="Verification Status"),
                row=2, col=2
            )
            
            fig.update_layout(height=800, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # Additional statistics
            st.subheader("Statistics Summary")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Most Common Event Type", event_type_counts.index[0])
            
            with col2:
                st.metric("Average Daily Events", round(time_counts.mean(), 1))
            
            with col3:
                verification_rate = (verified_counts.get(True, 0) / len(df)) * 100
                st.metric("Verification Rate", f"{verification_rate:.1f}%")
        else:
            st.info("No data available for analytics")
    
    def render_search_tab(self):
        """Render search functionality"""
        st.header("🔍 Event Search")
        
        # Search interface
        col1, col2 = st.columns([2, 1])
        
        with col1:
            search_query = st.text_input("Search Events", placeholder="Enter keywords...")
        
        with col2:
            search_button = st.button("Search", type="primary")
        
        # Advanced search options
        with st.expander("Advanced Search"):
            col1, col2 = st.columns(2)
            
            with col1:
                event_type_search = st.selectbox(
                    "Event Type",
                    ["all", "earthquake", "flood", "hurricane", "wildfire", "tornado"]
                )
                severity_search = st.selectbox(
                    "Severity",
                    ["all", "low", "medium", "high", "critical"]
                )
            
            with col2:
                verified_search = st.selectbox(
                    "Verification Status",
                    ["all", "verified", "unverified"]
                )
                date_range = st.date_input(
                    "Date Range",
                    value=[datetime.now() - timedelta(days=7), datetime.now()]
                )
        
        # Perform search
        if search_button or search_query:
            search_results = self.search_events(
                query=search_query,
                event_type=event_type_search if event_type_search != "all" else None,
                severity=severity_search if severity_search != "all" else None,
                verified=verified_search if verified_search != "all" else None
            )
            
            if search_results:
                st.success(f"Found {len(search_results)} events")
                
                # Display results
                for i, event in enumerate(search_results[:10]):  # Limit to 10 results
                    with st.expander(f"Event {i+1}: {event.get('title', 'No Title')}"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**Type:** {event.get('event_type', 'Unknown')}")
                            st.write(f"**Severity:** {event.get('severity', 'Unknown')}")
                            st.write(f"**Time:** {event.get('timestamp', 'Unknown')}")
                            st.write(f"**Source:** {event.get('source', 'Unknown')}")
                            st.write(f"**Content:** {event.get('content', 'No content')}")
                        
                        with col2:
                            verified = event.get('verified', False)
                            st.write(f"**Verified:** {'✅' if verified else '❌'}")
                            st.write(f"**Confidence:** {event.get('confidence_score', 0):.2f}")
                            
                            if event.get('location'):
                                loc = event['location']
                                st.write(f"**Location:** {loc.get('lat', 0):.4f}, {loc.get('lon', 0):.4f}")
            else:
                st.warning("No events found matching your search criteria")
    
    def render_system_status_tab(self):
        """Render system status and health"""
        st.header("⚙️ System Status")
        
        # System metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            api_status = self.check_api_health()
            st.metric("API Status", "🟢 Healthy" if api_status else "🔴 Unhealthy")
        
        with col2:
            db_status = self.check_database_health()
            st.metric("Database", "🟢 Connected" if db_status else "🔴 Disconnected")
        
        with col3:
            edge_nodes = self.get_edge_node_status()
            st.metric("Edge Nodes", f"{edge_nodes.get('online', 0)}/{edge_nodes.get('total', 0)} Online")
        
        with col4:
            storage_usage = self.get_storage_usage()
            st.metric("Storage", f"{storage_usage:.1f}%")
        
        st.markdown("---")
        
        # Detailed status information
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("API Endpoints")
            endpoints = [
                ("/", "Root endpoint"),
                ("/health", "Health check"),
                ("/events", "Get events"),
                ("/events/search", "Search events"),
                ("/events/nearby", "Nearby events")
            ]
            
            for endpoint, description in endpoints:
                status = "✅" if self.check_endpoint(endpoint) else "❌"
                st.write(f"{status} `{endpoint}` - {description}")
        
        with col2:
            st.subheader("Recent System Logs")
            logs = self.get_system_logs()
            if logs:
                for log in logs[-5:]:  # Show last 5 logs
                    timestamp = log.get('timestamp', 'Unknown')
                    level = log.get('level', 'INFO')
                    message = log.get('message', '')
                    
                    if level == 'ERROR':
                        st.error(f"`{timestamp}` {message}")
                    elif level == 'WARNING':
                        st.warning(f"`{timestamp}` {message}")
                    else:
                        st.info(f"`{timestamp}` {message}")
            else:
                st.info("No recent logs")
    
    # API integration methods
    def get_total_events(self) -> int:
        """Get total number of events"""
        try:
            response = requests.get(f"{self.api_base_url}/events/count")
            return response.json().get('count', 0)
        except:
            return 0
    
    def get_critical_events(self) -> int:
        """Get number of critical events"""
        try:
            response = requests.get(f"{self.api_base_url}/events?severity=critical")
            return len(response.json())
        except:
            return 0
    
    def get_verified_events(self) -> int:
        """Get number of verified events"""
        try:
            response = requests.get(f"{self.api_base_url}/events?verified=true")
            return len(response.json())
        except:
            return 0
    
    def get_active_locations(self) -> int:
        """Get number of active locations"""
        try:
            response = requests.get(f"{self.api_base_url}/locations/active")
            return response.json().get('count', 0)
        except:
            return 0
    
    def get_recent_events(self, days: int = 1) -> List[Dict[str, Any]]:
        """Get recent events"""
        try:
            response = requests.get(f"{self.api_base_url}/events?days={days}")
            return response.json()
        except:
            return []
    
    def get_events_with_location(self) -> List[Dict[str, Any]]:
        """Get events that have location data"""
        try:
            response = requests.get(f"{self.api_base_url}/events?has_location=true")
            return response.json()
        except:
            return []
    
    def search_events(self, query: str, event_type: str = None, 
                     severity: str = None, verified: bool = None) -> List[Dict[str, Any]]:
        """Search events with filters"""
        try:
            params = {'q': query}
            if event_type:
                params['event_type'] = event_type
            if severity:
                params['severity'] = severity
            if verified is not None:
                params['verified'] = verified
            
            response = requests.get(f"{self.api_base_url}/events/search", params=params)
            return response.json()
        except:
            return []
    
    def check_api_health(self) -> bool:
        """Check API health"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def check_database_health(self) -> bool:
        """Check database health"""
        try:
            response = requests.get(f"{self.api_base_url}/health/database", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_edge_node_status(self) -> Dict[str, int]:
        """Get edge node status"""
        try:
            response = requests.get(f"{self.api_base_url}/edge/status")
            return response.json()
        except:
            return {'total': 0, 'online': 0}
    
    def get_storage_usage(self) -> float:
        """Get storage usage percentage"""
        try:
            response = requests.get(f"{self.api_base_url}/storage/usage")
            return response.json().get('usage_percentage', 0.0)
        except:
            return 0.0
    
    def check_endpoint(self, endpoint: str) -> bool:
        """Check if an endpoint is responding"""
        try:
            response = requests.get(f"{self.api_base_url}{endpoint}", timeout=3)
            return response.status_code < 500
        except:
            return False
    
    def get_system_logs(self) -> List[Dict[str, Any]]:
        """Get recent system logs"""
        try:
            response = requests.get(f"{self.api_base_url}/logs/recent")
            return response.json()
        except:
            return []


def main():
    """Main function to run the dashboard"""
    dashboard = DisasterDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
