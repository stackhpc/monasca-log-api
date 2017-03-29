# Copyright 2014 Hewlett-Packard
# Copyright 2015 Cray Inc. All Rights Reserved.
# Copyright 2016 Hewlett Packard Enterprise Development Company LP
# Copyright 2016 FUJITSU LIMITED
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

import datetime
import json

import falcon
from monasca_common.rest import utils as rest_utils
from monasca_common.validation import metrics as metric_validation
from oslo_log import log
from oslo_utils import timeutils

from monasca_log_api.api import exceptions
from monasca_log_api.reference.common import validation

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


def get_x_tenant_or_tenant_id(req, delegate_authorized_roles):
    """Evaluates whether the tenant ID or cross tenant ID should be returned.

    :param req: HTTP request object.
    :param delegate_authorized_roles: List of authorized roles that have
    delegate privileges.
    :returns: Returns the cross tenant or tenant ID.
    """
    if any(x in set(delegate_authorized_roles) for x in req.roles):
        params = falcon.uri.parse_query_string(req.query_string)
        if 'tenant_id' in params:
            tenant_id = params['tenant_id']
            return tenant_id
    return req.project_id


def get_query_param(req, param_name, required=False, default_val=None):
    try:
        params = falcon.uri.parse_query_string(req.query_string)
        if param_name in params:
            if isinstance(params[param_name], list):
                param_val = params[param_name][0].decode('utf8')
            else:
                param_val = params[param_name].decode('utf8')

            return param_val
        else:
            if required:
                raise Exception("Missing " + param_name)
            else:
                return default_val
    except Exception as ex:
        LOG.debug(ex)
        raise exceptions.HTTPUnprocessableEntity(str(ex))


def get_query_dimensions(req, param_key='dimensions'):
    """Gets and parses the query param dimensions.

    :param req: HTTP request object.
    :param dimensions_param: param name for dimensions, default='dimensions'
    :return: Returns the dimensions as a JSON object
    :raises falcon.HTTPBadRequest: If dimensions are malformed.
    """
    try:
        params = falcon.uri.parse_query_string(req.query_string)
        dimensions = {}
        if param_key not in params:
            return dimensions

        dimensions_param = params[param_key]
        if isinstance(dimensions_param, str):
            dimensions_str_array = dimensions_param.split(',')
        elif isinstance(dimensions_param, list):
            dimensions_str_array = []
            for sublist in dimensions_param:
                dimensions_str_array.extend(sublist.split(","))
        else:
            raise Exception("Error parsing dimensions, unknown format")

        for dimension in dimensions_str_array:
            dimension_name_value = dimension.split(':')
            if len(dimension_name_value) == 2:
                dimensions[dimension_name_value[0]] = dimension_name_value[1]
            elif len(dimension_name_value) == 1:
                dimensions[dimension_name_value[0]] = ""
            else:
                raise Exception('Dimensions are malformed')
        return dimensions
    except Exception as ex:
        LOG.debug(ex)
        raise exceptions.HTTPUnprocessableEntity('Unprocessable Entity',
                                                 str(ex))


def validate_query_dimensions(dimensions):
    """Validates the query param dimensions.

    :param dimensions: Query param dimensions.
    :raises falcon.HTTPBadRequest: If dimensions are not valid.
    """
    try:

        result = []
        for key, value in dimensions.items():
            if key.startswith('_'):
                raise Exception("Dimension key {} may not start with '_'"
                                .format(key))
            metric_validation.validate_dimension_key(key)

            values = None

            if value:
                if '|' in value:
                    values = value.split('|')
                    for v in values:
                        metric_validation.validate_dimension_value(key, v)
                else:
                    metric_validation.validate_dimension_value(key, value)
                    values = [value]

            result.append((key, values))

        return result

    except Exception as ex:
        LOG.debug(ex)
        raise exceptions.HTTPUnprocessableEntity(str(ex))


def get_query_starttime_timestamp(req, required=True):
    try:
        params = falcon.uri.parse_query_string(req.query_string)
        if 'start_time' in params:
            return _convert_time_string(params['start_time'])
        else:
            if required:
                raise Exception("Missing start time")
            else:
                return None
    except Exception as ex:
        LOG.debug(ex)
        raise exceptions.HTTPUnprocessableEntity(str(ex))


def get_query_endtime_timestamp(req, required=True):
    try:
        params = falcon.uri.parse_query_string(req.query_string)
        if 'end_time' in params:
            return _convert_time_string(params['end_time'])
        else:
            if required:
                raise Exception("Missing end time")
            else:
                return None
    except Exception as ex:
        LOG.debug(ex)
        raise exceptions.HTTPUnprocessableEntity(str(ex))


def validate_start_end_timestamps(start_timestamp, end_timestamp=None):
    if end_timestamp:
        if not start_timestamp < end_timestamp:
            raise falcon.HTTPBadRequest('Bad request',
                                        'start_time must be before end_time')


def _convert_time_string(date_time_string):
    dt = timeutils.parse_isotime(date_time_string)
    dt = timeutils.normalize_time(dt)
    timestamp = (dt - datetime.datetime(1970, 1, 1)).total_seconds()
    return timestamp


def dumpit_utf8(thingy):
    return json.dumps(thingy, ensure_ascii=False).encode('utf8')


def get_int_query_param(req, param_name, **kwargs):
    val = get_query_param(req, param_name, **kwargs)
    if val is None or isinstance(val, int):
        return val

    try:
        return int(val)
    except Exception:
        raise exceptions.HTTPUnprocessableEntity(
            'Parameter {} value {} must be an integer'.format(param_name, val))
