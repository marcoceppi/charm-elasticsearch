import os

from apt.debfile import DebPackage

from charms.reactive import (
    when,
    when_not,
    set_state,
    remove_state,
)

from charms import apt

from charmhelpers.core.host import service_restart
from charmhelpers.core.templating import render

from charmhelpers.core.hookenv import (
    log,
    config,
    status_set,
    resource_get,
)


@when_not('elasticsearch.installed')
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
    # We've got the resource, but it doesn't appear to have downloaded properly.
    # Attempt apt installing elasticsearch instead.
    set_state('elasticsearch.apt-install')


@when('elasticsearch.apt-install')
@when_not('apt.installed.elasticsearch')
def apt_install():
    status_set('maintenance', 'Queuing dependencies for install')
    apt.queue_install(['elasticsearch'])


@when('apt.installed.elasticsearch')
def level_set():
    set_state('elasticsearch.installed')


@when('elasticsearch.deb-install')
@when_not('elasticsearch.installed')
def deb_install():
    deb = resource_get('deb')
    d = DebPackage(deb)
    d.install()
    set_state('elasticsearch.installed')


@when('elasticsearch.installed')
@when_not('elasticsearch.configured')
def configure_elasticsearch():
    status_set('maintenance', 'Configuring elasticsearch')
    # render(
    #     source = "elasticsearch.yml",
    #     target = "/etc/elasticsearch/elasticsearch.yml",
    #     owner = "root",
    #     perms = 0o644,
    #     context = {'config': hookenv.config()}
    # )
    set_state('elasticsearch.configured')
    set_state('elasticsearch.restart')


@when('config.changed')
def reconfigure():
    status_set('maintenance', 'Configuring elasticsearch')
    remove_state('elasticsearch.configured')
    set_state('elasticsearch.restart')


@when('elasticsearch.restart')
def restart():
    status_set('maintenance', 'Restarting elasticsearch')
    service_restart('elasticsearch')
    remove_state('elasticsearch.restart')
    status_set('active', 'Ready')
