# Change Hiddify update usage cron job

# Cron job path
update_usage_cron_path="/etc/cron.d/hiddify_usage_update"

update_usage_cron_target_time="*/5 * * * *"
update_usage_cron_user="root"
update_usage_cron_command="/opt/hiddify-config/hiddify-panel/update_usage.sh"

echo "Changing permissions"
sudo chmod o+w /opt/hiddify-config/log/
# Check if cron job exists
if [ -f "$update_usage_cron_path" ]; then
    echo "Cron job exists"
    cron_job=$(cat "$update_usage_cron_path")
    echo "Current Content: $cron_job"
    # Clear content of file and add new cron job
    echo "Clearing content of file"
    echo "" > "$update_usage_cron_path"
    echo "Adding new cron job"
    echo "" >> "$update_usage_cron_path"
    # Check if cron job replaced
    cron_job=$(cat "$update_usage_cron_path")
    echo "New Content: $cron_job"
    echo "Restarting cron service"
    sudo chattr -f -i /etc/cron.d/hiddify_usage_update
    echo "Cron job successfully replaced"

else
    echo "Cron job does not exist"
fi


