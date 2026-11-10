import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
url = "https://api.open-meteo.com/v1/forecast"
params = {
	"latitude": 22,
	"longitude": 79,
	"daily": ["sunrise", "sunset", "daylight_duration", "sunshine_duration", "temperature_2m_max", "temperature_2m_min", "apparent_temperature_max", "apparent_temperature_min", "rain_sum", "showers_sum", "snowfall_sum", "wind_speed_10m_max", "wind_gusts_10m_max", "wind_direction_10m_dominant", "precipitation_sum", "precipitation_hours", "precipitation_probability_max"],
	"hourly": ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "apparent_temperature", "precipitation_probability", "precipitation", "rain", "showers", "pressure_msl", "surface_pressure", "cloud_cover", "wind_speed_10m", "wind_direction_10m", "is_day", "sunshine_duration"],
	"models": "ukmo_seamless",
	"current": ["temperature_2m", "precipitation", "weather_code", "wind_speed_10m", "relative_humidity_2m", "rain", "showers", "is_day", "apparent_temperature", "surface_pressure", "pressure_msl", "wind_direction_10m"],
	"timezone": "auto",
	"forecast_days": 1,
}
responses = openmeteo.weather_api(url, params = params)

# Process first location. Add a for-loop for multiple locations or weather models
response = responses[0]
print(f"Coordinates: {abs(response.Latitude())}°{'S' if response.Latitude() < 0 else 'N'} {abs(response.Longitude())}°{'W' if response.Longitude() < 0 else 'E'}")
print(f"Elevation: {response.Elevation()} m asl")
print(f"Timezone: {response.Timezone()}{response.TimezoneAbbreviation()}")
print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")

# Process current data. The order of variables needs to be the same as requested.
current = response.Current()
current_temperature_2m = current.Variables(0).Value()
current_precipitation = current.Variables(1).Value()
current_weather_code = current.Variables(2).Value()
current_wind_speed_10m = current.Variables(3).Value()
current_relative_humidity_2m = current.Variables(4).Value()
current_rain = current.Variables(5).Value()
current_showers = current.Variables(6).Value()
current_is_day = current.Variables(7).Value()
current_apparent_temperature = current.Variables(8).Value()
current_surface_pressure = current.Variables(9).Value()
current_pressure_msl = current.Variables(10).Value()
current_wind_direction_10m = current.Variables(11).Value()

print(f"\nCurrent time: {current.Time()}")
print(f"Current temperature_2m: {current_temperature_2m}")
print(f"Current precipitation: {current_precipitation}")
print(f"Current weather_code: {current_weather_code}")
print(f"Current wind_speed_10m: {current_wind_speed_10m}")
print(f"Current relative_humidity_2m: {current_relative_humidity_2m}")
print(f"Current rain: {current_rain}")
print(f"Current showers: {current_showers}")
print(f"Current is_day: {current_is_day}")
print(f"Current apparent_temperature: {current_apparent_temperature}")
print(f"Current surface_pressure: {current_surface_pressure}")
print(f"Current pressure_msl: {current_pressure_msl}")
print(f"Current wind_direction_10m: {current_wind_direction_10m}")

# Process hourly data. The order of variables needs to be the same as requested.
hourly = response.Hourly()
hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
hourly_dew_point_2m = hourly.Variables(2).ValuesAsNumpy()
hourly_apparent_temperature = hourly.Variables(3).ValuesAsNumpy()
hourly_precipitation_probability = hourly.Variables(4).ValuesAsNumpy()
hourly_precipitation = hourly.Variables(5).ValuesAsNumpy()
hourly_rain = hourly.Variables(6).ValuesAsNumpy()
hourly_showers = hourly.Variables(7).ValuesAsNumpy()
hourly_pressure_msl = hourly.Variables(8).ValuesAsNumpy()
hourly_surface_pressure = hourly.Variables(9).ValuesAsNumpy()
hourly_cloud_cover = hourly.Variables(10).ValuesAsNumpy()
hourly_wind_speed_10m = hourly.Variables(11).ValuesAsNumpy()
hourly_wind_direction_10m = hourly.Variables(12).ValuesAsNumpy()
hourly_is_day = hourly.Variables(13).ValuesAsNumpy()
hourly_sunshine_duration = hourly.Variables(14).ValuesAsNumpy()

hourly_data = {
	"date": pd.date_range(
		start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
		end =  pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
		freq = pd.Timedelta(seconds = hourly.Interval()),
		inclusive = "left"
	).tz_convert(response.Timezone().decode())
}

hourly_data["temperature_2m"] = hourly_temperature_2m
hourly_data["relative_humidity_2m"] = hourly_relative_humidity_2m
hourly_data["dew_point_2m"] = hourly_dew_point_2m
hourly_data["apparent_temperature"] = hourly_apparent_temperature
hourly_data["precipitation_probability"] = hourly_precipitation_probability
hourly_data["precipitation"] = hourly_precipitation
hourly_data["rain"] = hourly_rain
hourly_data["showers"] = hourly_showers
hourly_data["pressure_msl"] = hourly_pressure_msl
hourly_data["surface_pressure"] = hourly_surface_pressure
hourly_data["cloud_cover"] = hourly_cloud_cover
hourly_data["wind_speed_10m"] = hourly_wind_speed_10m
hourly_data["wind_direction_10m"] = hourly_wind_direction_10m
hourly_data["is_day"] = hourly_is_day
hourly_data["sunshine_duration"] = hourly_sunshine_duration

hourly_dataframe = pd.DataFrame(data = hourly_data)
print("\nHourly data\n", hourly_dataframe)

# Process daily data. The order of variables needs to be the same as requested.
daily = response.Daily()
daily_sunrise = daily.Variables(0).ValuesInt64AsNumpy()
daily_sunset = daily.Variables(1).ValuesInt64AsNumpy()
daily_daylight_duration = daily.Variables(2).ValuesAsNumpy()
daily_sunshine_duration = daily.Variables(3).ValuesAsNumpy()
daily_temperature_2m_max = daily.Variables(4).ValuesAsNumpy()
daily_temperature_2m_min = daily.Variables(5).ValuesAsNumpy()
daily_apparent_temperature_max = daily.Variables(6).ValuesAsNumpy()
daily_apparent_temperature_min = daily.Variables(7).ValuesAsNumpy()
daily_rain_sum = daily.Variables(8).ValuesAsNumpy()
daily_showers_sum = daily.Variables(9).ValuesAsNumpy()
daily_snowfall_sum = daily.Variables(10).ValuesAsNumpy()
daily_wind_speed_10m_max = daily.Variables(11).ValuesAsNumpy()
daily_wind_gusts_10m_max = daily.Variables(12).ValuesAsNumpy()
daily_wind_direction_10m_dominant = daily.Variables(13).ValuesAsNumpy()
daily_precipitation_sum = daily.Variables(14).ValuesAsNumpy()
daily_precipitation_hours = daily.Variables(15).ValuesAsNumpy()
daily_precipitation_probability_max = daily.Variables(16).ValuesAsNumpy()

daily_data = {
	"date": pd.date_range(
		start = pd.to_datetime(daily.Time(), unit = "s", utc = True),
		end =  pd.to_datetime(daily.TimeEnd(), unit = "s", utc = True),
		freq = pd.Timedelta(seconds = daily.Interval()),
		inclusive = "left"
	).tz_convert(response.Timezone().decode())
}

daily_data["sunrise"] = pd.to_datetime(daily_sunrise, unit = "s", utc = True).tz_convert(response.Timezone().decode())
daily_data["sunset"] = pd.to_datetime(daily_sunset, unit = "s", utc = True).tz_convert(response.Timezone().decode())
daily_data["daylight_duration"] = daily_daylight_duration
daily_data["sunshine_duration"] = daily_sunshine_duration
daily_data["temperature_2m_max"] = daily_temperature_2m_max
daily_data["temperature_2m_min"] = daily_temperature_2m_min
daily_data["apparent_temperature_max"] = daily_apparent_temperature_max
daily_data["apparent_temperature_min"] = daily_apparent_temperature_min
daily_data["rain_sum"] = daily_rain_sum
daily_data["showers_sum"] = daily_showers_sum
daily_data["snowfall_sum"] = daily_snowfall_sum
daily_data["wind_speed_10m_max"] = daily_wind_speed_10m_max
daily_data["wind_gusts_10m_max"] = daily_wind_gusts_10m_max
daily_data["wind_direction_10m_dominant"] = daily_wind_direction_10m_dominant
daily_data["precipitation_sum"] = daily_precipitation_sum
daily_data["precipitation_hours"] = daily_precipitation_hours
daily_data["precipitation_probability_max"] = daily_precipitation_probability_max

daily_dataframe = pd.DataFrame(data = daily_data)
print("\nDaily data\n", daily_dataframe)
