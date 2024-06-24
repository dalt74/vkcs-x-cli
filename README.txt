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

*** Questions and answers ***

Q: Why didn't you used <xyz>> for <something> and reinventing the whell
A: The first - because I can and the second - because I hate dependencies

Q: I want to use curl directly, can you give me a docs / API refs?
A: No problem, the source is the docs. That's simple, yep?

Q: Why not pip package?
A: I'm too lazy
