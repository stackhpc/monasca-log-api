# Copyright 2018 StackHPC Ltd.
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

import monasca_common.rest.utils as utils
from oslo_log import log
import six
import voluptuous

from monasca_log_api.app.controller.v3.aid import helpers
from monasca_log_api.db.common import model

LOG = log.getLogger(__name__)

DEFAULT_LIMIT = '10'
DEFAULT_OFFSET = '0'


def _get_query_dimensions(dimensions):
    if dimensions:
        dimensions = utils.get_query_dimensions(dimensions)
        dimensions = utils.validate_query_dimensions(dimensions)
        return [model.Dimension(k, v) for k, v in dimensions.items()]


def _get_time(time):
    if time:
        return int(utils.get_query_timestamp(time))


_log_query_schema = {
    voluptuous.Optional('tenant_id'): voluptuous.Any(*six.string_types),
    voluptuous.Optional('start_time', default=None): _get_time,
    voluptuous.Optional('end_time', default=None): _get_time,
    voluptuous.Optional('dimensions', default=None): _get_query_dimensions,
    voluptuous.Optional('limit',
                        default=DEFAULT_LIMIT): helpers.get_int_query_param,
    voluptuous.Optional('sort_by', default=None): helpers.get_sort_by,
    voluptuous.Optional('offset',
                        default=DEFAULT_OFFSET): helpers.get_int_query_param,
}


request_body_schema = voluptuous.Schema(_log_query_schema, required=True)
