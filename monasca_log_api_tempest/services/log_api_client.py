# Copyright 2015 FUJITSU LIMITED
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

from oslo_serialization import jsonutils as json
from tempest import config
from tempest.common import service_client

CONF = config.CONF


def _uri(url):
    return CONF.monitoring.api_version + url


class LogApiClient(service_client.ServiceClient):
    def get_version(self):
        resp, response_body = self.send_request('GET', '/')
        return resp, response_body

    def send_single_log(self,
                        log,
                        headers=None):
        default_headers = {
            'X-Tenant-Id': 'b4265b0a48ae4fd3bdcee0ad8c2b6012',
            'X-Roles': 'admin',
            'X-Dimensions': 'dev:tempest'
        }
        default_headers.update(headers)

        uri = "/log/single"
        msg = json.dumps(log)

        resp, body = self.post(_uri(uri), msg, default_headers)

        return resp, body
