import os
import requests
import time
from flask import Flask, request
from waitress import serve
from arrapi import SonarrAPI, RadarrAPI
from dotenv import load_dotenv

#load the .env file to find any environment variables.
load_dotenv()

# Function to load the folders and the comma seperated values
def load_config_folders(instance_type):
    instance_type_lower = instance_type.upper()
    config_folders = []
    i = 0
    while True:
        config_folder = {}
        for key, value in os.environ.items():
            prefix = f"{instance_type_lower}_FOLDER_{i}_"
            if key.startswith(prefix):
                field_name = key.replace(prefix, "")
                if '_M_' in field_name:
                    config_folder[field_name] = value.split(',')
                else:
                    config_folder[field_name] = value
        if config_folder:
            config_folders.append(config_folder)
            i += 1
        else:
            break
    return config_folders

#Set variables
overseerr_baseurl = os.getenv("OVERSEERR_BASEURL", None)
overseerr_apikey = os.getenv("OVERSEERR_APIKEY", None)
overseerr_config_folders = load_config_folders('OVERSEERR')

radarr_baseurl = os.getenv("RADARR_BASEURL", "")
radarr_apikey = os.getenv("RADARR_APIKEY", "")
radarr_config_folders = load_config_folders('RADARR')

sonarr_baseurl = os.getenv("SONARR_BASEURL", "")
sonarr_apikey = os.getenv("SONARR_APIKEY", "")
sonarr_config_folders = load_config_folders('SONARR')


sonarr = SonarrAPI(sonarr_baseurl, sonarr_apikey)
radarr = RadarrAPI(radarr_baseurl, radarr_apikey)
app = Flask(__name__)

# Handle webhook requests
@app.route('/overseerr', methods=['POST'])
def handle_request():
    post_request_data = request.get_json()
    process_request_overseerr(post_request_data)

    return ('success', 202)

# Process request data
def process_request_overseerr(post_request_data):
    # Extract the needed data from the request_data
    data_overseerr = extract_request_data_overseerr(post_request_data)
    message_overseerr = data_overseerr['message']
    request_id_overseerr = data_overseerr['request_id']
    
    # Process Overseerr Webhook test and return
    if message_overseerr == 'Check check, 1, 2, 3. Are we coming in clear?':
        return print('Overseerr Webhook test successful')

    # Prepare and get overseerr request data of tmdb
    response_tmdb_overseerr, response_tmdb_data_overseerr = get_tmdb_overseerr(post_request_data)
    
    # Modify data as per user config to prepare it for the update
    put_data_overseerr = modify_request_overseerr(post_request_data, response_tmdb_data_overseerr, overseerr_config_folders)

    # Submit the changes made to overseerr after modifications to Overseerr
    submit_modifications_overseerr(put_data_overseerr, response_tmdb_data_overseerr, request_id_overseerr)

    # Submit the auto approved modifications to Sonarr / Radarr for Overseerr
    submit_modifications_overseerr_sonarr_radarr(put_data_overseerr, post_request_data)


# Extracts the initial request data of overseerr
def extract_request_data_overseerr(post_request_data):
    # Extract data from request
    notification_type = post_request_data.get('notification_type')
    message = post_request_data.get('message')
    
    request_info = post_request_data.get('request') or {}
    request_id = request_info.get('request_id')
    
    media_data = post_request_data.get('media') or {}
    media_type = media_data.get('media_type')
    media_tmdbid = media_data.get('tmdbId')
    media_tvdbid = media_data.get('tvdbId')
        
    return {
        'notification_type': notification_type,
        'message': message,
        'request_id': request_id,
        'media_type': media_type,
        'media_tmdbid': media_tmdbid,
        'media_tvdbid': media_tvdbid
    }


# Gets the request data of overseerr
def get_tmdb_overseerr(post_request_data):
    # Extract the needed data from the request_data
    data_overseerr = extract_request_data_overseerr(post_request_data)
    media_type_overseerr = data_overseerr['media_type']
    media_tmdbid_overseerr = data_overseerr['media_tmdbid']

    # Prepare the url for the get request
    get_url_overseerr = overseerr_baseurl + f'/api/v1/{media_type_overseerr}/{media_tmdbid_overseerr}?language=en'
    get_headers_overseerr = {
        'accept': 'application/json',
        'X-Api-Key': overseerr_apikey
    }

    # Initiate the get request and store the response_data
    response = requests.get(get_url_overseerr, headers=get_headers_overseerr)
    response_data = response.json()

    return response, response_data

# Gets the request data of overseerr
def get_request_overseerr(post_request_data):
    # Extract the needed data from the request_data
    data_overseerr = extract_request_data_overseerr(post_request_data)
    request_id_overseerr = data_overseerr['request_id']

    # Prepare the url for the get request
    get_url_overseerr = overseerr_baseurl + f'/api/v1/request/{request_id_overseerr}'
    get_headers_overseerr = {
        'accept': 'application/json',
        'X-Api-Key': overseerr_apikey
    }

    # Initiate the get request and store the response_data
    response = requests.get(get_url_overseerr, headers=get_headers_overseerr)
    response_data = response.json()

    return response, response_data

# Modifies the data of overseerr
def modify_request_overseerr(post_request_data, response_data, config):

    # Extract seasons from request data
    seasons = None
    if 'extra' in post_request_data:
        for item in post_request_data['extra']:
            if item['name'] == 'Requested Seasons':
                seasons = item['value']
                break
    
    # Extract the needed data from the request_data
    data_overseerr = extract_request_data_overseerr(post_request_data)
    media_type = data_overseerr['media_type']

    # Start the logic for categorization
    put_data = None

    for folder_config in config:
        folder_conditions = []
        # define initial parameters to use ids if names are not defined
        tags_ids = [int(tag.strip()) for tag in folder_config.get('M_ADD_TAGS_ID', '').split(',') if tag.strip()]
        profile_id = int(folder_config.get('PROFILE_ID')) if folder_config.get('PROFILE_ID') is not None else None
        tags_names = folder_config.get('M_ADD_TAGS_NAME', '')

        
        # Check if media type matches the folder configuration
        if folder_config.get('TYPE') == media_type:
            # Check if tmdb_genres condition exists for the folder configuration
            if 'TMBD_GENRES' in folder_config:
                for genre in folder_config['TMBD_GENRES']:
                    if genre.startswith('!'):
                        if any(g['name'] == genre[1:] for g in response_data['genres']):
                            break  # Exclude this folder_config if any excluded genre is found
                    else:
                        folder_conditions.append(any(g['name'] == genre for g in response_data['genres']))

            # Check if tmdb_keywords condition exists for the folder configuration
            if 'TMDB_KEYWORDS' in folder_config:
                for keyword in folder_config['TMDB_KEYWORDS']:
                    if keyword.startswith('!'):
                        if any(k['name'] == keyword[1:] for k in response_data['keywords']):
                            break  # Exclude this folder_config if any excluded keyword is found
                    else:
                        folder_conditions.append(any(k['name'] == keyword for k in response_data['keywords']))

            # Check if all folder conditions are satisfied
            if all(folder_conditions):
                if media_type == 'movie':
                    # Find the ids based on tags_name if it is configured
                    if tags_names:
                        tags_ids = find_ids(radarr.all_tags(), tags_names, id_attr='id', name_attr='label')
                    
                    # use profile name instead if is configured
                    profile_name = folder_config.get('PROFILE_NAME')
                    if profile_name:
                        profile_id = find_id(radarr.quality_profile(), profile_name)
                        
                    put_data = {
                        "mediaType": media_type,
                        "rootFolder": folder_config.get('PATH')
                    }
                    # Add optional put_data
                    if profile_id is not None:
                        put_data["profileId"] = profile_id
                    if tags_ids:
                        put_data["tags"] = tags_ids
                    break  # Exit loop if a matching folder configuration is found
                elif media_type == 'tv':
                    # Find the ids based on tags_name if it is configured
                    if tags_names:
                        tags_ids = find_ids(sonarr.all_tags(), tags_names, id_attr='id', name_attr='label')
                    
                    # use profile name instead if is configured
                    profile_name = folder_config.get('PROFILE_NAME')
                    if profile_name:
                        profile_id = find_id(sonarr.quality_profile(), profile_name)

                    if seasons is not None:
                        seasons = [int(season) for season in seasons.split(',')]
                        put_data ={
                            "mediaType": media_type,
                            "seasons": seasons,
                            "rootFolder": folder_config.get('PATH')
                        }
                        # Add optional put_data
                        if profile_id is not None:
                            put_data["profileId"] = profile_id
                        if tags_ids:
                            put_data["tags"] = tags_ids
                        break  # Exit loop if a matching folder configuration is found
    return put_data

# Submits the modified content to overseerr
def submit_modifications_overseerr(put_data, response_data, request_id):
    # Prepare the url for the put request
    put_url = overseerr_baseurl + f'/api/v1/request/{request_id}'
    headers = {
        'accept': 'application/json',
        'X-Api-Key': overseerr_apikey,
        'Content-Type': 'application/json'
    }
    # Submits the put data
    if put_data:
        response = requests.put(put_url, headers=headers, json=put_data)
        modified_root_folder = put_data.get('rootFolder', '')
        title = response_data.get('title', response_data.get('name', ''))
        print(f"{title}\nRoot Folder: {modified_root_folder}")
        if response.status_code != 200:
            raise Exception(f'Error updating request status: {response.content}')
        else:
            print("Success! Overseerr request updated")
    else:
        print("No changes to submit")

def submit_modifications_overseerr_sonarr_radarr(put_data, request_data):
    # Extract the needed data from the request_data
    data_overseerr = extract_request_data_overseerr(request_data)
    notification_type_overseerr = data_overseerr['notification_type']
    media_type_overseerr = data_overseerr['media_type']
    media_tmdbid_overseerr = data_overseerr['media_tmdbid']
    media_tvdbid_overseerr = data_overseerr['media_tvdbid']
    
    # Apply logic to apply modifications only for auto approved requests
    if notification_type_overseerr == 'MEDIA_AUTO_APPROVED':
        # Get the item depending if it is movie or series
        if media_type_overseerr == 'movie':
            overseerr_target = custom_function_interval_retry(lambda: radarr.get_movie(tmdb_id=media_tmdbid_overseerr), None, 1)
            edit_multiple_function = radarr.edit_multiple_movies
        else:
            overseerr_target = custom_function_interval_retry(lambda: sonarr.get_series(tvdb_id=media_tvdbid_overseerr), None, 1)
            edit_multiple_function = sonarr.edit_multiple_series

        # Adjust put_data to match edit_movie, edit_series parameters
        adjusted_put_data = {
            "ids": [overseerr_target],  # For some reason it needs the name and ID instead of overseerr_target.id. This works :)
            "root_folder": put_data.get("rootFolder"),
            "move_files": True,
        }
        if "profileId" in put_data:
            adjusted_put_data["quality_profile"] = put_data["profileId"]
        if "tags" in put_data:
            adjusted_put_data["tags"] = put_data["tags"]
        
        # Edit the item we got based on the modifications to put_data
        edit_multiple_function(**adjusted_put_data)

# ---Utility functions---
def find_ids(all_array, config_array, id_attr='id', name_attr='name'):
    ids = []
    # Iterate over each entry in all_array to find the corresponding entry
    for entry in all_array:
        # Check if the entry has the specified name attribute
        if hasattr(entry, name_attr):
            # Extract the name attribute value
            entry_name = getattr(entry, name_attr)
            # If the entry matches any name in config_array (converted to lower case)
            if entry_name.lower() in config_array.lower():
                # Check if the entry has the specified ID attribute
                if hasattr(entry, id_attr):
                    # Extract the ID attribute value and append it to the ids list
                    ids.append(getattr(entry, id_attr))
    return ids

def find_id(all_array, config_string, id_attr='id', name_attr='name'):
    # Iterate over each entry in all_array to find the corresponding entry
    for entry in all_array:
        # Check if the entry has the specified name attribute
        if hasattr(entry, name_attr):
            # Extract the name attribute value
            entry_name = getattr(entry, name_attr)
            # If the entry matches the config_string (converted to lower case)
            if entry_name.lower() == config_string.lower():
                # Check if the entry has the specified ID attribute
                if hasattr(entry, id_attr):
                    # Return the ID attribute value as an integer
                    return int(getattr(entry, id_attr))
    # Return None if no matching entry is found
    return None
           
# Function to delay any process by using seconds
def delay(seconds):
    start_time = time.monotonic()
    while time.monotonic() - start_time < seconds:
        pass

# Function to retry function after interval with max_tries limit
def custom_function_interval_retry(parent_function, child_function=None, first_interval=0, retry_interval=1, max_retries=10):
    delay(first_interval)  # Delay for the first attempt
    retries = 0
    while retries < max_retries:
        try:
            parent_function_output = parent_function()  # Run the parent function
            if child_function is not None:
                child_function(parent_function_output)    # Run the child function, if defined
            return parent_function_output # return the parent_
        except Exception as e:
            print(f"Error: {e}. Retrying in {retry_interval} seconds...")
            delay(retry_interval)
            retries += 1
    print("Max retries reached, function failed.")

if __name__ == '__main__':
    listen_addr = os.getenv("WEBSERVER_LISTEN_ADDR", "0.0.0.0:5252")
    host, port = listen_addr.split(':')
    protocol = "https" if port == "443" else "http"
    print(f"Listening on {protocol}://{host}:{port}")    
    serve(app, host=host, port=port)
