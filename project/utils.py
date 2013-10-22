import cStringIO

import paramiko

class StringIO(object):
    def __init__(self, *args, **kwargs):
        self.s = cStringIO.StringIO(*args, **kwargs)
        self.name = kwargs.get("name", "")
    def __getattr__(self, key):
        return getattr(self.s, key)
    def __iter__(self):
        for line in self.readlines():
            yield line
    def __enter__(self):
        return self
    def __exit__(self, type, value, traceback):
        self.close()

class SSHClient(paramiko.SSHClient):
    def __init__(self, *args, **kwargs):
        super(SSHClient, self).__init__(*args, **kwargs)
    def __enter__(self):
        return self
    def __exit__(self, type, value, traceback):
        self.close()

class SFTPClient(paramiko.SFTPClient):
    def __init__(self, *args, **kwargs):
        super(SFTPClient, self).__init__(*args, **kwargs)
    def __enter__(self):
        return self
    def __exit__(self, type, value, traceback):
        self.close()

def get_sftp_connection(hostname, username, key=None, password=None, port=22):
    if key is None and password is None:
        raise Exception("no key or password")

    transport = paramiko.Transport((hostname, port))
    if key:
        pkey = paramiko.RSAKey.from_private_key(key)
        transport.connect(username=username, pkey=pkey)
    else:
        transport.connect(username=username, password=pkey)
    return SFTPClient.from_transport(transport)

def get_ssh_connection(hostname, username, key=None, password=None, port=22):
    if key is None and password is None:
        raise Exception("no key or password")

    client = SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if key:
        pkey = paramiko.RSAKey.from_private_key(key)
        client.connect(hostname, username=username, pkey=pkey, port=port)
    else:
        client.connect(hostname, username=username, password=password, port=port)
    return client