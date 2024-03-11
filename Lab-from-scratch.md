# Creating a lab from scratch

# Install Ansible
- Install Ubuntu 22.04 with Ansible, python3-pyvmomi
- Download this repository to the Ubuntu server
- Edit the inventory file
- Download ISOs for Windows Server, 10, and 11
- Download any software MSIs defined in the installer scripts
- Run the playbooks to build and uopload the no-boot-prompt ISOs to VMware

# Phase 1
- Run phase1 to install the domain controller

# Phase 2
- Run Phase 2 to build all other servers and workstations

# Phase 3 (optional)
- Run the user-activity playbooks at various intervals to simulate user activity
