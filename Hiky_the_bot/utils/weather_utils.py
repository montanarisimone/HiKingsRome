import requests
from datetime import datetime, date, timedelta

class WeatherUtils:
    """Utility class for weather-related operations"""
    
    @staticmethod
    def get_weather_forecast(lat, lon, hike_date, api_key):
        """
        Get weather forecast for a specific date and location
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
            hike_date (str): Date in YYYY-MM-DD format
            api_key (str): OpenWeatherMap API key
            
        Returns:
            dict: Weather forecast data or None if not available
        """
        try:
            if not lat or not lon or not hike_date or not api_key:
                return None
                
            # Convert string date to date object if needed
            if isinstance(hike_date, str):
                target_date = datetime.strptime(hike_date, '%Y-%m-%d').date()
            else:
                target_date = hike_date
                
            today = date.today()
            days_diff = (target_date - today).days
            
            # For the free plan, we can only get 5 day forecast
            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': api_key,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"Weather API error: {response.status_code} - {response.text}")
                return None
                
            data = response.json()
            
            # With the free plan we can only see up to 5 days
            if days_diff > 5:
                return {
                    'temp_min': None,
                    'temp_max': None,
                    'description': 'Forecast not available yet',
                    'probability_rain': None,
                    'accuracy': 'unavailable'
                }
            
            # Find forecasts for the requested day
            target_forecasts = []
            for item in data['list']:
                forecast_date = datetime.fromtimestamp(item['dt']).date()
                if forecast_date == target_date:
                    target_forecasts.append(item)
            
            if not target_forecasts:
                return None
                
            # Calculate min and max for the day
            temps = [f['main']['temp'] for f in target_forecasts]
            rain_probs = [f.get('pop', 0) for f in target_forecasts]
            descriptions = [f['weather'][0]['description'] for f in target_forecasts]
            
            return {
                'temp_min': round(min(temps)),
                'temp_max': round(max(temps)),
                'description': max(set(descriptions), key=descriptions.count),  # most frequent description
                'probability_rain': round(max(rain_probs) * 100),  # max rain probability
                'accuracy': 'high' if days_diff <= 3 else 'medium'
            }

        except Exception as e:
            print(f"Error getting weather forecast: {e}")
            return None
    
    @staticmethod
    def format_weather_message(weather, days_until_hike):
        """
        Format weather info into a nicely formatted message
        
        Args:
            weather (dict): Weather data
            days_until_hike (int): Days until the hike
            
        Returns:
            str: Formatted weather message
        """
        if not weather:
            return "⚠️ _Weather forecast not available_"

        if weather['accuracy'] == 'unavailable':
            return ("🌡 *Weather Forecast*:\n"
                    "_Forecast not available yet. Check again 5 days before the hike_")

        return (
            f"🌡 *Weather Forecast*:\n"
            f"Temperature: {weather['temp_min']}°C - {weather['temp_max']}°C\n"
            f"Conditions: {weather['description']}\n"
            f"Chance of rain: {weather['probability_rain']}%\n\n"
            f"_{'High' if weather['accuracy'] == 'high' else 'Medium'} accuracy forecast_"
        )