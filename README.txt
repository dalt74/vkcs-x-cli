How to use

*** Prepare ***

Fedora/CentOS:

$ sudo dnf -y install python3-cinderclient python3-novaclient
$ . openstack-rc

Other:

$ pip install python-cidnerclient python-novaclient

*** Volume retype ***

VK Cloud online retype API is extended so you can change
availability zone with the same retype operation:

$ python3 vkc-x-cli.py volume retype MyVolume --type volume-type --zone MS1

*** VM Boot disk replace ***

(TODO)
