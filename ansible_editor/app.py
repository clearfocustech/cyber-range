import os
from flask import Flask, render_template, request, redirect, url_for
from configparser import ConfigParser, ExtendedInterpolation

app = Flask(__name__)
INVENTORY_FILE = 'inventory.txt'

# --- Custom INI Parser/Writer for Ansible Inventory ---
def load_inventory(file_path):
    """Loads Ansible inventory, separating host data and group variables."""
    # Use ConfigParser to handle groups and vars
    config = ConfigParser(interpolation=ExtendedInterpolation(), allow_no_value=True)
    config.read(file_path)
    
    hosts = {}
    groups = {}

    for section in config.sections():
        # Handle [group] sections (hosts and children)
        if section not in ['DEFAULT'] and not section.endswith(':vars'):
            groups[section] = {
                'hosts': [],
                'children': config.get(section, 'children', fallback='').split('\n') if 'children' in config[section] else [],
                'vars': {} # Will populate later
            }
            
            # The uploaded file has host entries inline, not just a list of hostnames.
            # We'll treat all entries in these sections as host entries with inline variables.
            for key, value in config.items(section):
                if value is None or value == '':
                    # Host entry: key is hostname, value is parameters string
                    host_params = {}
                    # Try to parse inline parameters (e.g., ip=10.3.0.5 prefix=24)
                    try:
                        params_str = key
                        # Split by space and then by '='
                        params = dict(item.split('=', 1) for item in params_str.split() if '=' in item)
                        hostname = params_str.split()[0]
                        
                        hosts[hostname] = {'group': section, **params}
                        groups[section]['hosts'].append(hostname)
                    except ValueError:
                        # Non-host line like 'children = ...' handled separately
                        if key.lower() not in ['children']:
                            groups[section]['vars'][key] = value # Could be a simple var for the group, though none in the example
        
        # Handle [group:vars] sections
        elif section.endswith(':vars'):
            group_name = section.replace(':vars', '')
            if group_name not in groups:
                groups[group_name] = {'hosts': [], 'children': [], 'vars': {}}
            
            for key, value in config.items(section):
                groups[group_name]['vars'][key] = value
                
    # Merge group vars into host data for display
    for hostname, host_data in hosts.items():
        group_name = host_data.get('group')
        if group_name and group_name in groups:
            # Add group vars to host data (host vars take precedence, but for this display, we'll just show them all)
            for key, value in groups[group_name]['vars'].items():
                if key not in host_data:
                    host_data[key] = value

    return hosts, groups

# Global variable to store the inventory data
inventory_data, group_data = load_inventory(INVENTORY_FILE)

def write_inventory(hosts, groups, file_path):
    """Writes the structured data back to an Ansible INI-like format."""
    with open(file_path, 'w') as f:
        # 1. Write host entries grouped by their section
        for group_name, group in groups.items():
            if group_name in ['DEFAULT']: continue
            
            # Write the [group] section header
            f.write(f"\n[{group_name}]\n")
            
            # Write hosts in this group
            for hostname in group['hosts']:
                host_data = hosts.get(hostname, {})
                
                # Combine hostname and inline parameters
                inline_params = []
                for key, value in host_data.items():
                    if key not in ['group', 'hostname']: # 'group' is internal, 'hostname' is the key
                        inline_params.append(f"{key}={value}")
                
                # Write the host entry: hostname param1=value1 param2=value2
                f.write(f"{hostname} {' '.join(inline_params)}\n")

        # 2. Write [group:children] and [group:vars] sections
        for group_name, group in groups.items():
            if group_name in ['DEFAULT']: continue
            
            if group['children']:
                 f.write(f"\n[{group_name}:children]\n")
                 for child in group['children']:
                    if child.strip():
                        f.write(f"{child}\n")
                        
            if group['vars']:
                f.write(f"\n[{group_name}:vars]\n")
                for key, value in group['vars'].items():
                    f.write(f"{key}={value}\n")

# --- Flask Routes ---

@app.route('/')
def index():
    """Display the main inventory table."""
    # List of all unique keys across all hosts to build the table columns
    all_keys = set()
    for host in inventory_data.values():
        all_keys.update(host.keys())
    
    # Exclude 'group' as it's an internal key for display
    column_headers = sorted(list(all_keys - {'group'}))
    
    return render_template('inventory_table.html', hosts=inventory_data, headers=column_headers)

@app.route('/edit/<hostname>', methods=['GET', 'POST'])
def edit_host(hostname):
    """Edit an existing host entry."""
    host = inventory_data.get(hostname)
    if not host:
        return "Host not found", 404

    if request.method == 'POST':
        # Get data from the form
        new_hostname = request.form.get('hostname')
        new_group = request.form.get('group')
        
        # New data for the host
        updated_host_data = {'group': new_group}
        
        # Collect all key-value pairs from the dynamic form fields
        for key, value in request.form.items():
            if key not in ['hostname', 'group'] and value.strip():
                updated_host_data[key] = value.strip()
        
        # Handle rename: delete old host entry and add new one
        if new_hostname != hostname:
            del inventory_data[hostname]
            # Also remove from old group's host list
            if host['group'] in group_data and hostname in group_data[host['group']]['hosts']:
                group_data[host['group']]['hosts'].remove(hostname)
            
            # Add to new group's host list
            if new_group not in group_data:
                 group_data[new_group] = {'hosts': [], 'children': [], 'vars': {}}
            if new_hostname not in group_data[new_group]['hosts']:
                group_data[new_group]['hosts'].append(new_hostname)
            
            inventory_data[new_hostname] = updated_host_data
        else:
            # Handle group change
            if new_group != host['group']:
                # Remove from old group's host list
                if host['group'] in group_data and hostname in group_data[host['group']]['hosts']:
                    group_data[host['group']]['hosts'].remove(hostname)
                # Add to new group's host list
                if new_group not in group_data:
                     group_data[new_group] = {'hosts': [], 'children': [], 'vars': {}}
                if hostname not in group_data[new_group]['hosts']:
                    group_data[new_group]['hosts'].append(hostname)
            
            inventory_data[hostname] = updated_host_data # Update in place

        write_inventory(inventory_data, group_data, INVENTORY_FILE)
        return redirect(url_for('index'))

    # GET request: render the edit form
    all_keys = sorted(list(set(host.keys()) - {'group'}))
    return render_template('edit_host.html', hostname=hostname, host=host, headers=all_keys, groups=sorted(group_data.keys()))

@app.route('/add', methods=['GET', 'POST'])
def add_host():
    """Add a new host entry."""
    if request.method == 'POST':
        new_hostname = request.form.get('hostname').strip()
        new_group = request.form.get('group').strip()
        
        if not new_hostname or new_hostname in inventory_data:
            return "Invalid or duplicate hostname.", 400

        new_host_data = {'group': new_group}
        for key, value in request.form.items():
            if key not in ['hostname', 'group'] and value.strip():
                new_host_data[key] = value.strip()

        inventory_data[new_hostname] = new_host_data
        
        # Update group list
        if new_group not in group_data:
            group_data[new_group] = {'hosts': [], 'children': [], 'vars': {}}
        if new_hostname not in group_data[new_group]['hosts']:
            group_data[new_group]['hosts'].append(new_hostname)

        write_inventory(inventory_data, group_data, INVENTORY_FILE)
        return redirect(url_for('index'))

    # GET request: render the add form
    # Provide a list of all known keys for pre-populating fields
    all_keys = set()
    for host in inventory_data.values():
        all_keys.update(host.keys())
    
    # Exclude 'group' and provide all possible groups
    default_keys = sorted(list(all_keys - {'group'}))
    return render_template('add_host.html', headers=default_keys, groups=sorted(group_data.keys()))

@app.route('/delete/<hostname>', methods=['POST'])
def delete_host(hostname):
    """Delete a host entry."""
    if hostname in inventory_data:
        group_name = inventory_data[hostname]['group']
        del inventory_data[hostname]
        
        # Remove from group's host list
        if group_name in group_data and hostname in group_data[group_name]['hosts']:
            group_data[group_name]['hosts'].remove(hostname)
            
        write_inventory(inventory_data, group_data, INVENTORY_FILE)
        return redirect(url_for('index'))
    return "Host not found", 404

if __name__ == '__main__':
    # Load the initial data once the app starts
    inventory_data, group_data = load_inventory(INVENTORY_FILE)
    app.run(debug=True)
