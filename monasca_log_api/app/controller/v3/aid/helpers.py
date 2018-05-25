# Copyright 2014 Hewlett-Packard
# Copyright 2015 Cray Inc. All Rights Reserved.
# Copyright 2016 Hewlett Packard Enterprise Development Company LP
# Copyright 2016 FUJITSU LIMITED
# Copyright 2017-2018 StackHPC Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import falcon
from monasca_common.rest import utils as rest_utils
from oslo_log import log

from monasca_log_api.app.base import exceptions
from monasca_log_api.app.base import validation
from monasca_log_api.db.common import model
from monasca_log_api.db.repo import logs_repository

LOG = log.getLogger(__name__)


def read_json_msg_body(req):
    """Read the json_msg from the http request body and return them as JSON.

    :param req: HTTP request object.
    :return: Returns the metrics as a JSON object.
    :raises falcon.HTTPBadRequest:
    """
    try:
        msg = req.stream.read()
        json_msg = rest_utils.from_json(msg)
        return json_msg

    except rest_utils.exceptions.DataConversionException as ex:
        LOG.debug(ex)
        raise falcon.HTTPBadRequest('Bad request',
                                    'Request body is not valid JSON')
    except ValueError as ex:
        LOG.debug(ex)
        raise falcon.HTTPBadRequest('Bad request',
                                    'Request body is not valid JSON')


def get_global_dimensions(request_body):
    """Get the top level dimensions in the HTTP request body."""
    global_dims = request_body.get('dimensions', {})
    validation.validate_dimensions(global_dims)
    return global_dims


def get_logs(request_body):
    """Get the logs in the HTTP request body."""
    if 'logs' not in request_body:
        raise exceptions.HTTPUnprocessableEntity(
            'Unprocessable Entity Logs not found')
    return request_body['logs']


def get_int_query_param(param):
    val = rest_utils.get_query_param(param)
    if val is None or isinstance(val, int):
        return val
    try:
        return int(float(val))
    except Exception:
        raise exceptions.HTTPUnprocessableEntity(
            'Parameter {} value {} must be parsable to an int'.format(param,
                                                                      val))


def get_sort_by(sort_by):
    if not sort_by:
        return
    if not isinstance(sort_by, list):
        sort_by = sort_by.split(',')
    result = []
    for sort_by_field in sort_by:
        parts = sort_by_field.split()
        if len(parts) > 2:
            raise exceptions.HTTPUnprocessableEntity(
                "Invalid sort_by {}".format(sort_by_field))
        if parts[0] not in logs_repository.SORT_BY_FIELDS:
            raise exceptions.HTTPUnprocessableEntity(
                "The sort_by field {} must be one of: [{}]".format(
                    parts[0],
                    ', '.join(logs_repository.SORT_BY_FIELDS)))
        if len(parts) == 1:
            # No sort order specified, use default
            parts.append(logs_repository.DEFAULT_SORT_ORDER)
        allowed_sort_by_orders = logs_repository.SORT_BY_ORDERS.values()
        if len(parts) > 1 and parts[1] not in allowed_sort_by_orders:
            raise exceptions.HTTPUnprocessableEntity(
                "The sort_by value {} must be one of: [{}]".format(
                    parts[1], ', '.join(allowed_sort_by_orders)))
        result.append(model.SortBy(*parts))
    return result
