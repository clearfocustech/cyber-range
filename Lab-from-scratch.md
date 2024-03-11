# Creating a lab from scratch

# TLDR:
- Download the ISOs identified in the inventory.txt file
- Have admin credentials to a paid licensed ESXi host or vCenter cluster (the free ESXi license doesn;t support writes through the API)
- Run the build-lab.sh script


# Install Ansible
- Install Ubuntu 22.04 with Ansible, python3-pyvmomi
- Download this repository to the Ubuntu server
- Edit the inventory file
- Download ISOs for Windows Server, 10, and 11
- Download ISOs for Ubuntu and CentOS
- Download any software MSIs defined in the installer scripts
- Run the script build-lab.sh

### System Requirements
- These playbooks call linux commands and must run on an Linux Ansible host
- These do not work on the free ESXi as it does not enable write access to the API.
- genisoimage must be installed to rebuild the Windows ISOs to make them bootable
- pyVMomi (pyhton3-pyvmomim) must be installed
- p7zip (p7zip-full) is needed to extract the Windows ISOs to make them bootable
- isomd5sum is needed to build the Linux ISO images

## What it does
- This playbook creates a new guest in VMware and installs a Windows 7, 8, 10, 11, or Server 2019 operating system on it. It assigns a static IP, disables the firewall, and enables PSRemoting. These 3 actions are sufficient to allow all follow on configuration to take place via other Ansible scripts. It also enables Remote Desktop. 
- The is accomplished by, in order: extracting the contents of an ISO downloaded from Microsoft and removing the "Press any keey to boot from CD ROM", making a new bootable ISO with the suffix -no-prompt.iso, populating values from the Ansible inventory into an autounattend.xml file, placing the autounattaend.xml on a 2nd CD-ROM/ISO image, also placing a PowerShell script(which is called in the autounattend.xml) on the 2nd ISO image which sets the IP, disables the Firewall, and enables PS-Remoting, then uploading the 2 ISO images to ESXi, then creating a nerw guest on ESXi and assigning it 2 CD-ROM drives for the 2 ISOs.

## expected ansible host variables
Looking at the example inventory is probably as good an explanation as any.
- local_admin: The acocunt name for the user with Administrator privileges. 
- local_admin_pass: The password for the above account. Also used for the Administrator account on Windows 2019.
- win_key: the license key for Windows. This determines what WIndows product is installed (Home versus Pro, Standard versus Datacenter)
- unattend: the J2 templated autounattend.xml file to use. Sampls are provided in the templates folder which can be used as-is, or modified if required.
- iso_image: The name of the ISO images file downloaded from Microsoft. Should be placed in the isos folder.
- disk_gb: Gigabytes of disk space to assign to the guest
- ram_mb: megabytes of RAM to assign the guest
- cpu_count: How many cores to assign the guest
- vm_network: The name of the virtual network in vCenter for the guest
- vsphere_hostname
- vsphere_username
- vsphere_password
- vsphere_datastore: Where to place the guest
- vsphere_iso_datastore: Where to upload the ISOs to
- esxi_hostname: the name the esxi server refers to itsefl as, not necessarily the same as DNS.

### Notes
- The License key (win_key) must match the verison and product of Windows on the ISO image. 
- The disk partitioning in autounattend.xml must match the drives and UEFI or BIOS. ESXi 7 uses EFI, so this template matches that.
- This playbook may require at least 3x the disk space of the Windows ISO you are using. It requires, the orignial, and extracted copy of the original, and a new iso made without a key press prompt. This is typically 15G plus per Windows version.
- To run this playbook from the LInux CLI: ansible-playbook ./install-windows-esxi.yml -l test-win10 -i inventory.txt -b -k -K -u root
- The esxi_host variable must be the name of the ESXi server, from its perspective (not neccessarily matching DNS)
- The script will prompt for the credentials for vsphere
- The boot_firmware for the vm (either bios or efi) must match the disk configuration in the autounattend.xml 
- The vmware guest_id is hardcoided to Windows9_64Guest, which seems to work for everything. 
- The autoattend.xml templates provided call a Powershell script to set the IP address, disable the firewall, and enable PSRemoting and Remote Desktop. 
