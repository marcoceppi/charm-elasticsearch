import os
from subprocess import check_call

from charms.reactive import (
    when,
    when_not,
    set_state,
    remove_state,
)

from charms import apt

from charmhelpers.core.hookenv import (
    log,
    config,
    status_set,
    resource_get,
)

import inspect

@when_not('jre.installed')
def check_install_path():
    # Make sure we've got the resource.
    try:
        status_set('maintenance', 'Checking for jre resource')
        jre = resource_get('jre')
    except Exception:
        message = 'Error fetching the jre resource.'
        log(message)
        status_set('blocked', message)
        return
    # We've got the resource. If it's of an expected size, install it.
    filesize = os.stat(jre).st_size
    if jre and filesize > 1000000:
        set_state('jre.targz-install')
        return
    # We've got the resource, but it doesn't appear to have downloaded properly.
    # Attempt apt installing default-jre instead.
    set_state('jre.apt-install')


@when('jre.apt-install')
@when_not('apt.installed.default-jre')
def apt_install():
    status_set('maintenance', 'Queuing default-jre for install')
    apt.queue_install(['default-jre'])


@when('apt.installed.default-jre')
def level_set():
    status_set('maintenance', 'default-jre installed')
    set_state('jre.installed')


@when('jre.targz-install')
@when_not('jre.installed')
def targz_install():
    status_set('maintenance', 'Installing jre from resource')
    jre_install_path = '/opt/jre'
    if not os.path.exists(jre_install_path):
        os.makedirs(jre_install_path)
    jre = resource_get('jre')
    command = 'tar -zxf %s -C %s --strip-components 1' % (jre, jre_install_path)
    check_call(command.split())
    command = 'update-alternatives --install /usr/bin/java java %s 100'
    command = command % os.path.join(jre_install_path, 'bin', 'java')
    check_call(command.split())
    set_state('jre.installed')
    status_set('maintenance', 'Installed jre from resource')
