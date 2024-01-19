import subprocess
import requests
import json
import os
def install_or_update():
    command_install = 'sudo bash -c "$(curl -Lfo- https://raw.githubusercontent.com/B3H1Z/Hiddify-API-Expanded/main/install.sh)"'
    try:
        print("Installing...")
        # check_output will run the command and store to variable
        output = subprocess.check_output(command_install, shell=True).decode("utf-8").strip()
        if not output:
            print("Failed to install")
            return False
        print(output)
        print("Installed")
    except Exception as e:
        print(e)
        print("Failed to install")
        return False

def get_pip_location():
    pip_location_command = "pip3 show hiddifypanel | grep -oP 'Location: \K.*'"
    try:
        pip_location = subprocess.check_output(pip_location_command, shell=True).decode("utf-8").strip()
        if not pip_location:
            print("Failed to get pip location")
            return False
        print(f"pip location: {pip_location}")
        return pip_location
    except Exception as e:
        print(e)
        print("Failed to get pip location")
        return False

api_location = "hiddifypanel/panel/commercial/restapi"
user_location = "hiddifypanel/panel/user"
lock_file = "expanded.lock"
# check if expanded.lock exists
pip_location = get_pip_location()
try:
    # is file exists?
    if os.path.isfile(f"{pip_location}/{api_location}/{lock_file}") and os.path.isfile(f"{pip_location}/{user_location}/{lock_file}"):
        print("Expanded is exist")
    else:
        print("Expanded is not exist")
        if not install_or_update():
            print("Failed to install")
            exit()
        print("Installed Again")
        exit()
except Exception as e:
    print(e)
    print("Failed to check if expanded is exist")
    exit()
    


json_version_file_path = "/usr/local/bin/hiddify-api-expanded/version.json"
try:
    with open(json_version_file_path, "r") as json_version_file:
        json_version_file = json_version_file.read()
except Exception as e:
    print(e)
    print("Failed to read version.json")
    exit()

try:
    json_version_file = json.loads(json_version_file)
except Exception as e:
    print(e)
    print("version.json is corrupted")
    exit()

if "version" not in json_version_file:
    print("version.json is corrupted")
    exit()

current_version = json_version_file["version"]


github_version_url = "https://raw.githubusercontent.com/B3H1Z/Hiddify-API-Expanded/main/version.json"
try:
    github_version_file = requests.get(github_version_url).text
except Exception as e:
    print(e)
    print("Failed to check for updates")
    exit()

try:
    check_version = json.loads(github_version_file)
except Exception as e:
    print(e)
    print("Failed to check for updates")
    exit()

if "version" not in check_version:
    print("Failed to check for updates")
    exit()

github_version = check_version["version"]
github_version_status = check_version["public"]
if github_version == current_version:
    print("You are up to date")
    exit()
else:
    print("Update available")
    print(f"Current version: {current_version}")
    print(f"Latest version: {github_version}")
    if github_version_status == "public":
        print("This is a public release")
        print("Updating...")
        if not install_or_update():
            print("Failed to update")
            exit()
        print("Updated")
    else:
        print("This is a beta release")
        exit()
    exit()
