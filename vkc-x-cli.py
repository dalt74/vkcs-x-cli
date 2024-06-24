import sys
import os
import requests

from cinderclient import client as cinder_lib
from keystoneclient.v3 import client as keystone_lib
from novaclient import client as nova_lib
from keystoneauth1 import loading as ks_loading
from keystoneauth1 import session as ks_session

from dataclasses import dataclass
from dataclasses import field

from typing import Any
from typing import Dict
from typing import List


def _same(v: Any) -> Any:
    return v


@dataclass
class Option:
    name: str
    keys: List[str] = field(default_factory=list)
    const_value: Any = None
    default_value: Any = None
    cast_type: Any = _same

    @staticmethod
    def build(name: str, cast_type: Any=_same) -> 'Option':
        return Option(name, cast_type=cast_type)

    def alias(self, a: str) -> 'Option':
        self.keys.append(a)
        return self

    def aliases(self, *a: str) -> 'Option':
        for v in a:
            self.keys.append(v)
        return self

    def default(self, v: Any) -> 'Option':
        self.default_value = v
        return self

    def value(self, v: Any) -> 'Option':
        self.const_value = v
        return self

    def cast(self, v: Any) -> 'Option':
        self.cast_type = v
        return self

    @property
    def need_value(self) -> bool:
        return self.const_value is None

    def matches(self, key: str) -> int:
        for k in self.keys:
            if k == key:
                return 2
            if key.startswith("%s=" % k):
                if self.need_value:
                    return 1
                raise ValueError("Argument %s rejects value" % self.name)
        return 0

    def __call__(self, v: Any) -> Any:
        return self.cast_type(v)


class CmdlineParser:
    def __init__(self) -> None:
        self._positional: List[Option] = list()
        self._named: List[Option] = list()

    def add_named(self, opt: Option) -> None:
        self._named.append(opt)

    def add_positional(self, opt: Option) -> None:
        self._positional.append(opt)

    def parse(self, items: List[str]) -> Dict[str, Any]:
        values: Dict[str, Any] = dict()
        xitems = [s for s in items]
        pos_tmp = [o for o in self._positional]
        while xitems:
            item = xitems.pop(0)
            done = False
            for opt in self._named:
                mt = opt.matches(item)
                if mt == 1:
                    values[opt.name] = opt("=".join(item.split("=")[1:]))
                    done = True
                elif mt == 2:
                    if opt.need_value:
                        values[opt.name] = opt(xitems.pop(0))
                    else:
                        values[opt.name] = opt.const_value
                    done = True
            if done:
                continue
            if len(pos_tmp) == 0:
                raise ValueError("Unsupported extra argument '%s'" % item)
            parg = pos_tmp.pop(0)
            values[parg.name] = parg(item)
        for opt in self._named:
            if opt.name not in values and opt.default_value is not None:
                values[opt.name] = opt.default_value
        for opt in pos_tmp:
            if opt.default_value is None:
                raise ValueError("Missing positional argument %s" % opt.name)
            values[opt.name] = opt.default_value
        return values


loader = ks_loading.get_plugin_loader('password')
"""
if 'OS_PROJECT_ID' in os.environ:
    auth = loader.load_from_options(auth_url=os.environ['OS_AUTH_URL'],
        username=os.environ['OS_USERNAME'],
        password=os.environ['OS_PASSWORD'],
        project_id=os.environ['OS_PROJECT_ID'],
        user_domain_name=os.environ['OS_USER_DOMAIN_NAME'],
    )
else:
    auth = loader.load_from_options(auth_url=os.environ['OS_AUTH_URL'],
        username=os.environ['OS_USERNAME'],
        password=os.environ['OS_PASSWORD'],
        user_domain_name=os.environ['OS_USER_DOMAIN_NAME'],
        project_name=os.environ['OS_PROJECT_NAME'],
        project_domain_name=os.environ['OS_PROJECT_DOMAIN_NAME'],
    )
"""

auth = loader.load_from_options(
    auth_url=os.environ['OS_AUTH_URL'],
    username=os.environ['OS_USERNAME'],
    password=os.environ['OS_PASSWORD'],
    project_id=os.environ.get('OS_PROJECT_ID'),
    project_name=os.environ.get('OS_PROJECT_NAME'),
    project_domain_id=os.environ.get('OS_PROJECT_DOMAIN_ID'),
    project_domain_name=os.environ.get('OS_PROJECT_DOMAIN_NAME'),
    user_domain_id=os.environ.get('OS_USER_DOMAIN_ID'),
    user_domain_name=os.environ.get('OS_USER_DOMAIN_NAME'),
)

session = ks_session.Session(auth=auth)

nova = nova_lib.Client('2.42',
    region_name=os.environ.get('OS_REGION_NAME', 'RegionOne'),
    endpoint_type=os.environ.get('OS_INTERFACE', 'public'),
    session=session,
)

cinder = cinder_lib.Client('3.27',
    region_name=os.environ.get('OS_REGION_NAME', 'RegionOne'),
    endpoint_type=os.environ.get('OS_INTERFACE', 'public'),
    session=session,
)

keystone = keystone_lib.Client(
    region_name=os.environ.get('OS_REGION_NAME', 'RegionOne'),
    endpoint_type=os.environ.get('OS_INTERFACE', 'public'),
    session=session,
)

parser = CmdlineParser()
parser.add_named(Option.build("volume_type").aliases("--type", "--volume_type"))
parser.add_named(Option.build("zone").aliases("--availability_zone", "--zone"))
parser.add_named(Option.build("size", int).aliases("--size_gb", "--size"))
parser.add_positional(Option("service"))
parser.add_positional(Option("action"))
parser.add_positional(Option("object_id"))

def usage():
    print("")
    print("Usage:")
    print("")
    print("vkc-x-cli volume retype <volume-id> [ --type <new_type> ] [ --zone <new_zone> ]")
    print("")


def find_volume(endpoint: str, token: str, id_or_name: str) -> str:
    url = "%s/volumes/%s" % (endpoint, id_or_name)
    reply = requests.get(
        url,
        headers={"x-auth-token": token}
    )
    if reply.status_code == 200:
        return id_or_name
    url = "%s/volumes?name=%s" % (endpoint, id_or_name.replace(" ", "+"))
    reply = requests.get(
        url,
        headers={"x-auth-token": token}
    )
    if reply.status_code < 200 or reply.status_code > 299:
        raise ValueError("Search error: %s / %s" % (reply.status_code, reply.reason))
    ret = reply.json()["volumes"]
    if len(ret) == 0:
        raise ValueError("Volume %s not found" % id_or_name)
    if len(ret) > 1:
        raise ValueError("Too many volumes matched name %s" % id_or_name)
    return ret[0]["id"]


def retype(
    client: cinder_lib.Client,
    args: Dict[str, Any]
) -> int:
    ep_url = client.client.get_endpoint()
    token = client.client.get_token()
    volume_id = find_volume(ep_url, token, args["object_id"])
    url = "%s/volumes/%s/action" % (ep_url, volume_id)
    data = dict(migration_policy="on-demand")
    if "volume_type" in args:
        data["new_type"] = args["volume_type"]
    if "zone" in args:
        data["availability_zone"] = args["zone"]
    reply = requests.post(
        url,
        headers={"x-auth-token": token},
        json={"os-retype": data}
    )
    if reply.status_code < 200 or reply.status_code > 299:
        print("Error: %s / %s" % (reply.status_code, reply.reason))
        try:
            body = reply.json()
            print(body["error"]["message"])
        except:
            print(reply.text)
        return 1
    print("Accepted")
    return 0

try:
    args = parser.parse(sys.argv[1:])
    if args["service"] == "volume":
        if args["action"] == "retype":
            sys.exit(retype(cinder, args))
    raise ValueError("Unknown command")
except Exception as err:
    print("Error: %s" % err)
    usage()
    sys.exit(1)
