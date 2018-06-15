#!/usr/bin/env python

# Created by Wazuh, Inc. <info@wazuh.com>.
# This program is a free software; you can redistribute it and/or modify it under the terms of GPLv2

import json
from wazuh.exception import WazuhException
from wazuh import common
from wazuh.cluster.cluster import read_config, check_cluster_config, get_status_json
from wazuh.cluster.internal_socket import execute
from wazuh.utils import sort_array, search_array, cut_array

## Requests

def get_nodes(filter_list_nodes=None):
    request="get_nodes {}"
    nodes = execute(request)

    if nodes.get("err"):
        response = nodes
    else:
        response = {"items":{}, "node_error":[]}
        response["items"] = {node:node_info for node, node_info in nodes.items() if not filter_list_nodes or node in filter_list_nodes}
        if filter_list_nodes:
            response["node_error"] = [node for node in filter_list_nodes if node not in response["items"]]
    return response


def get_nodes_api(filter_node=None, filter_type=None, offset=0, limit=common.database_limit, sort=None, search=None, select=None):
    request="get_nodes {}"
    nodes = execute(request)

    if nodes.get("err"):
        raise WazuhException(3016, "{}".format(nodes['err']))

    valid_select_fiels = {"name", "version", "type", "ip"}
    valid_types = {"client", "master"}
    select_fields_param = {}

    if select:
        select_fields_param = set(select['fields'])
        if not select_fields_param.issubset(valid_select_fiels):
            incorrect_fields = select_fields_param - valid_select_fiels
            raise WazuhException(1724, "Allowed select fields: {0}. Fields {1}".\
                    format(', '.join(list(valid_select_fiels)), ', '.join(incorrect_fields)))
    if filter_type:
        if not filter_type in valid_types:
            raise WazuhException(1728, "{0} is not valid. Allowed types: {1}.".format(filter_type, ', '.join(list(valid_types))))

    response = {"items":[], "totalItems":0}
    for node, data in nodes.items():
        if (filter_node and node != filter_node) or (filter_type and data['type'] not in filter_type):
            continue
        if select:
            filtered_node = {}
            for field in select_fields_param:
                filtered_node.update({field:data[field]})
        else:
            filtered_node = data
        response["items"].append(filtered_node)

    if filter_node:
        if len(response["items"]):
            return response["items"][0]
        else:
            raise WazuhException(1730, "{0}.".format(filter_node))

    if search:
        response["items"] = search_array(response['items'], search['value'], search['negation'], fields=['name','type','version','ip'])
    if sort:
        response["items"] = sort_array(response['items'], sort['fields'], sort['order'])

    response["totalItems"] = len(response["items"])

    if limit:
        response["items"] = cut_array(response["items"],int(offset),int(limit))

    return response


def get_healthcheck(filter_node=None):
    request="get_health {}".format(filter_node)
    return execute(request)


def sync(filter_node=None):
    request = "sync {}".format(filter_node) if filter_node else "sync"
    return execute(request)


def get_files(filter_file_list=None, filter_node_list=None):
    request = "get_files {}".format(filter_file_list) if not filter_node_list else "get_files {}%--%{}".format(filter_file_list, filter_node_list)
    return execute(request)


def get_agents(filter_status, filter_node):
    filter_status = "all" if not filter_status else filter_status
    filter_node = "all" if not filter_node else filter_node

    input_json = {'function': '/agents', 'from_cluster': False, 'limit': 0,
                  'arguments': {'filters':{'status': filter_status, 'node_name': filter_node},
                                'select': {'fields': ['id','ip','name','status','node_name']}}}

    request = "dapi {}".format(json.dumps(input_json))
    return execute(request)['data']