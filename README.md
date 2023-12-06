# PowerDNS Zone File Sync Script

## Description
This Python script automatically synchronizes DNS zone files to a PowerDNS server using the PowerDNS API. It monitors a directory for changes in zone files and updates the corresponding zones on the PowerDNS server. It was originally made for cPanel DNS sync to a remote PowerDNS installation. Scripts to sync changes to Cloudflare & BunnyDNS via API also exists. Please reach out if there's an interest in having these public.

## Requirements
- Python 3
- `requests` library for Python
- Access to PowerDNS API
- `inotify` library for file system monitoring

## Setup
1. **Install Python 3**:
   Ensure Python 3 is installed on your system.

2. **Install Required Python Libraries**:
   You can install the necessary libraries using pip:
   ```bash
   pip3 install requests inotify
   ```

3. **Configure PowerDNS API Access**:
   - Ensure that your PowerDNS server has API access enabled.
   - Set the `pdns_api_url` and `api_key` variables in the script to match your PowerDNS API URL and API key.

4. **Logging Setup**:
   - The script logs events to `/var/log/pdns_sync.log`. Make sure the user running the script has write permissions to this file or modify the log file path as needed.

## Running the Script
1. **Start the Script**:
   Run the script using Python 3:
   ```bash
   python3 pdns_zone_sync.py
   ```
   Replace `pdns_zone_sync.py` with the path to your script.

2. **Monitor Logs**:
   You can monitor the logs for events and errors:
   ```bash
   tail -f /var/log/pdns_sync.log
   ```

## Notes
- The script uses `inotify` to monitor for file changes in the `/var/named/` directory. Ensure this path is correct or update it according to your configuration.
- The script skips SOA records for existing zones and only updates them when creating new zones.
- It's recommended to run the script in a screen session or set it up as a service for continuous operation.

---

Remember to replace `pdns_zone_sync.py` with the actual filename of your script if it's different. Also, make sure to adjust any paths or configuration details to fit your specific setup.
