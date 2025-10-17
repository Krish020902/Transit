import requests
import time
from datetime import datetime, timedelta

class TransitAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://external.transitapp.com/v3/public"
        self.headers = {
            "apiKey": self.api_key
        }
    
    def get_nearby_stops(self, lat, lon):
        """
        Get nearby stops based on latitude and longitude
        """
        url = f"{self.base_url}/nearby_stops"
        params = {
            "lat": lat,
            "lon": lon
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching nearby stops: {e}")
            return None
    
    def get_stop_departures(self, global_stop_id):
        """
        Get departures for a specific stop using global_stop_id
        """
        url = f"{self.base_url}/stop_departures"
        params = {
            "global_stop_id": global_stop_id
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching departures for stop {global_stop_id}: {e}")
            return None
    
    def seconds_to_minutes(self, seconds_timestamp):
        """
        Convert Unix timestamp in seconds to minutes from now
        """
        current_time = int(time.time())
        seconds_from_now = seconds_timestamp - current_time
        minutes_from_now = max(0, seconds_from_now // 60)
        return minutes_from_now
    
    def get_bus_arrival_times(self, lat, lon):
        """
        Main function to get bus arrival times for nearby stops
        """
        print(f"Finding nearby stops for coordinates: {lat}, {lon}")
        
        # Step 1: Get nearby stops
        stops_data = self.get_nearby_stops(lat, lon)
        if not stops_data or "stops" not in stops_data:
            print("No stops found or error retrieving stops")
            return []
        
        print(f"Found {len(stops_data['stops'])} nearby stops")
        
        arrival_info = []
        
        # Step 2: For each stop, get departure times
        for stop in stops_data["stops"]:
            stop_name = stop["stop_name"]
            global_stop_id = stop["global_stop_id"]
            distance = stop["distance"]
            
            print(f"\nChecking departures for: {stop_name} ({distance}m away)")
            
            # Get departures for this stop
            departures_data = self.get_stop_departures(global_stop_id)
            if not departures_data or "route_departures" not in departures_data:
                continue
            
            # Step 3: Process each route's departures
            for route in departures_data["route_departures"]:
                route_name = route.get("route_long_name", "Unknown Route")
                route_short_name = route.get("route_short_name", "")
                
                for itinerary in route.get("itineraries", []):
                    direction = itinerary.get("direction_headsign", "Unknown Direction")
                    
                    for schedule in itinerary.get("schedule_items", []):
                        # Get both scheduled and real-time departure if available
                        departure_time = schedule.get("departure_time")
                        scheduled_time = schedule.get("scheduled_departure_time")
                        
                        # Use real-time if available, otherwise use scheduled
                        actual_departure_time = departure_time if departure_time else scheduled_time
                        
                        if actual_departure_time:
                            minutes_until_arrival = self.seconds_to_minutes(actual_departure_time)
                            is_real_time = schedule.get("is_real_time", False)
                            
                            arrival_info.append({
                                "stop_name": stop_name,
                                "global_stop_id": global_stop_id,
                                "route_name": route_name,
                                "route_short_name": route_short_name,
                                "direction": direction,
                                "arrival_in_minutes": minutes_until_arrival,
                                "is_real_time": is_real_time,
                                "distance_meters": distance,
                                "departure_timestamp": actual_departure_time
                            })
                            
                            time_type = "Real-time" if is_real_time else "Scheduled"
                            print(f"  - {route_name} ({route_short_name}) to {direction}: "
                                  f"{minutes_until_arrival} min ({time_type})")
        
        # Sort by arrival time (soonest first)
        arrival_info.sort(key=lambda x: x["arrival_in_minutes"])
        return arrival_info

def main():
    # Initialize the API with your key
    API_KEY = "bd14f5800440578f5da9f690c1a4f5d79578951edb5232638f8010c60d4859e0"
    transit_api = TransitAPI(API_KEY)
    
    # Coordinates from your example
    LATITUDE = 39.257768
    LONGITUDE = -76.698649
    
    # Get bus arrival times
    bus_arrivals = transit_api.get_bus_arrival_times(LATITUDE, LONGITUDE)
    
    # Display final results
    print("\n" + "="*60)
    print("BUS ARRIVAL SUMMARY")
    print("="*60)
    
    if not bus_arrivals:
        print("No upcoming buses found.")
        return
    
    for i, arrival in enumerate(bus_arrivals, 1):
        real_time_indicator = "✓" if arrival["is_real_time"] else "⏰"
        print(f"{i}. {arrival['route_short_name']} - {arrival['route_name']}")
        print(f"   Direction: {arrival['direction']}")
        print(f"   Stop: {arrival['stop_name']} ({arrival['distance_meters']}m)")
        print(f"   Arrives in: {arrival['arrival_in_minutes']} minutes {real_time_indicator}")
        print(f"   Stop ID: {arrival['global_stop_id']}")
        print()

if __name__ == "__main__":
    main()