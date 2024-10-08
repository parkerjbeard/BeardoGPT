from utils.travel_format import process_travel_dates
from app.config.settings import settings 
from utils.logger import logger
from typing import Dict, Any
import traceback
import requests

class HotelSearch:
    def __init__(self):
        self.serpapi_api_key = settings.SERPAPI_API_KEY
        if not self.serpapi_api_key:
            raise ValueError("SerpAPI API key is not set in environment variables")

        self.default_params = {
            "engine": "google_hotels",
            "currency": "USD",
            "hl": "en",
            "gl": "us",
            "adults": "2",
            "children": "0",
            "rating": "8",
            "output": "json"
        }

    def search_hotels(self, travel_request: Dict[str, Any]) -> str:
        logger.debug(f"Searching hotels with travel request: {travel_request}")
        try:
            # Process and normalize the travel request
            processed_request = self._process_travel_request(travel_request)
            
            params = self._build_params(processed_request)
            response = requests.get("https://serpapi.com/search", params=params)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                return f"Failed to retrieve hotel data: {data['error']}"

            hotels_results = data.get("hotels_results", [])
            if not hotels_results:
                return "No hotels found"

            formatted_results = self._format_hotel_results(hotels_results)
            logger.debug(f"Hotel search results: {formatted_results}")
            return formatted_results
        except requests.RequestException as e:
            logger.error(f"Error searching for hotels: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Failed to retrieve hotel data: {str(e)}"

    def _process_travel_request(self, travel_request: Dict[str, Any]) -> Dict[str, Any]:
        processed_request = travel_request.copy()
        
        # Process dates
        processed_request = process_travel_dates(processed_request)
        
        return processed_request

    def _build_params(self, travel_request: Dict[str, Any]) -> Dict[str, Any]:
        params = {
            "q": travel_request["destination"],
            "check_in_date": travel_request["check_in"],
            "check_out_date": travel_request["check_out"],
            "api_key": self.serpapi_api_key,
        }

        params.update(self.default_params)
        params.update({k: v for k, v in travel_request.items() if k in self._get_optional_params()})

        return params

    def _get_optional_params(self) -> list:
        return [
            "gl", "hl", "currency", "adults", "children", "children_ages",
            "sort_by", "min_price", "max_price", "property_types", "amenities",
            "rating", "brands", "hotel_class", "free_cancellation", "special_offers",
            "eco_certified", "vacation_rentals", "bedrooms", "bathrooms",
            "next_page_token", "property_token", "no_cache", "async"
        ]

    def _format_hotel_results(self, hotels_results: list) -> str:
        formatted_output = []
        for idx, hotel in enumerate(hotels_results, 1):
            formatted_output.append(
                f"{idx}. {hotel.get('name', 'N/A')}\n"
                f"  - Price: {hotel.get('price', 'N/A')}\n"
                f"  - Rating: {hotel.get('rating', 'N/A')}/5 ({hotel.get('reviews', 'N/A')} reviews)\n"
                f"  - Address: {hotel.get('address', 'N/A')}\n"
                f"  - Description: {hotel.get('description', 'N/A')}"
            )
        return "\n\n".join(formatted_output)

    def get_hotel_details(self, property_token: str) -> str:
        logger.debug(f"Getting hotel details for property_token: {property_token}")
        try:
            params = {
                "engine": "google_hotels",
                "property_token": property_token,
                "api_key": self.serpapi_api_key,
                "output": "json"
            }
            response = requests.get("https://serpapi.com/search", params=params)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                return f"Failed to retrieve hotel details: {data['error']}"

            hotel_data = data.get("hotel_results", {})
            formatted_details = self._format_hotel_details(hotel_data)
            logger.debug(f"Hotel details: {formatted_details}")
            return formatted_details
        except requests.RequestException as e:
            logger.error(f"Error getting hotel details: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Failed to retrieve hotel details: {str(e)}"

    def _format_hotel_details(self, hotel_data: Dict[str, Any]) -> str:
        amenities = ", ".join(hotel_data.get("amenities", []))
        nearby_places = ", ".join(hotel_data.get("nearby_places", []))

        return (
            f"Name: {hotel_data.get('name', 'N/A')}\n"
            f"Address: {hotel_data.get('address', 'N/A')}\n"
            f"Phone: {hotel_data.get('phone', 'N/A')}\n"
            f"Rating: {hotel_data.get('rating', 'N/A')}/5 ({hotel_data.get('reviews', 'N/A')} reviews)\n"
            f"Price: {hotel_data.get('price', 'N/A')}\n"
            f"Website: {hotel_data.get('website', 'N/A')}\n"
            f"Check-in: {hotel_data.get('check_in_time', 'N/A')}\n"
            f"Check-out: {hotel_data.get('check_out_time', 'N/A')}\n"
            f"Description: {hotel_data.get('description', 'N/A')}\n"
            f"Amenities: {amenities}\n"
            f"Nearby Places: {nearby_places}"
        )

def create_hotel_search() -> HotelSearch:
    return HotelSearch()