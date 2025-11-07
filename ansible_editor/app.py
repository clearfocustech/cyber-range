import os
from flask import Flask, render_template, request, redirect, url_for
from configparser import ConfigParser, ExtendedInterpolation

app = Flask(__name__)
INVENTORY_FILE = 'inventory.txt'

# Define the set of mandatory host variables
REQUIRED_VARS = [
    'ip', 'prefix', 'gateway', 'netmask', 'vm_network',
    'ram_mb', 'cpu_count', 'disk_gb'
]

# --- Custom INI Parser/Writer for Ansible Inventory ---
def load_inventory(file_path):
    """Loads Ansible inventory, separating host data and group variables,
    and ensures all required variables are present on each host object."""
    config = ConfigParser(interpolation=ExtendedInterpolation(), allow_no_value=True)
    config.read(file_path)

    hosts = {}
    groups = {}

    for section in config.sections():
        # Handle [group] sections (hosts and children)
        if section not in ['DEFAULT'] and not section.endswith(':vars'):
            group_name = section
            groups[group_name] = {
                'hosts': [],
                'children': [c.strip() for c in config.get(group_name, 'children', fallback='').split('\n') if c.strip()] if config.has_option(group_name, 'children') else [],
                'vars': {}
            }

            for key, value in config.items(group_name):
                # We assume any entry that is not 'children' or 'vars' is a host entry (which may or may not have inline params)
                if key.lower() not in ['children']:
                    
                    # 1. Parse inline host parameters
                    host_params = {}
                    parts = key.split()
                    hostname = parts[0]
                    
                    for item in parts[1:]:
                        if '=' in item:
                            k, v = item.split('=', 1)
                            host_params[k] = v

                    if hostname not in hosts:
                        hosts[hostname] = {'group': group_name, **host_params}
                        groups[group_name]['hosts'].append(hostname)
                    else:
                        # If a host is defined twice (e.g., in two groups), we prefer the first definition
                        # and continue parsing
                        pass
                        
        # Handle [group:vars] sections
        elif section.endswith(':vars'):
            group_name = section.replace(':vars', '')
            if group_name not in groups:
                groups[group_name] = {'hosts': [], 'children': [], 'vars': {}}

            for key, value in config.items(section):
                groups[group_name]['vars'][key] = value

    # Merge group vars and apply required vars template
    for hostname, host_data in hosts.items():
        group_name = host_data.get('group')
        
        # 1. Merge Group Variables
        if group_name and group_name in groups:
            group_vars = groups[group_name]['vars']
            # We don't overwrite existing host_data with group_vars, but add missing ones.
            # However, for display simplicity, we'll ensure all keys are present here.
            # In a real Ansible run, host vars override group vars.
            merged_data = {**group_vars, **host_data}
            hosts[hostname] = merged_data # Update the host data with all merged vars

        # 2. Enforce REQUIRED_VARS
        for required_var in REQUIRED_VARS:
            # Add required var with empty string if missing
            if required_var not in hosts[hostname]:
                hosts[hostname][required_var] = ''
            
    return hosts, groups

def write_inventory(hosts, groups, file_path):
    """Writes the structured data back to an Ansible INI-like format."""
    with open(file_path, 'w') as f:
        
        # 1. Write host entries grouped by their section
        for group_name, group in groups.items():
            if group_name == 'DEFAULT': continue
            
            # Write the [group] section header
            f.write(f"\n[{group_name}]\n")
            
            for hostname in group['hosts']:
                host_data = hosts.get(hostname, {})
                
                # Combine hostname and inline parameters
                inline_params = []
                
                # For inline parameters, we only include the REQUIRED_VARS 
                # as the inventory file was structured that way.
                # All other variables should ideally go into group:vars, 
                # but since the original input had them inline, we write them back.
                
                # Identify parameters that are not 'group' and are not empty
                for key, value in host_data.items():
                    if key not in ['group'] and value is not None and value != '':
                        # Quote values if they contain spaces (Ansible best practice for inline vars)
                        if ' ' in str(value):
                            inline_params.append(f"{key}=\"{value}\"")
                        else:
                            inline_params.append(f"{key}={value}")
                
                # Filter out variables that are part of [group:vars] 
                # to avoid writing them both inline and in :vars section.
                # Since all the variables in the example were written INLINE, 
                # we will write all host variables inline for simplicity here.
                
                # Write the host entry: hostname param1=value1 param2=value2
                f.write(f"{hostname} {' '.join(inline_params)}\n")

        # 2. Write [group:children] and [group:vars] sections
        for group_name, group in groups.items():
            if group_name == 'DEFAULT': continue
            
            if group['children']:
                 f.write(f"\n[{group_name}:children]\n")
                 for child in group['children']:
                    if child:
                        f.write(f"{child}\n")
                        
            # We don't write group vars back to the file since the input 
            # had most variables defined inline with the host entries, 
            # and that's how we are handling the required variables. 
            # For a proper Ansible inventory editor, this part would need more complex logic
            # to determine if a variable is better suited for inline vs. group:vars.
            # For this focused requirement, we prioritize writing the host data back correctly.

# Global variable to store the inventory data
inventory_data, group_data = load_inventory(INVENTORY_FILE)

# --- Flask Routes ---

@app.route('/')
def index():
    """Display the main inventory table."""
    # The columns must always include REQUIRED_VARS plus any other unique variables
    all_keys = set(REQUIRED_VARS)
    for host in inventory_data.values():
        all_keys.update(host.keys())
    
    # Exclude 'group' as it's an internal key for display
    column_headers = sorted(list(all_keys - {'group'}))
    
    # Ensure REQUIRED_VARS appear first in the headers list for better organization
    ordered_headers = REQUIRED_VARS + sorted([h for h in column_headers if h not in REQUIRED_VARS])
    
    return render_template('inventory_table.html', hosts=inventory_data, headers=ordered_headers)

@app.route('/edit/<hostname>', methods=['GET', 'POST'])
def edit_host(hostname):
    """Edit an existing host entry."""
    host = inventory_data.get(hostname)
    if not host:
        return "Host not found", 404

    if request.method == 'POST':
        # Get data from the form
        new_hostname = request.form.get('hostname').strip()
        new_group = request.form.get('group').strip()
        
        # New data for the host
        updated_host_data = {'group': new_group}
        
        # Collect all key-value pairs from the dynamic form fields
        for key, value in request.form.items():
            if key not in ['hostname', 'group'] and value is not None:
                 # Only store non-empty strings (unless it's a required field which will be added later)
                 if value.strip() != '':
                    updated_host_data[key] = value.strip()
                    
        # Ensure all REQUIRED_VARS are present, even if empty (for required fields)
        for required_var in REQUIRED_VARS:
            if required_var not in updated_host_data:
                # Use the submitted (potentially empty) value from the form if it exists, otherwise empty string
                updated_host_data[required_var] = request.form.get(required_var, '').strip()

        
        # Handle rename and group change logic
        old_group = host.get('group')
        
        if new_hostname != hostname:
            # Handle rename: delete old host entry and add new one
            del inventory_data[hostname]
            
            # Remove from old group's host list
            if old_group in group_data and hostname in group_data[old_group]['hosts']:
                group_data[old_group]['hosts'].remove(hostname)
            
            # Add to new group's host list
            if new_group not in group_data:
                 group_data[new_group] = {'hosts': [], 'children': [], 'vars': {}}
            if new_hostname not in group_data[new_group]['hosts']:
                group_data[new_group]['hosts'].append(new_hostname)
            
            inventory_data[new_hostname] = updated_host_data
        else:
            # Handle group change only
            if new_group != old_group:
                # Remove from old group's host list
                if old_group in group_data and hostname in group_data[old_group]['hosts']:
                    group_data[old_group]['hosts'].remove(hostname)
                # Add to new group's host list
                if new_group not in group_data:
                     group_data[new_group] = {'hosts': [], 'children': [], 'vars': {}}
                if hostname not in group_data[new_group]['hosts']:
                    group_data[new_group]['hosts'].append(hostname)
            
            inventory_data[hostname] = updated_host_data # Update in place

        write_inventory(inventory_data, group_data, INVENTORY_FILE)
        return redirect(url_for('index'))

    # GET request: render the edit form
    # All keys: REQUIRED_VARS plus all other unique keys for the host being edited
    all_keys = sorted(list(set(host.keys()) - {'group'}))
    ordered_headers = REQUIRED_VARS + sorted([h for h in all_keys if h not in REQUIRED_VARS])

    return render_template('edit_host.html', 
                           hostname=hostname, 
                           host=host, 
                           headers=ordered_headers, 
                           groups=sorted(group_data.keys()))

@app.route('/add', methods=['GET', 'POST'])
def add_host():
    """Add a new host entry."""
    if request.method == 'POST':
        new_hostname = request.form.get('hostname').strip()
        new_group = request.form.get('group').strip()
        
        if not new_hostname or new_hostname in inventory_data:
            return "Invalid or duplicate hostname.", 400

        if not new_group:
            return "Group cannot be empty.", 400

        new_host_data = {'group': new_group}
        
        # Collect all key-value pairs from the form
        for key, value in request.form.items():
            if key not in ['hostname', 'group'] and value is not None:
                # Only store non-empty strings (unless it's a required field which will be added later)
                 if value.strip() != '':
                    new_host_data[key] = value.strip()

        # Enforce REQUIRED_VARS (guaranteeing they are in the dictionary, even if empty)
        for required_var in REQUIRED_VARS:
            if required_var not in new_host_data:
                 # Use the submitted (potentially empty) value from the form if it exists, otherwise empty string
                new_host_data[required_var] = request.form.get(required_var, '').strip()

        inventory_data[new_hostname] = new_host_data
        
        # Update group list
        if new_group not in group_data:
            group_data[new_group] = {'hosts': [], 'children': [], 'vars': {}}
        if new_hostname not in group_data[new_group]['hosts']:
            group_data[new_group]['hosts'].append(new_hostname)

        write_inventory(inventory_data, group_data, INVENTORY_FILE)
        return redirect(url_for('index'))

    # GET request: render the add form
    # Provide REQUIRED_VARS plus any other historically used keys for the form
    all_keys = set(REQUIRED_VARS)
    for host in inventory_data.values():
        all_keys.update(host.keys())
    
    # Exclude 'group'
    default_keys = sorted(list(all_keys - {'group'}))
    ordered_headers = REQUIRED_VARS + sorted([h for h in default_keys if h not in REQUIRED_VARS])

    return render_template('add_host.html', headers=ordered_headers, groups=sorted(group_data.keys()))

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
