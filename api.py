# api.py
import requests
import logging
import urllib3

# Disable SSL warnings for development (not recommended for production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def fetch_data_from_api(api_url, api_key):
    try:
        logging.info(f"Attempting to fetch data from API at {api_url}.")
        params = {'api-key': api_key, 'school_name': 'ALL'}
        response = requests.get(api_url, params=params, timeout=30, verify=False) # Added timeout and disabled SSL verification for development
        if response.status_code == 200:
            logging.info("Data fetched from API successfully (Status 200 OK).")
            return response.json()
        else:
            logging.error(f"Failed to retrieve data from API. Status code: {response.status_code}. Response: {response.text}")
            return None
    except requests.exceptions.Timeout:
        logging.error(f"API request timed out after 30 seconds for {api_url}.", exc_info=True)
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error while fetching data from API ({api_url}): {e}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred while fetching data from API: {e}", exc_info=True)
        return None