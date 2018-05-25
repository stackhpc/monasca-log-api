# Copyright 2016 Hewlett Packard Enterprise Development Company, L.P.
# Copyright 2016-2017 FUJITSU LIMITED
# Copyright 2017-2018 StackHPC Ltd.
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
import json
from monasca_common.rest import utils as rest_utils
from monasca_common.simport import simport
from oslo_log import log
from oslo_utils import encodeutils

from monasca_log_api.app.base import exceptions
from monasca_log_api.app.base import validation
from monasca_log_api.app.controller.api import logs_api
from monasca_log_api.app.controller.v3.aid import bulk_processor
from monasca_log_api.app.controller.v3.aid import helpers
from monasca_log_api.app.controller.v3.schemas import log_query_schema
from monasca_log_api import conf
from monasca_log_api.monitoring import metrics


CONF = conf.CONF
LOG = log.getLogger(__name__)


class Logs(logs_api.LogsApi):

    VERSION = 'v3.0'
    SUPPORTED_CONTENT_TYPES = {'application/json'}

    def __init__(self):
        super(Logs, self).__init__()

        self._region = CONF.service.region
        role_conf = CONF.roles_middleware
        self._delegate_authorized_roles = role_conf.delegate_roles
        self._get_logs_authorized_roles = (role_conf.default_roles +
                                           role_conf.read_only_roles)

        if CONF.monitoring.enable:
            self._processor = bulk_processor.BulkProcessor(
                logs_in_counter=self._logs_in_counter,
                logs_rejected_counter=self._logs_rejected_counter
            )
            self._bulks_rejected_counter = self._statsd.get_counter(
                name=metrics.LOGS_BULKS_REJECTED_METRIC,
                dimensions=self._metrics_dimensions
            )
        else:
            self._processor = bulk_processor.BulkProcessor()

        self._logs_repo = None
        logs_driver = CONF.repositories.logs_driver
        if logs_driver:
            self._logs_repo = simport.load(logs_driver)()

    def on_post(self, req, res):
        if CONF.monitoring.enable:
            with self._logs_processing_time.time(name=None):
                self.process_on_post_request(req, res)
        else:
            self.process_on_post_request(req, res)

    def process_on_post_request(self, req, res):
        try:
            req.validate(self.SUPPORTED_CONTENT_TYPES)

            request_body = helpers.read_json_msg_body(req)

            log_list = self._get_logs(request_body)
            global_dimensions = self._get_global_dimensions(request_body)

        except Exception as ex:
            LOG.error('Entire bulk package has been rejected')
            LOG.exception(ex)
            if CONF.monitoring.enable:
                self._bulks_rejected_counter.increment(value=1)

            raise ex

        if CONF.monitoring.enable:
            self._bulks_rejected_counter.increment(value=0)
            self._logs_size_gauge.send(name=None,
                                       value=int(req.content_length))

        tenant_id = (req.cross_project_id if req.cross_project_id
                     else req.project_id)

        try:
            self._processor.send_message(
                logs=log_list,
                global_dimensions=global_dimensions,
                log_tenant_id=tenant_id
            )
        except Exception as ex:
            res.status = getattr(ex, 'status', falcon.HTTP_500)
            return

        res.status = falcon.HTTP_204

    def on_get(self, req, res):
        if not self._logs_repo:
            LOG.error(
                'Logs repository is not configured. Please configure'
                'a log driver in the Monasca Log API configuration file.')
            res.status = falcon.HTTP_500
            return

        rest_utils.validate_authorization(req, self._get_logs_authorized_roles)

        try:
            raw_query = falcon.uri.parse_query_string(req.query_string)
            query = log_query_schema.request_body_schema(raw_query)
            rest_utils.validate_timestamp_order(query.get('start_time'),
                                                query.get('end_time'))
            # Support cross project queries
            query['tenant_id'] = (
                rest_utils.get_x_tenant_or_tenant_id(
                    req,  self._delegate_authorized_roles))
        except Exception as ex:
            LOG.debug(ex)
            res.status = getattr(
                ex, 'status', falcon.HTTP_UNPROCESSABLE_ENTITY)
            return

        try:
            query['region'] = self._region
            elements = self._logs_repo.list_logs(**query)
            body = json.dumps({'elements': elements}, ensure_ascii=False)
            res.body = encodeutils.to_utf8(body)
        except Exception as ex:
            res.status = getattr(ex, 'status', falcon.HTTP_500)
            return

        res.status = falcon.HTTP_200

    @staticmethod
    def _get_global_dimensions(request_body):
        """Get the top level dimensions in the HTTP request body."""
        global_dims = request_body.get('dimensions', {})
        validation.validate_dimensions(global_dims)
        return global_dims

    @staticmethod
    def _get_logs(request_body):
        """Get the logs in the HTTP request body."""
        if 'logs' not in request_body:
            raise exceptions.HTTPUnprocessableEntity(
                'Unprocessable Entity Logs not found')
        return request_body['logs']
