script_location="/usr/local/bin/hiddify-api-expanded"
update_usage_cron_target_time="*/5 * * * *"

remove_cron_job_if_exists() {
    local cron_job="$1"
    local current_crontab

    # Normalize the cron job formatting (remove extra spaces)
    cron_job=$(echo "$cron_job" | sed -e 's/^[ \t]*//' -e 's/[ \t]*$//')

    # Check if the cron job already exists in the current user's crontab
    current_crontab=$(crontab -l 2>/dev/null || true)

    if [[ -z "$current_crontab" ]]; then
        # No existing crontab, so add the new cron job
        (echo "$cron_job") | crontab -
    elif (echo "$current_crontab" | grep -Fq "$cron_job"); then
        # Cron job exists, so remove it from the crontab
        (echo "$current_crontab" | grep -Fv "$cron_job") | crontab -
    fi
}

if command -v pip3 &> /dev/null; then
    version=$(pip3 show hiddifypanel | grep -oP 'Version: \K.*')
    if [ $? -eq 0 ]; then
        echo "HiddifyPanel version is found - $version"
        pip install --no-deps --force-reinstall hiddifypanel==$version
        if [ $? -eq 0 ]; then
            echo "HiddifyPanel is successfully reinstalled"
            # remove cron job
            remove_cron_job_if_exists "*/5 * * * * cd $script_location && python3 update.py"
            echo "Cron job Successfully removed"
            systemctl restart hiddify-panel
            echo "HiddifyPanel service restarted"
            echo "Hiddify-API-Expanded is successfully uninstalled"
            exit 0
        else
            echo "Failed to reinstall HiddifyPanel"
            exit 1
        fi
    else
        echo "HiddifyPanel is not installed. Please install HiddifyPanel and try again."
        exit 1
    fi
else
    echo "pip3 is not installed. Please install pip3 and try again."
    exit 1
fi