import tweepy
import pandas as pd
import geopandas as gpd
import datetime as dt
from math import radians, degrees, cos, sin, asin, atan2, sqrt
from shapely.geometry import Point

with open('./RunOnThePi/.twitter_keys.txt') as f:
    lines = [line.strip() for line in f.readlines()]

CONSUMER_KEY = lines[1]
CONSUMER_SECRET = lines[3]
ACCESS_KEY = lines[5]
ACCESS_SECRET = lines[7]

client = tweepy.Client(consumer_key=CONSUMER_KEY,
                       consumer_secret=CONSUMER_SECRET,
                       access_token=ACCESS_KEY,
                       access_token_secret=ACCESS_SECRET)


def haversine(lon1: float, lat1: float, lon2: float, lat2: float, metric=False) -> float:
    """
    Calculate the great circle distance between two points on the earth.
    Input units in degrees.
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    delta_lon = lon2 - lon1
    delta_lat = lat2 - lat1
    a = sin(delta_lat/2)**2 + cos(lat1) * cos(lat2) * sin(delta_lon/2)**2
    c = 2 * asin(sqrt(a))
    if metric:
        r = 6371 # Radius of earth in kilometers
    else:
        r = 3956 # Radius of earth in miles
    return c * r


def haversine_from_points(point1: Point, point2: Point) -> float:
    """
    Calculate the great circle distance between two points on the earth.
    Input units in degrees.
    """
    return haversine(point1.x, point1.y, point2.x, point2.y)


def bearing(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Calculate the bearing and return the direction in degrees.
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    delta_lon = lon2 - lon1
    x = cos(lat2) * sin(delta_lon)
    y = cos(lat1) * sin(lat2) - (sin(lat1) * cos(lat2) * cos(delta_lon))
    return degrees(atan2(x, y))


def bearing_from_points(point1: Point, point2: Point) -> float:
    """
    Calculate the bearing and return the direction in degrees.
    """
    return bearing(point1.x, point1.y, point2.x, point2.y)


def cardinal_direction(angle: float, letter=False):
    """
    Returns the cardinal direction when given an angle.
    """
    direction_letters = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', "NW"]
    direction_names = ['North', 'Northeast', 'East', 'Southeast', 'South', 'Southwest', 'West', 'Northwest']

    # each cardinal direction takes up 45° or ±22.5°
    angle += 22.5
    angle = angle % 360
    if letter:
        return direction_letters[int(angle / 45)]
    else:
        return direction_names[int(angle / 45)]


wildfires = gpd.read_file("./RunOnThePi/Wildland_Fire_Incident_Locations.geojson")
zipcodes = pd.read_csv("./RunOnThePi/US Zip Codes from 2013 Government Data.csv",
                       dtype={'ZIP': 'int64', 'LNG': 'float64', 'LAT': 'float64'})
zipcodes = gpd.GeoDataFrame(zipcodes,
                            geometry=gpd.points_from_xy(zipcodes.LNG, zipcodes.LAT))


def get_wildfire_update(zipcode: int, distance_range:float=100, days_ago: int = 0) -> str:
    upper_date = (dt.datetime.today() - dt.timedelta(days=days_ago)).strftime('%Y-%m-%d')
    lower_date = (dt.datetime.today() - dt.timedelta(days=days_ago + 1)).strftime('%Y-%m-%d')
    wildfires_slice = wildfires[(wildfires["FireDiscoveryDateTime"] > lower_date) & (wildfires["FireDiscoveryDateTime"] < upper_date)]

    try:
        origin = zipcodes[zipcodes.ZIP == zipcode].iloc[0].geometry
    except IndexError:
        return f"{zipcode} is not a valid zipcode"

    d = wildfires_slice.geometry.apply(lambda point: haversine_from_points(point, origin))
    wildfires_slice['distance'] = d

    report_date = (dt.datetime.today() - dt.timedelta(days=days_ago + 1)).strftime('%B %-d, %Y')

    nearest_point = wildfires_slice[wildfires_slice['distance'] == wildfires_slice['distance'].min()].iloc[0].geometry

    direction = bearing_from_points(origin, nearest_point)
    cardinal = cardinal_direction(direction)

    if d[d < 100].shape[0] == 0:
        return f"On {report_date}:\n" \
               f"There are no reported wildfires within {distance_range} miles of zipcode {zipcode}."
    elif d[d < 100].shape[0] == 1:
        return f"On {report_date}:\n" \
               f"There is {d[d < 100].shape[0]} reported wildfire within {distance_range} miles of zipcode {zipcode}.\n" \
               f"The closest reported wildfire is {d.min():.2f} miles {cardinal.lower()}."
    else:
        return f"On {report_date}:\n" \
               f"There are {d[d < 100].shape[0]} reported wildfires within {distance_range} miles of zipcode {zipcode}.\n" \
               f"The closest reported wildfire is {d.min():.2f} miles {cardinal.lower()}."


if __name__ == '__main__':
    user_zipcode = 77840
    client.create_tweet(text=get_wildfire_update(77840, days_ago=364))
