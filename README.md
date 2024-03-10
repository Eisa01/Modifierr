# Modifierr
Automatically modify entry to select different profiles, change the path of the newly added item, and add new tags.

Modifierr (currently) works by receving a get request from Overseerr.

# Instructions
### Modify Entries Based on Config
To create the rules of modifying an entry:
* Modify the `.env` file and input your instances `APIKEY` and `BASEURL`.
* Create as many `FOLDER_0`, `FOLDER_1` configurations needed, all with their own configurations.
* The tool will try to match any entry you add with the `M_TMDB` found in the added entry.
* Then it will apply the changes created for `_FOLDER_#,` , e.g.: `PATH` you set, or the `PROFILE`, or the `TAGS`.
### Overseerr Settings
In order for Modifierr to work, apply the following Settings in Overseerr.
* In Overseerr > Settings > Notifications > Webhook
* Tick `[✓] Enable Agent`
* Add **Webhook URL**, for example, `127.0.0.1:5252/overseerr`
* Default **JSON Payload** should work fine
* Tick the below **Notification Types**, If you want Modifierr apply changes on both request types: 
     * `[✓] Request Pending Approval`
     * `[✓] Request Automatically Approved`
* **Save the changes** and you should be ready :)

### Installation Steps
* Download / clone repo to your device
* Install Python 3
* Install Modifierr pre-requisuites
```
pip install -r requirements.txt
```
* Run with `python main.py` or `nohup python main.py &`(detached)

### Docker Installation (Manual)
* Clone this repo in your device
* Navigate to the root folder of the repo
* Run
```
docker build -t modifierr .
```
* Run the docker container with the env file passed in
```
docker run --env-file ./.env modifierr
```
# Misc
### Special Thanks
Below is list of contributors/ honorable mentions. Without the below contributions these scripts would not exist today.
* All inspiration came from [seerr-route](https://github.com/Fallenbagel/seerr-route). And because this is still not directly integrated with Sonarr / Radarr.
* Utilizes [ArrAPI](https://github.com/meisnate12/ArrAPI). A great project to make your life easier when interacting with Sonarr / Radarr
#### TODO:
* Support Sonarr / Radarr webhooks directly without Overseerr
* Option to only modify entries that have a specific tag
* Add additional tmdb categories / rules for Modifierr
* Allow modifier to do more modifications, e.g: Deleting tags, Unmonitoring, etc..
