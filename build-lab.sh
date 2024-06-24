#!/bin/bash

#sudo apt-get install p7zip-full isomd5sum genisoimage python3-pyvmomi

echo "If issues occur, you can add a ' -vvv' to the end of any ansible-playbook command in this script to help debug"

echo "Enter your vsphere username, such as administrator@vsphere.local:"
read -r VSPHERE_USERNAME
export VSPHERE_USERNAME

echo "Enter your vsphere password:"
read -rs VSPHERE_PASSWORD
export VSPHERE_PASSWORD

echo "Make sure you have linked the inventory.txt file, iso directory, and templates directory into this folder"
#ln -s ./isos ./tasks/; ln -s ./templates ./tasks/


## Run this for one of each host with a unique iso
echo "Making the Windows CD iso images bootable without prompt to continue"
ansible-playbook ./tasks/make_win_cd_bootable.yml -l win10,win2019 -i inventory.txt -b -k -K -u root --extra-vars "ansible_connection=local"
echo "If the above playbooks completed successfully, please go edit you inventory and update the iso_image variables to end with '-no-prompt.iso'"
echo "Press any key to continue"
read var

## Then update the iso_image variable for each to the -no-prompt.iso name

echo "Starting playbooks to install the hosts"
echo "Starting Windows installation"
ansible-playbook ./tasks/install-windows-esxi.yml -l win10,win11,win2019 -i inventory.txt -b -k -K -u root --extra-vars "ansible_connection=local" 

echo "Starting Linux installation"
echo "Installing Ubuntu 18 and 20"
ansible-playbook ./tasks/install-ubuntu-esxi.yml -l ubuntu20 -i inventory.txt -b -k -K -u root --extra-vars "ansible_connection=local"
echo "Installing Ubuntu 22 and 24"
ansible-playbook ./tasks/install-ubuntu22-esxi.yml -l ubuntu22,ubunt24 -i inventory.txt -b -k -K -u root --extra-vars "ansible_connection=local"
echo "Installing RedHat and variants"
ansible-playbook ./tasks/install-redhat-esxi.yml -l redhat9 -i inventory.txt -b -k -K -u root --extra-vars "ansible_connection=local"
echo "Sleeping for 6 minutes to let windows finish install"
sleep 360

## Need to update to winrm for hosts
echo  "We feed to fix DNS, we assume the Ansbible host has a different DNS server than the range, so add them to the local hosts file, via sudo."
sudo cat inventory.txt | grep ip= | awk '{print $2 " " $1}' | sed 's/ip=//' >> /etc/hosts

echo "Starting playbooks to setup ActiveDirectory"
ansible-playbook ./tasks/first-domain-controller.yml -l dc1 -i inventory.txt
echo "Sleeping for 30 seconds before joining Windows computers to the domain."
sleep 30
ansible-playbook ./tasks/join-domain.yml -l '!test-win2019'  -i inventory.txt
echo "Adding Domain users"
ansible-playbook ./tasks/domain-users.yml  -i user-inventory.txt

echo "Baselining Windows installations"
ansible-playbook ./tasks/baseline-windows.yml -l win10 -i inventory.txt
echo "Baselining Linux installations"
ansible-playbook ./tasks/baseline-linux.yml -l ubuntu22,ubuntu24 -i inventory.txt

