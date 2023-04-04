#!/usr/bin/env python3

import requests
import json
import logging
import argparse

# Setup logging
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)

# Set up command line arguments
parser = argparse.ArgumentParser(description='Cloudflare DDNS updater.')
parser.add_argument('-e', '--email', type=str, help='Email used to login to Cloudflare', required=True)
parser.add_argument('-k', '--api-key', type=str, help='API token or global API key', required=True)
parser.add_argument('-z', '--zone-id', type=str, help='Zone identifier found in the "Overview" tab of your domain', required=True)
parser.add_argument('-n', '--record-name', type=str, help='Name of the DNS record you want to update', required=True)
parser.add_argument('-t', '--ttl', type=int, help='DNS TTL in seconds (default: 3600)', default=3600)
parser.add_argument('-p', '--proxy', action='store_true', help='Enable Cloudflare proxy (default: disabled)', default=False)
parser.add_argument('-s', '--site-name', type=str, help='Title of site (default: None)', default=None)
parser.add_argument('--slack-channel', type=str, help='Slack channel name (default: None)', default=None)
parser.add_argument('--slack-uri', type=str, help='Slack webhook URI (default: None)', default=None)
parser.add_argument('--discord-uri', type=str, help='Discord webhook URI (default: None)', default=None)
args = parser.parse_args()

# Set API URL
api_url = 'https://api.cloudflare.com/client/v4'

# Check for public IP
try:
    ip = requests.get('https://api.ipify.org').text.strip()
except requests.exceptions.RequestException:
    try:
        ip = requests.get('https://ipv4.icanhazip.com').text.strip()
    except requests.exceptions.RequestException:
        logging.error('Could not retrieve public IP')
        exit(1)

# Seek for the A record
headers = {
    'X-Auth-Email': args.email,
    'X-Auth-Key': args.api_key,
    'Content-Type': 'application/json'
}
params = {
    'type': 'A',
    'name': args.record_name
}
response = requests.get(f'{api_url}/zones/{args.zone_id}/dns_records', headers=headers, params=params)

# Check if the domain has an A record
if response.json()['result_info']['count'] == 0:
    logging.error(f"Record {args.record_name} does not exist, perhaps create one first? ({ip} for {args.record_name})")
    exit(1)

# Get existing IP
old_ip = response.json()['result'][0]['content']

# Compare if they're the same
if ip == old_ip:
    logging.info(f'IP {ip} for {args.record_name} has not changed.')
    exit(0)

# Change the IP@Cloudflare using the API
record_id = response.json()['result'][0]['id']
data = {
    'type': 'A',
    'name': args.record_name,
    'content': ip,
    'ttl': args.ttl,
    'proxied': args.proxy
}
response = requests.patch(f'{api_url}/zones/{args.zone_id}/dns_records/{record_id}', headers=headers, data=json.dumps(data))

# Report the status
if response.json()['success']:
    logging.info(f'IP {ip} for {args.record_name} has been updated.')
    if args.slack_uri:
