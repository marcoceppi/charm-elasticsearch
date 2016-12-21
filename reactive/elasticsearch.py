#!/usr/bin/env python3
# pylint: disable=c0111,c0103,c0301
import pwd
import grp
import os
import subprocess

from subprocess import CalledProcessError
from apt.debfile import DebPackage
from jujubigdata import utils
from charms import apt
from charms.reactive import (
    hook,
    when,
    when_not,
    set_state,
    remove_state,
)
from charmhelpers.core import hookenv
from charmhelpers.core.host import service_restart
from charmhelpers.core.hookenv import (
    log,
    config,
    status_set,
    resource_get,
)


@when('java.installed')
@when_not('elasticsearch.installed')
def preinstall():
    conf = config()
    install_package = conf['install-package']
    if install_package == 'offline':
        check_install_path()
    else:
        set_state('elasticsearch.apt-install')

@when('elasticsearch.apt-install', 'java.installed')
@when_not('apt.installed.elasticsearch')
def apt_install():
    status_set('maintenance', 'Queuing dependencies for install')
    apt.queue_install(['elasticsearch'])

@when('apt.installed.elasticsearch', 'java.installed')
def level_set():
    set_state('elasticsearch.installed')

@when('elasticsearch.deb-install', 'java.installed')
@when_not('elasticsearch.installed')
def deb_install():
    try:
        deb = resource_get('deb')
        d = DebPackage(deb)
        d.install()
        set_state('elasticsearch.installed')
    except CalledProcessError:
        status_set('error', 'Elasticsearch could not be installed with package')

@when('elasticsearch.installed', 'java.installed')
@when_not('elasticsearch.configured')
def configure_elasticsearch():
    conf = config()
    status_set('maintenance', 'Configuring elasticsearch')
    path = '/etc/elasticsearch/elasticsearch.yml'
    # check if Firewall has to be enabled
    init_fw()
    utils.re_edit_in_place(path, {
        r'#cluster.name: my-application': 'cluster.name: {0}'.format(conf['cluster-name']),
    })
    utils.re_edit_in_place(path, {
        r'#network.host: 192.168.0.1': 'network.host: ["_site_", "_local_"]',
    })
    uid = pwd.getpwnam("root").pw_uid
    gid = grp.getgrnam("elasticsearch").gr_gid
    os.chown(path, uid, gid)
    hookenv.open_port(conf['port'])
    set_state('elasticsearch.configured')

@hook('config-changed')
def reconfigure():
    status_set('maintenance', 'Configuring elasticsearch')
    init_fw()
    set_state('elasticsearch.configured')

@when('elasticsearch.configured', 'java.installed')
def restart():
    try:
        status_set('maintenance', 'Restarting elasticsearch')
        service_restart('elasticsearch')
        set_state('elasticsearch.ready')
        status_set('active', 'Ready')
    except CalledProcessError:
        status_set('error', 'Could not restart elasticsearch')


@when('client.connected')
def connect_to_client(client):
    conf = config()
    cluster_name = conf['cluster-name']
    port = conf['port']
    client.configure(port, cluster_name)
    clients = client.list_connected_clients_data()
    for c in clients:
        add_fw_exception(c)

@when('client.broken')
def remove_client(client):
    subprocess.check_output(['ufw', 'reset'], input='y\n', universal_newlines=True)
    init_fw()
    clients = client.list_connected_clients_data
    for c in clients:
        if c is not None:
            add_fw_exception(c)

################################
# Install and config functions #
################################

def check_install_path():
    # Make sure we've got the resource.
    try:
        status_set('maintenance', 'Checking for resources')
        deb = resource_get('deb')
    except Exception:
        message = 'Error fetching the elasticsearch deb resource.'
        log(message)
        status_set('blocked', message)
        return
    # We've got the resource. If it's of an expected size, install it.
    filesize = os.stat(deb).st_size
    if deb and filesize > 1000000:
        set_state('elasticsearch.deb-install')
        return
    else:
            # We've got the resource, but it doesn't appear to have downloaded properly.
            # Attempt apt installing elasticsearch instead.
        set_state('elasticsearch.apt-install')

######################
# Firewall functions #
######################

def init_fw():
    conf = config()
    utils.re_edit_in_place('/etc/default/ufw', {
        r'IPV6=yes': 'IPV6=no',
    })
    if conf['firewall-enabled']:
        subprocess.check_call(['ufw', 'allow', '22'])
        subprocess.check_output(['ufw', 'enable'], input='y\n', universal_newlines=True)
    else:
        subprocess.check_output(['ufw', 'disable'])

def add_fw_exception(host_ip):
    subprocess.check_call(['ufw', 'allow', 'proto', 'tcp', 'from', host_ip,
    'to', 'any', 'port', '9200'])
