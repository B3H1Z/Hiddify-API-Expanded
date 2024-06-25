#!/bin/bash
# replace __init__.py and resources.py in hiddifypanel/panel/commercial/restapi with the ones in this folder

# Define text colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
RESET='\033[0m' # Reset text color

HIDY_BOT_ID="@HidyBotGroup"
api_location="hiddifypanel/panel/commercial/restapi"
user_location="hiddifypanel/panel/user"
script_location="/usr/local/bin/hiddify-api-expanded"
base_location="/opt/Hiddify-API-Expanded" 
base_location_api="/opt/Hiddify-API-Expanded/api" 

# Function to display error messages and exit
function display_error_and_exit() {
  echo -e "${RED}Error: $1${RESET}"
  echo -e "${YELLOW}${HIDY_BOT_ID}${RESET}"
  exit 1
}

add_cron_job_if_not_exists() {
  local cron_job="$1"
  local current_crontab

  # Normalize the cron job formatting (remove extra spaces)
  cron_job=$(echo "$cron_job" | sed -e 's/^[ \t]*//' -e 's/[ \t]*$//')

  # Check if the cron job already exists in the current user's crontab
  current_crontab=$(crontab -l 2>/dev/null || true)

  if [[ -z "$current_crontab" ]]; then
    # No existing crontab, so add the new cron job
    (echo "$cron_job") | crontab -
  elif ! (echo "$current_crontab" | grep -Fq "$cron_job"); then
    # Cron job doesn't exist, so append it to the crontab
    (echo "$current_crontab"; echo "$cron_job") | crontab -
  fi
}

echo "Installing dependencies"
sudo rm -rf /usr/lib/python3/dist-packages/OpenSSL
sudo pip3 install pyopenssl
sudo pip3 install pyopenssl --upgrade

# اضافه کردن دستور تغییر مجوز‌ها
echo "Setting permissions for /opt/hiddify-manager/log/"
sudo chmod -R 777 /opt/hiddify-manager/log/

echo "Cloning repo"
repository_url="https://github.com/B3H1Z/Hiddify-API-Expanded.git"
install_dir="/opt/Hiddify-API-Expanded"
if [ -d "$install_dir" ]; then
    echo "Removing old installation"
    rm -rf "$install_dir"
fi
git clone "$repository_url" "$install_dir" || display_error_and_exit "Failed to clone the repository."
cd "$install_dir" || display_error_and_exit "Failed to change directory."

if command -v pip3 &> /dev/null; then
    version=$(pip3 show hiddifypanel | grep -oP 'Version: \K.*')
    # check is it run successfully
    if [ $? -eq 0 ]; then
        echo "HiddifyPanel version is found"
    else
        display_error_and_exit "HiddifyPanel is not installed. Please install HiddifyPanel and try again."
    fi
    pip_location=$(pip3 show hiddifypanel | grep -oP 'Location: \K.*')
    if [ $? -eq 0 ]; then
        echo "HiddifyPanel location is found"
    else
        display_error_and_exit "HiddifyPanel is not installed. Please install HiddifyPanel and try again."
    fi
    pip_location_1="$pip_location/$api_location"
    if [ -f "$script_location" ]; then
        echo "Removing old script"
        rm -rf "$script_location"
    fi
    # if folder not exist
    if [ ! -d "$script_location" ]; then
        echo "Creating folder"
        mkdir -p "$script_location"
    fi
    echo "HiddifyPanel version: $version"
    echo "HiddifyPanel location: $pip_location_1"

    # Version Example: 1.0.0
    # Split the version string into an array
    IFS='.' read -r -a version_parts <<<"$version"
    # Get the major, minor, and patch version numbers
    major_version=${version_parts[0]}
    minor_version=${version_parts[1]}
    echo "Major version: $major_version"
    echo "Minor version: $minor_version"
    echo "Version: $version"
    # if major version is 8 
    if [ "$major_version" -eq 8 ]; then
        echo "HiddifyPanel version is 8"
        # add /v8 to the base location
        base_location_api="$base_location_api/v8"
    fi
    # if major version is 10
    if [ "$major_version" -eq 10 ] && [ "$minor_version" -lt 20 ]; then
        echo "HiddifyPanel version is 10"
        base_location_api="$base_location_api/v10"
        pip_location_1="$pip_location_1/v1"
    # if minor version is 10.20
    elif [ "$major_version" -eq 10 ] && [ "$minor_version" -eq 20 ]; then
    echo "HiddifyPanel version is 10.20"
    base_location_api="$base_location_api/v10/v10.20.4"
    pip_location_1="$pip_location_1/v1"
    fi

    echo "Replacing files"
    cp "$base_location_api/__init__.py" "$pip_location_1/__init__.py"
    cp "$base_location_api/resources.py" "$pip_location_1/resources.py"
    cp "$base_location_api/user.py" "$pip_location/$user_location/user.py"
    cp "$base_location/update.py" "$script_location/update.py"

    chmod +x "$script_location/update.py"
    cp /opt/Hiddify-API-Expanded/version.json "$script_location/version.json"

    echo "Adding cron job"
    add_cron_job_if_not_exists "*/5 * * * * cd $script_location && python3 update.py"

    echo "Restarting HiddifyPanel"
    systemctl restart hiddify-panel
    #remove cache
    cd /opt
    rm -rf /opt/Hiddify-API-Expanded
    echo -e "${GREEN}Hiddify API Expanded successfully installed.${RESET}"
    
else
    display_error_and_exit "pip3 is not installed. Please install pip3 and try again."
fi
