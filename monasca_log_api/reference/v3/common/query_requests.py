# Copyright 2017 StackHPC
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import falcon

from monasca_log_api.api import exceptions
from monasca_log_api.reference.v3.common import helpers
from monasca_log_api.common.repositories import logs_repository

def get_list_logs_query(req):
    """Parse and calidate the contents of a logs listing request."""

    # For now, tenant is always the authorized request.
    tenant_id = req.project_id
#    if req.monasca_log_agent:
#        raise falcon.HTTPUnauthorized('Forbidden',
#                                 'Tenant ID is missing a required role to '
#                                      'access this service',
#                                      'Token')
#    tenant_id = (
#        helpers.get_x_tenant_or_tenant_id(req, delegate_authorized_roles))
#    tenant_id = None

    dimensions = _get_dimensions(req)

    start_timestamp = helpers.get_query_starttime_timestamp(req, False)
    end_timestamp = helpers.get_query_endtime_timestamp(req, False)
    helpers.validate_start_end_timestamps(start_timestamp, end_timestamp)

    if start_timestamp is not None:
        start_timestamp = int(start_timestamp)
    if end_timestamp is not None:
        end_timestamp = int(end_timestamp)
        
    offset = helpers.get_int_query_param(req, 'offset')
    limit = helpers.get_int_query_param(req, 'limit', default_val='10')

    sort_by = _get_sort_by(req)

    return {
        'tenant_id': tenant_id,
        'dimensions': dimensions,
        'start_time': start_timestamp,
        'end_time': end_timestamp,
        'offset': offset,
        'limit': limit,
        'sort_by': sort_by
    }


def _get_dimensions(req):

    dimensions = helpers.get_query_dimensions(req)
    if not dimensions:
        return None

    return [ logs_repository.Dimension(*d)
             for d in helpers.validate_query_dimensions(dimensions) ]


def _get_sort_by(req):

    params = falcon.uri.parse_query_string(req.query_string)

    if 'sort_by' not in params:
        return None
    sort_by = params['sort_by']

    if not isinstance(sort_by, list):
        sort_by = sort_by.split(',')

    allowed_sort_by = {'timestamp'}

    if not sort_by:
        return None

    result = []
    
    for sort_by_field in sort_by:
        parts = sort_by_field.split()
        if len(parts) > 2:
            raise exceptions.HTTPUnprocessableEntity(
                "Invalid sort_by {}".format(sort_by_field))

        if parts[0] not in allowed_sort_by:
            raise exceptions.HTTPUnprocessableEntity(
                "sort_by field {} must be one of [{}]".format(
                    parts[0],
                    ','.join(list(allowed_sort_by))))

        if len(parts) > 1 and parts[1] not in ['asc', 'desc']:
            raise exceptions.HTTPUnprocessableEntity(
                "sort_by value {} must be 'asc' or 'desc'".format(
                    parts[1]))

        result.append(logs_repository.SortBy(*parts))

    return result
