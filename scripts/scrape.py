#!/usr/bin/python

"""
BMTC GTFS Data Scraper

This script is designed to interact with the BMTC API to gather and store data about bus routes, schedules, and stops.
The collected data includes:
1. Routes: General information on bus routes.
2. Routelines: Pointwise data for individual routes.
3. Timetables: Timetable data for specific days.
4. Stoplists: Data regarding each route's stops.

The script ensures that data is saved to files in a structured manner, creating different directories as needed.
Error handling, adaptive delay, and context managers are used to ensure robust execution and error recovery.
"""

import logging
import json
import os
import requests
import time
import traceback
from datetime import datetime, timedelta
import random

# Configuring logging to store messages both in a file and display on the console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)

# Constants
FILE_EXTENSION = '.json'
ROUTE_JSON_MESSAGE = "Fetching {}.json"

# Request headers to mimic a web request from a browser
headers = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Content-Type': 'application/json',
    'lan': 'en',
    'deviceType': 'WEB',
    'Origin': 'https://bmtcwebportal.amnex.com',
    'Referer': 'https://bmtcwebportal.amnex.com/'
}

def get_routes():
    """
    Fetch the list of all routes from the BMTC API and save it to a file.

    Returns:
        response (requests.Response): The response object from the API.
    """
    response = requests.post('https://bmtcmobileapistaging.amnex.com/WebAPI/GetAllRouteList', headers=headers)
    if response.status_code == 200:
        with open("routes.json", "w") as f:
            f.write(response.text)
    else:
        logging.error("Failed to fetch routes. Status code: {}".format(response.status_code))
    return response

def get_routelines(routes):
    """
    Fetch the routeline details for all available routes.
    Each route is saved as a separate file under the 'routelines' directory.

    Args:
        routes (dict): JSON dictionary containing all the routes data.
    """
    logging.info("Fetching routelines...")
    directory_path = "routelines"
    os.makedirs(directory_path, exist_ok=True)  # Ensure directory exists
    dir_list = os.listdir(directory_path)
    for route in routes['data']:
        if (route['routeno'] + FILE_EXTENSION) in dir_list:
            continue
        adaptive_delay()
        route_id = route['routeid']
        route_no = route['routeno'].strip()
        logging.debug(ROUTE_JSON_MESSAGE.format(route_no))
        data = f'{{"routeid":{route_id}}}'
        response = requests.post('https://bmtcmobileapistaging.amnex.com/WebAPI/RoutePoints', headers=headers, data=data)
        if response.status_code == 200:
            with open(f'{directory_path}/{route_no}{FILE_EXTENSION}', 'w') as f:
                f.write(response.text)
            logging.info("Fetched {}".format(route_no))
        else:
            logging.error("Failed to fetch route points for {}. Status code: {}".format(route_no, response.status_code))
    dir_list = os.listdir(directory_path)
    logging.info("Finished fetching routelines... ({} routelines)".format(len(dir_list)))

def get_timetables(routes):
    """
    Fetch the timetables for each route, focusing only on the upcoming Monday.
    The timetable for each route is saved in separate files under the 'timetables/{day_of_week}' directory.

    Args:
        routes (dict): JSON dictionary containing all the routes data.
    """
    logging.info("Fetching timetables...")
    for day in range(1, 8):
        date = datetime.now() + timedelta(days=day)
        dow = date.strftime("%A")
        # Fetch only Monday
        if dow != "Monday":
            continue
        directory_path = f'timetables/{dow}'
        os.makedirs(directory_path, exist_ok=True)  # Ensure directory exists
        dir_list = os.listdir(directory_path)
        for route in routes['data']:
            if (route['routeno'] + FILE_EXTENSION) in dir_list:
                continue
            adaptive_delay()
            route_id = route['routeid']
            route_no = route['routeno'].strip()
            fromstation_id = route['fromstationid']
            tostation_id = route['tostationid']
            logging.debug(ROUTE_JSON_MESSAGE.format(route_no))
            data = f'{{"routeid":{route_id},"fromStationId":{fromstation_id},"toStationId":{tostation_id},"current_date":"{date.strftime("%Y-%m-%d")}T00:00:00.000Z","endtime":"{date.strftime("%Y-%m-%d")} 23:59","starttime":"{date.strftime("%Y-%m-%d")} 00:00"}}'
            response = requests.post('https://bmtcmobileapistaging.amnex.com/WebAPI/GetTimetableByRouteid_v3', headers=headers, data=data)
            if response.status_code == 200:
                with open(f'timetables/{dow}/{route_no}{FILE_EXTENSION}', 'w') as f:
                    f.write(response.text)
                logging.info("Fetched {}".format(route_no))
            else:
                logging.error("Failed to fetch timetable for {}. Status code: {}".format(route_no, response.status_code))
    dir_list = os.listdir(directory_path)
    logging.info("Finished fetching timetables... ({} timetables)".format(len(dir_list)))

def get_route_ids(routes):
    """
    Fetch and store the route IDs for each route prefix.
    Each route prefix is stored as a separate file under the 'routeids' directory.

    Args:
        routes (dict): JSON dictionary containing all the routes data.

    Returns:
        dict: Dictionary containing route numbers as keys and route parent IDs as values.
    """
    route_parents = {}
    logging.info("Fetching routeids...")
    directory_path = "routeids"
    os.makedirs(directory_path, exist_ok=True)  # Ensure directory exists
    dir_list = os.listdir(directory_path)
    pending_routes = []
    for route in routes['data']:
        if (route['routeno'].replace(" UP", "").replace(" DOWN", "") + FILE_EXTENSION) not in dir_list:
            pending_routes.append(route)
    routes_no = ([route.get('routeno') for route in pending_routes])
    routes_prefix = sorted(set([route[:3] for route in routes_no]))
    for route in routes_prefix:
        if (route + FILE_EXTENSION) in dir_list:
            continue
        adaptive_delay()
        logging.debug(ROUTE_JSON_MESSAGE.format(route))
        data = f'{{"routetext":"{route}"}}'
        response = requests.post('https://bmtcmobileapistaging.amnex.com/WebAPI/SearchRoute_v2', headers=headers, data=data)
        if response.status_code == 200:
            with open(f'{directory_path}/{route}{FILE_EXTENSION}', 'w') as f:
                f.write(response.text)
        else:
            logging.error("Failed to fetch route IDs for {}. Status code: {}".format(route, response.status_code))
    for filename in os.listdir(directory_path):
        with open(os.path.join(directory_path, filename), 'r', encoding='utf-8') as file:
            data = json.load(file)
            for route in data['data']:
                route_parents[route['routeno']] = route['routeparentid']
    logging.info("Finished fetching routeids!")
    return route_parents

def fetch_route_data(route, route_parents):
    """
    Fetch data for a specific route using the route parent ID.

    Args:
        route (str): Route number.
        route_parents (dict): Dictionary mapping route numbers to route parent IDs.

    Returns:
        tuple: Response object and routeparentname string.
    """
    routeparentname = route.replace(" UP", "").replace(" DOWN", "")
    logging.debug("Fetching {}.json with routeid {}".format(routeparentname, route_parents[routeparentname]))
    data = f'{{"routeid":{route_parents[routeparentname]},"servicetypeid":0}}'
    response = requests.post('https://bmtcmobileapistaging.amnex.com/WebAPI/SearchByRouteDetails_v4', headers=headers, data=data)
    return response, routeparentname

def save_stoplist_data(response, routeparentname, directory_path):
    """
    Save the stoplist data for a route to appropriate files.

    Args:
        response (requests.Response): Response object containing the stoplist data.
        routeparentname (str): The route's parent name.
        directory_path (str): The directory path where data should be saved.
    """
    if len(response.json().get("up", {}).get("data", [])) > 0:
        with open(f'{directory_path}/{routeparentname} UP{FILE_EXTENSION}', 'w') as f:
            f.write(response.text)
    if len(response.json().get("down", {}).get("data", [])) > 0:
        with open(f'{directory_path}/{routeparentname} DOWN{FILE_EXTENSION}', 'w') as f:
            f.write(response.text)

def get_stop_lists(routes, route_parents):
    """
    Fetch the stoplists for each route and save them under the 'stops' directory.
    Stops are fetched multiple times to ensure completion of all data.

    Args:
        routes (dict): JSON dictionary containing all the routes data.
        route_parents (dict): Dictionary mapping route numbers to route parent IDs.
    """
    logging.info("Fetching stoplists...")
    directory_path = "stops"
    os.makedirs(directory_path, exist_ok=True)  # Ensure directory exists
    dir_list = os.listdir(directory_path)
    pending_routes = [route['routeno'] for route in routes['data'] if (route['routeno'] + FILE_EXTENSION) not in dir_list]
    pending_routes.reverse()
    for _ in range(1, 100):
        for route in pending_routes:
            try:
                if (route + FILE_EXTENSION) in dir_list:
                    continue
                adaptive_delay()
                response, routeparentname = fetch_route_data(route, route_parents)
                if response.status_code != 200:
                    logging.error("Failed to fetch stoplist for {}. Status code: {}".format(routeparentname, response.status_code))
                    continue
                if response.json().get("message", "") == "Data not found":
                    continue
                save_stoplist_data(response, routeparentname, directory_path)
                pending_routes.remove(route)
                logging.info("Fetched {} with routeid {}".format(routeparentname, route_parents[routeparentname]))
            except Exception:
                logging.error("Failed {}.json".format(routeparentname))
                logging.error(traceback.format_exc())
    dir_list = os.listdir(directory_path)
    logging.info("Finished fetching stoplists ({} routes)".format(len(dir_list)))

def adaptive_delay():
    """
    Introduce a random delay to avoid overwhelming the server.
    The delay is chosen randomly between 0.5 and 1.5 seconds.
    """
    delay = random.uniform(0.5, 1.5)  # Adaptive delay between 0.5 to 1.5 seconds
    time.sleep(delay)

# Main execution
with open("routes.json", "r") as f:
    routes = json.load(f)

route_parents = get_route_ids(routes)
get_routelines(routes)
get_timetables(routes)
get_stop_lists(routes, route_parents)
