import requests
import time
from datetime import datetime
from typing import Dict, List, Optional
import json
from flask import Flask, request, jsonify
from flask_cors import CORS


class TransitAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://external.transitapp.com/v3/public"
        self.headers = {
            "apiKey": self.api_key
        }

    def get_nearby_stops(self, lat, lon):
        """Get nearby stops based on latitude and longitude"""
        url = f"{self.base_url}/nearby_stops"
        params = {"lat": lat, "lon": lon}

        try:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching nearby stops: {e}")
            return None

    def get_stop_departures(self, global_stop_id):
        """Get departures for a specific stop using global_stop_id"""
        url = f"{self.base_url}/stop_departures"
        params = {"global_stop_id": global_stop_id}

        try:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching departures: {e}")
            return None

    def seconds_to_minutes(self, seconds_timestamp):
        """Convert Unix timestamp in seconds to minutes from now"""
        current_time = int(time.time())
        seconds_from_now = seconds_timestamp - current_time
        minutes_from_now = max(0, seconds_from_now // 60)
        return minutes_from_now

    def get_bus_arrival_times(self, lat: float, lon: float) -> Dict:
        """
        Main function to get bus arrival times for nearby stops
        Returns a structured JSON response for frontend consumption
        """
        response = {
            "success": False,
            "message": "",
            "data": {
                "location": {"latitude": lat, "longitude": lon},
                "stops_count": 0,
                "arrivals": []
            },
            "timestamp": datetime.now().isoformat(),
            "error": None
        }

        # Get nearby stops
        stops_data = self.get_nearby_stops(lat, lon)
        if not stops_data or "stops" not in stops_data:
            response["message"] = "No stops found or error retrieving stops"
            response["error"] = "STOPS_NOT_FOUND"
            return response

        stops_count = len(stops_data['stops'])
        response["data"]["stops_count"] = stops_count

        arrival_info = []

        # For each stop, get departure times
        for stop in stops_data["stops"]:
            stop_name = stop["stop_name"]
            global_stop_id = stop["global_stop_id"]
            distance = stop["distance"]

            departures_data = self.get_stop_departures(global_stop_id)
            if not departures_data or "route_departures" not in departures_data:
                continue

            # Process each route's departures
            for route in departures_data["route_departures"]:
                route_name = route.get("route_long_name", "Unknown Route")
                route_short_name = route.get("route_short_name", "")

                for itinerary in route.get("itineraries", []):
                    direction = itinerary.get(
                        "direction_headsign", "Unknown Direction")

                    for schedule in itinerary.get("schedule_items", []):
                        departure_time = schedule.get("departure_time")
                        scheduled_time = schedule.get(
                            "scheduled_departure_time")
                        actual_departure_time = departure_time if departure_time else scheduled_time

                        if actual_departure_time:
                            minutes_until_arrival = self.seconds_to_minutes(
                                actual_departure_time)
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
                                "departure_timestamp": actual_departure_time,
                                "scheduled_time": datetime.fromtimestamp(actual_departure_time).strftime("%I:%M %p")
                            })

        # Sort by arrival time
        arrival_info.sort(key=lambda x: x["arrival_in_minutes"])

        response["success"] = True
        response["message"] = f"Found {len(arrival_info)} upcoming departures from {stops_count} nearby stops"
        response["data"]["arrivals"] = arrival_info

        return response


# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize Transit API
API_KEY = "bd14f5800440578f5da9f690c1a4f5d79578951edb5232638f8010c60d4859e0"
transit_api = TransitAPI(API_KEY)


@app.route('/')
def index():
    """Root endpoint with API documentation"""
    return jsonify({
        "api": "Transit Bus Arrivals API",
        "version": "1.0",
        "endpoints": {
            "/": "API documentation (this page)",
            "/api/bus-arrivals": "GET - Get bus arrivals (params: lat, lon)",
            "/api/nearby-stops": "GET - Get nearby stops (params: lat, lon)",
            "/api/health": "GET - Health check"
        },
        "example": "/api/bus-arrivals?lat=39.257768&lon=-76.698649"
    })


@app.route('/api/bus-arrivals', methods=['GET'])
def get_bus_arrivals():
    """
    GET /api/bus-arrivals?lat=39.257768&lon=-76.698649
    Returns all bus arrivals for nearby stops
    """
    try:
        lat = request.args.get('lat')
        lon = request.args.get('lon')

        if lat is None or lon is None:
            return jsonify({
                "success": False,
                "message": "Missing required parameters: lat and lon",
                "error": "MISSING_PARAMETERS"
            }), 400

        lat = float(lat)
        lon = float(lon)

    except ValueError:
        return jsonify({
            "success": False,
            "message": "Invalid latitude or longitude values",
            "error": "INVALID_PARAMETERS"
        }), 400

    result = transit_api.get_bus_arrival_times(lat, lon)
    status_code = 200 if result["success"] else 404

    return jsonify(result), status_code


@app.route('/api/nearby-stops', methods=['GET'])
def get_nearby_stops():
    """
    GET /api/nearby-stops?lat=39.257768&lon=-76.698649
    Returns just the nearby stops without departure times
    """
    try:
        lat = request.args.get('lat')
        lon = request.args.get('lon')

        if lat is None or lon is None:
            return jsonify({
                "success": False,
                "message": "Missing required parameters: lat and lon",
                "error": "MISSING_PARAMETERS"
            }), 400

        lat = float(lat)
        lon = float(lon)

    except ValueError:
        return jsonify({
            "success": False,
            "message": "Invalid latitude or longitude values",
            "error": "INVALID_PARAMETERS"
        }), 400

    stops_data = transit_api.get_nearby_stops(lat, lon)

    if stops_data and "stops" in stops_data:
        return jsonify({
            "success": True,
            "message": f"Found {len(stops_data['stops'])} nearby stops",
            "data": stops_data,
            "timestamp": datetime.now().isoformat()
        }), 200
    else:
        return jsonify({
            "success": False,
            "message": "No stops found or error retrieving stops",
            "error": "STOPS_NOT_FOUND",
            "timestamp": datetime.now().isoformat()
        }), 404


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Transit API",
        "timestamp": datetime.now().isoformat()
    }), 200


if __name__ == "__main__":
    print("=" * 60)
    print("Transit API Server Starting...")
    print("=" * 60)
    print("\nAvailable endpoints:")
    print("  Root:         http://localhost:5000/")
    print("  Bus Arrivals: http://localhost:5000/api/bus-arrivals?lat=39.257768&lon=-76.698649")
    print("  Nearby Stops: http://localhost:5000/api/nearby-stops?lat=39.257768&lon=-76.698649")
    print("  Health Check: http://localhost:5000/api/health")
    print("\n" + "=" * 60)
    print("Server running on http://localhost:5000")
    print("=" * 60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
