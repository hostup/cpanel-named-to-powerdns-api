import inotify.adapters
import requests
import os
import logging
import traceback

# Configuration
pdns_api_url = "URL"
api_key = "KEY"
headers = {'X-API-Key': api_key}

# Set up logging
logging.basicConfig(filename='/var/log/pdns_sync.log', level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def parse_zone_file(zone_file_path, zone_exists):
    rrsets = {}
    default_ttl = 14400  # Default TTL value, adjust as needed
    last_ttl = default_ttl
    soa_provided = False
    ns_record_exists = False  # Flag to track if NS records already exist

    with open(zone_file_path, 'r') as file:
        domain_name = os.path.basename(zone_file_path).replace('.db', '') + '.'
        soa_record = False

        for line in file:
            if line.startswith(';') or line.strip() == '':
                continue

            if 'SOA' in line and '(' in line:
                soa_record = True
                soa_provided = True
                if zone_exists:
                    continue  # Skip SOA if zone exists
                continue

            if soa_record:
                if ')' in line:
                    soa_record = False
                continue

            parts = line.split()
            if len(parts) < 4:
                continue

            name = parts[0]
            if 'IN' not in parts:
                continue  # Skip if 'IN' is not in the line

            in_index = parts.index('IN')
            ttl = last_ttl if parts[in_index - 1].isdigit() else default_ttl
            last_ttl = int(parts[in_index - 1]) if parts[in_index - 1].isdigit() else last_ttl

            rtype = parts[in_index + 1]
            if zone_exists and rtype in ['NS', 'SOA']:
                continue

            if rtype == 'NS':
                ns_record_exists = True  # Set flag if NS record is found

            rdata = ' '.join(parts[in_index + 2:])
            if name == '@':
                name = domain_name
            elif not name.endswith('.'):
                name += f".{domain_name}"

            key = (name, rtype)
            if key not in rrsets:
                rrsets[key] = {
                    "name": name,
                    "type": rtype,
                    "ttl": ttl,
                    "records": []
                }
            rrsets[key]["records"].append({"content": rdata, "disabled": False})

        if not soa_provided and not zone_exists:
            # Add default SOA record for new zones
            default_soa = "ns1.hostup.se. hostmaster." + domain_name + " 2023120501 10800 3600 604800 3600"
            rrsets[(domain_name, "SOA")] = {
                "name": domain_name,
                "type": "SOA",
                "ttl": default_ttl,
                "records": [{"content": default_soa, "disabled": False}]
            }

        if not ns_record_exists and not zone_exists:
            # Add NS records only if they don't already exist in the zone file
            ns_records = [
                {"content": "ns1.hostup.se.", "disabled": False},
                {"content": "ns2.hostup.se.", "disabled": False}
            ]
            ns_record_set = {
                "name": domain_name,
                "type": "NS",
                "ttl": 3600,
                "records": ns_records
            }
            rrsets.append(ns_record_set)

    return list(rrsets.values())

def process_zone_file(zone_file_path):
    domain_name = os.path.basename(zone_file_path).replace('.db', '')

    try:
        logging.info(f"Processing zone file: {zone_file_path}")

        url = f"{pdns_api_url}/servers/localhost/zones/{domain_name}"
        response = requests.get(url, headers=headers)
        logging.info(f"GET request to {url}. Response: {response.status_code}, Body: {response.text}")

        zone_exists = response.status_code == 200
        if zone_exists:
            update_zone(domain_name, zone_file_path, zone_exists)
        else:
            create_zone(domain_name, zone_file_path)
    except Exception as e:
        logging.error(f"Error processing {zone_file_path}: {e}")
        logging.error(traceback.format_exc())

def create_zone(domain_name, zone_file_path):
    # Parse the zone file to get the record sets. Set zone_exists to False for new zone creation
    records = parse_zone_file(zone_file_path, False)

    # Prepare the payload for API request
    payload = {
        "name": f"{domain_name}.",
        "kind": "Native",
        "rrsets": records
    }

    # API request to create the new zone
    url = f"{pdns_api_url}/servers/localhost/zones"
    try:
        response = requests.post(url, headers=headers, json=payload)
        logging.info(f"POST request to {url}. Response: {response.status_code}, Body: {response.text}")
    except Exception as e:
        logging.error(f"Error creating zone {domain_name}: {e}")
        logging.error(traceback.format_exc())

def update_zone(domain_name, zone_file_path, zone_exists):
    records = parse_zone_file(zone_file_path, zone_exists)
    payload = {
        "rrsets": [
            {
                "name": record["name"],
                "type": record["type"],
                "ttl": record["ttl"],
                "changetype": "REPLACE",
                "records": record["records"]
            } for record in records
        ]
    }
    url = f"{pdns_api_url}/servers/localhost/zones/{domain_name}"
    try:
        response = requests.patch(url, headers=headers, json=payload)
        logging.info(f"PATCH request to {url}. Response: {response.status_code}, Body: {response.text}")
    except Exception as e:
        logging.error(f"Error updating zone {domain_name}: {e}")
        logging.error(traceback.format_exc())

def main():
    i = inotify.adapters.Inotify()
    i.add_watch('/var/named/', mask=inotify.constants.IN_CLOSE_WRITE)

    for event in i.event_gen(yield_nones=False):
        (_, type_names, path, filename) = event

        if filename.endswith('.db'):
            logging.info(f"Detected change in: {filename}")
            process_zone_file(os.path.join(path, filename))

if __name__ == "__main__":
    main()
