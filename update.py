import subprocess
import requests
import json
import os


sign_message = "# Description: Hiddify API Expanded Edition".lower()
api_location = "hiddifypanel/panel/commercial/restapi"
user_location = "hiddifypanel/panel/user"
json_version_file_path = "/usr/local/bin/hiddify-api-expanded/version.json"
VENV_ACTIVATE_PATH="/opt/hiddify-manager/.venv/bin/activate"

def is_version_less(version1, version2):
    v1_parts = list(map(int, version1.split('.')))
    v2_parts = list(map(int, version2.split('.')))

    for part1, part2 in zip(v1_parts, v2_parts):
        if part1 < part2:
            return True
        elif part1 > part2:
            return False

    # If both versions are identical up to the available parts
    return False

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
        return True
    except Exception as e:
        print(e)
        print("Failed to install")
        return False

def get_pip_location():
    pip_location_command_venv = f"bash -c 'source {VENV_ACTIVATE_PATH} && pip3 show hiddifypanel | grep -oP \"Location: \\K.*\" && deactivate'"
    pip_location_command = "pip3 show hiddifypanel | grep -oP 'Location: \\K.*'"

    try:
        # Attempt to get pip location with the virtual environment activated
        pip_location = subprocess.check_output(pip_location_command_venv, shell=True).decode("utf-8").strip()

        if not pip_location:
            # Fallback to trying without activating the virtual environment
            pip_location = subprocess.check_output(pip_location_command, shell=True).decode("utf-8").strip()

        if not pip_location:
            print("Failed to get pip location after both attempts.")
            return False

        return pip_location

    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e.cmd}")
        print("Failed to get pip location")
        return False

    except Exception as e:
        print(f"Unexpected error: {e}")
        print("Failed to get pip location")
        return False
    #     pip_location = subprocess.check_output(pip_location_command, shell=True).decode("utf-8").strip()
    #     if not pip_location:
    #         print("Failed to get pip location")
    #         return False
    #     print(f"pip location: {pip_location}")
    #     return pip_location
    # except Exception as e:
    #     print(e)
    #     print("Failed to get pip location")
    #     return False
def get_hiddify_panel_version():
    hiddify_panel_version_command_venv = f"source {VENV_ACTIVATE_PATH} && pip3 show hiddifypanel | grep -oP 'Version: \K.*' && deactivate"
    hiddify_panel_version_command = "pip3 show hiddifypanel | grep -oP 'Version: \K.*'"
    
    hiddify_panel_version_command_venv = f"bash -c 'source {VENV_ACTIVATE_PATH} && pip3 show hiddifypanel | grep -oP \"Version: \\K.*\" && deactivate'"
    hiddify_panel_version_command = "pip3 show hiddifypanel | grep -oP 'Version: \\K.*'"

    try:
        # Attempt to get version with the virtual environment activated
        hiddify_panel_version = subprocess.check_output(hiddify_panel_version_command_venv, shell=True).decode("utf-8").strip()

        if not hiddify_panel_version:
            # Fallback to trying without activating the virtual environment
            hiddify_panel_version = subprocess.check_output(hiddify_panel_version_command, shell=True).decode("utf-8").strip()

        if not hiddify_panel_version:
            print("Failed to get hiddify panel version after both attempts.")
            return False

        return hiddify_panel_version

    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e.cmd}")
        print("Failed to get hiddify panel version")
        return False

    except Exception as e:
        print(f"Unexpected error: {e}")
        print("Failed to get hiddify panel version")
        return False
    
    # try:
    #     hiddify_panel_version = subprocess.check_output(hiddify_panel_version_command, shell=True).decode("utf-8").strip()
    #     if not hiddify_panel_version:
    #         print("Failed to get hiddify panel version")
    #         return False
    #     return hiddify_panel_version
    # except Exception as e:
    #     print(e)
    #     print("Failed to get hiddify panel version")
    #     return False
def return_file_first_line(file_path):
    try:
        with open(file_path, "r") as file:
            file = file.read()
    except Exception as e:
        print(e)
        print(f"Failed to read {file_path}")
        return False
    try:
        file = file.split("\n")[0]
    except Exception as e:
        print(e)
        print(f"Failed to split {file_path}")
        return False
    return file

def get_github_version_file():
    github_version_url = "https://raw.githubusercontent.com/B3H1Z/Hiddify-API-Expanded/main/version.json"
    try:
        github_version_file = requests.get(github_version_url).text
    except Exception as e:
        print(e)
        print("Failed to check for updates")
        return False

    try:
        check_version = json.loads(github_version_file)
    except Exception as e:
        print(e)
        print("Failed to check for updates")
        return False

    if "version" not in check_version:
        print("Failed to check for updates")
        return False
    return check_version

def json_version_file():
    try:
        with open(json_version_file_path, "r") as json_version_file:
            json_version_file = json_version_file.read()
    except Exception as e:
        print(e)
        print("Failed to read version.json")
        return False

    try:
        json_version_file = json.loads(json_version_file)
    except Exception as e:
        print(e)
        print("version.json is corrupted")
        return False

    if "version" not in json_version_file:
        print("version.json is corrupted")
        return False   
    return json_version_file



pip_location = get_pip_location()
github_version_file = get_github_version_file()
json_version_dict = json_version_file()
hiddify_panel_version = get_hiddify_panel_version()
compare_version = is_version_less(hiddify_panel_version, github_version_file["max_panel_allowed_version"])

edited_files = [
    f"{pip_location}/{api_location}/__init__.py",
    f"{pip_location}/{api_location}/resources.py",
    f"{pip_location}/{user_location}/user.py",
]

print(f"Current hiddify panel version: {hiddify_panel_version}")
print(f"Max hiddify panel allowed version: {github_version_file['max_panel_allowed_version']}")
print(f"Allowed to update: {compare_version}")
print(f"Api expanded github version: {github_version_file['version']}")
print(f"Api expanded installed version: {json_version_dict['version']}")

if not compare_version:
    print("Not allowed to Install or Update")
    exit()
print("Allowed to Install or Update")
    
need_install = False
for file in edited_files:
    if not os.path.isfile(file):
        print(f"This file not exist {file}")
        need_install = True
        break
    file_first_line = return_file_first_line(file)
    if not file_first_line:
        print(f"Header not returned {file}")
        need_install = True
        break
    if sign_message.lower() not in file_first_line.lower():
        print(f"Header not found {file}")
        need_install = True
        break
    
if need_install:
    print("Need install Again")
    if not install_or_update():
        print("Failed to install")
        exit()
    print("Installed")
    exit()

current_version = json_version_dict["version"]

if not github_version_file:
    print("Failed to check for updates")
    exit()
    
github_version = github_version_file["version"]
github_version_status = github_version_file["public"]
github_max_panel_allowed_version = github_version_file["max_panel_allowed_version"]

if is_version_less(current_version, github_version):
    print("Update available")
    print(f"Current version: {current_version}")
    print(f"Latest version: {github_version}")
    if github_version_status:
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
else:
    print("You have the latest version")
    exit()
