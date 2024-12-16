#!/bin/bash

script_location="/usr/local/bin/hiddify-api-expanded"
update_usage_cron_target_time="*/5 * * * *"
VENV_ACTIVATE_PATH="/opt/hiddify-manager/.venv/bin/activate"

remove_cron_job_if_exists() {
    local cron_job="$1"
    local current_crontab

    # Normalize the cron job formatting (remove extra spaces)
    cron_job=$(echo "$cron_job" | sed -e 's/^[ \t]*//' -e 's/[ \t]*$//')

    # Get current crontab entries
    current_crontab=$(crontab -l 2>/dev/null || true)

    if [[ -n "$current_crontab" ]]; then
        if echo "$current_crontab" | grep -Fq "$cron_job"; then
            # Remove the cron job if it exists
            echo "$current_crontab" | grep -Fv "$cron_job" | crontab -
            echo "Cron job successfully removed."
        else
            echo "Cron job does not exist."
        fi
    else
        echo "No existing crontab found."
    fi
}

# Check if pip3 is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip3 is not installed. Please install pip3 and try again."
    exit 1
fi

# Source utility script and check if it exists
if [[ -f /opt/hiddify-manager/common/utils.sh ]]; then
    source /opt/hiddify-manager/common/utils.sh
else
    echo "Utility script not found. Exiting."
    exit 1
fi

version=$(get_installed_panel_version)
if [[ $? -ne 0 ]]; then
    echo "Failed to retrieve HiddifyPanel version."
    exit 1
fi

echo "HiddifyPanel version is found: $version"

# Install HiddifyPanel in the virtual environment if it exists
if [[ -f "$VENV_ACTIVATE_PATH" ]]; then
    echo "Virtual environment found."
    source "$VENV_ACTIVATE_PATH"
    pip install --no-deps --force-reinstall hiddifypanel==$version
    deactivate
else
    echo "Virtual environment not found. Installing globally."
    pip install --no-deps --force-reinstall hiddifypanel==$version
fi

if [[ $? -eq 0 ]]; then
    echo "HiddifyPanel is successfully reinstalled."
    remove_cron_job_if_exists "$update_usage_cron_target_time cd $script_location && python3 update.py"
    systemctl restart hiddify-panel
    echo "HiddifyPanel service restarted."
    echo "Hiddify-API-Expanded is successfully uninstalled."
    exit 0
else
    echo "Failed to reinstall HiddifyPanel."
    exit 1
fi
