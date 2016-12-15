#!/usr/bin/env python3
# pylint: disable=c0111,c0103,c0301
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
from charmhelpers.core import hookenv, templating
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
    status_set('maintenance', 'Configuring elasticsearch')
    utils.re_edit_in_place('/etc/elasticsearch/elasticsearch.yml', {
        r'#network.host: 192.168.0.1': 'network.host: ["_site_", "_local_"]',
    })
    set_state('elasticsearch.configured')

@when('config-changed')
def reconfigure():
    status_set('maintenance', 'Configuring elasticsearch')
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
