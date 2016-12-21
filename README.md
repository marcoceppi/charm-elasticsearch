# Overview

Elasticsearch is a flexible and powerful open source, distributed, real-time
search and analytics engine. Architected from the ground up for use in
distributed environments where reliability and scalability are must haves,
Elasticsearch gives you the ability to move easily beyond simple full-text
search. Through its robust set of APIs and query DSLs, plus clients for the
most popular programming languages, Elasticsearch delivers on the near
limitless promises of search technology.

Excerpt from [elasticsearch.org](http://www.elasticsearch.org/overview/ "Elasticsearch Overview")

# Usage

There are two ways to deploy elasticsearch. There is a possibility to deploy
this charm with the deb package being available on your local computer(offline)
or by downloading the package from their repository(online). Those settings can
be set in the `config.yaml`.

```
install-package:
  type: string
  default: "online"
  description: |
    This gives you the option to install elasticsearch 'offline' by giving the
    path of the debian package or 'online' to install it by adding repository
    and downloading the package.
```

### online

You can simply deploy one node with:

    juju deploy elasticsearch

You can also deploy and relate the Kibana dashboard:

    juju deploy kibana
    juju add-relation kibana elasticsearch
    juju expose kibana

This will expose the Kibana web UI, which will then act as a front end to
all subsequent Elasticsearch units.

### offline

Deploying the charm with the offline config can be done by giving the path to
the packages

`juju deploy elasticsearch --resource deb="/path/to/deb.package"`

It is possible to deploy a beat and relate it to elasticsearch as well:
```
juju deploy my-service
juju deploy metricbeat
juju add-relation metricbeat:beats-host my-service
juju add-relation metricbeat:elasticsearch elasticsearch:client
```

# Configuration

- Not all the configuration options are implemented yet
- This charm uses a java layer where you have the following config-options
    - java-mayor
    - java-flavor
    - install-type
The different config values are shown in the description of each option in the
`config.yaml`

# Contact Information

## Elasticsearch

- [Elasticsearch website](http://www.elasticsearch.org/)
