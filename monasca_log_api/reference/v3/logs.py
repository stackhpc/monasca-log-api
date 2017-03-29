# Copyright 2016 Hewlett Packard Enterprise Development Company, L.P.
# Copyright 2016-2017 FUJITSU LIMITED
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
from oslo_config import cfg
from oslo_log import log

from monasca_common.simport import simport
from monasca_log_api.api import exceptions
from monasca_log_api.api import logs_api
from monasca_log_api.monitoring import metrics
from monasca_log_api.reference.common import validation
from monasca_log_api.reference.v3.common import bulk_processor
from monasca_log_api.reference.v3.common import helpers
from monasca_log_api.reference.v3.common import query_requests

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class Logs(logs_api.LogsApi):

    VERSION = 'v3.0'
    SUPPORTED_CONTENT_TYPES = {'application/json'}

    def __init__(self):
        super(Logs, self).__init__()

        self._processor = bulk_processor.BulkProcessor(
            logs_in_counter=self._logs_in_counter,
            logs_rejected_counter=self._logs_rejected_counter
        )
        self._bulks_rejected_counter = self._statsd.get_counter(
            name=metrics.LOGS_BULKS_REJECTED_METRIC,
            dimensions=self._metrics_dimensions
        )
        self._logs_repo = None
        logs_driver = CONF.repositories.logs_driver
        if logs_driver:
            print(logs_driver)
            self._logs_repo = simport.load(logs_driver)()

    def on_post(self, req, res):
        with self._logs_processing_time.time(name=None):
            try:
                req.validate(self.SUPPORTED_CONTENT_TYPES)

                request_body = helpers.read_json_msg_body(req)

                log_list = self._get_logs(request_body)
                global_dimensions = self._get_global_dimensions(request_body)

            except Exception as ex:
                LOG.error('Entire bulk package has been rejected')
                LOG.exception(ex)

                self._bulks_rejected_counter.increment(value=1)

                raise ex

            self._bulks_rejected_counter.increment(value=0)
            self._logs_size_gauge.send(name=None,
                                       value=int(req.content_length))

            tenant_id = (req.project_id if req.project_id
                         else req.cross_project_id)

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
            LOG.error('Logs repository is not configured')
            res.status = falcon.HTTP_500
            return

        args = query_requests.get_list_logs_query(req)
        elements = self._logs_repo.list_logs(**args)
        print(elements)

        # Add links
        body = {'elements': elements}

        print(body)

        res.body = helpers.dumpit_utf8(body)
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
