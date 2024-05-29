#!/bin/bash

# Really Confirm
echo "Are you really sure you want to destroy the range ? Type the word YES to proceed, or anything else to cancel"
read confirm

if [ "$confirm" != "YES" ]; then
  echo "Exiting"
  exit
fi
echo "Proceeding to destroy range in 3 seconds !! CTRL-C to cancel."
sleep 1
echo "Proceeding to destroy range in 2 seconds !! CTRL-C to cancel."
sleep 1
echo "Proceeding to destroy range in 1 seconds !! CTRL-C to cancel."
sleep 1
#sudo apt-get install p7zip-full isomd5sum genisoimage python3-pyvmomi

echo "Enter your vsphere username, such as administrator@vsphere.local:"
read -rs VSPHERE_USERNAME
#export VSPHERE_USERNAME

echo "Enter your vsphere password:"
read -rs VSPHERE_PASSWORD
#export VSPHERE_PASSWORD

#ln -s ./isos ./tasks/; ln -s ./templates ./tasks/


## This will remove every VM in the inventory
ansible-playbook ./tasks/delete-vm-esxi.yml -l vsphere -i catfish-inventory.txt -b -k -K -u root --extra-vars "ansible_connection=local"
