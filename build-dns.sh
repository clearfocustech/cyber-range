#!/bin/bash

echo "Enter your vsphere username, such as administrator@vsphere.local:"
read -r VSPHERE_USERNAME
export VSPHERE_USERNAME

echo "Enter your vsphere password:"
read -rs VSPHERE_PASSWORD
export VSPHERE_PASSWORD


ansible-playbook ./tasks/install-ubuntu22-esxi.yml -l bind -i catfish-inventory.txt -b -k -K -u root --extra-vars "ansible_connection=local" -vvv

#ansible-playbook ./tasks/bind.yml -l bind -i catfish-inventory.txt --extra-vars "ansible_connection=local"

