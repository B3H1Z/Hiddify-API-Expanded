#!/bin/bash
# replace __init__.py and resources.py in hiddifypanel/panel/commercial/restapi with the ones in this folder

#cloning repo


# Define text colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
RESET='\033[0m' # Reset text color

HIDY_BOT_ID="@HidyBotGroup"
api_location="hiddifypanel/panel/commercial/restapi"
user_location="hiddifypanel/panel/user"

# Function to display error messages and exit
function display_error_and_exit() {
  echo -e "${RED}Error: $1${RESET}"
  echo -e "${YELLOW}${HIDY_BOT_ID}${RESET}"
  exit 1
}

echo "Installing dependencies"
sudo rm -rf /usr/lib/python3/dist-packages/OpenSSL
sudo pip3 install pyopenssl
sudo pip3 install pyopenssl --upgrade

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
    script_location="/usr/local/bin/hiddify-api-expanded"
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

    echo "Replacing files"
    cp /opt/Hiddify-API-Expanded/__init__.py "$pip_location_1/__init__.py"
    cp /opt/Hiddify-API-Expanded/resources.py "$pip_location_1/resources.py"
    cp /opt/Hiddify-API-Expanded/user.py "$pip_location/$user_location/user.py"
    cp /opt/Hiddify-API-Expanded/update.py "$script_location/update.py"

    chmod +x "$script_location/update.py"
    cp /opt/Hiddify-API-Expanded/version.json "$script_location/version.json"

    echo "Adding .lock files"
    touch "$pip_location_1/expanded.lock"
    echo "loc location: $pip_location_1/expanded.lock"
    touch "$pip_location/$user_location/expanded.lock"
    echo "loc location: $pip_location/$user_location/expanded.lock"

    echo "Restarting HiddifyPanel"
    systemctl restart hiddify-panel
    #remove cache
    cd /opt
    rm -rf /opt/Hiddify-API-Expanded
    echo -e "${GREEN}Hiddify API Expanded successfully installed.${RESET}"
    
    
else
    display_error_and_exit "pip3 is not installed. Please install pip3 and try again."
fi



