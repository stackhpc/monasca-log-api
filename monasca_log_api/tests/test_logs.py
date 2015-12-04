# Copyright 2015 kornicameister@gmail.com
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

import falcon
from falcon import testing
import mock

from monasca_log_api.api import exceptions as log_api_exceptions
from monasca_log_api.api import headers
from monasca_log_api.api import logs_api
from monasca_log_api.tests import base
from monasca_log_api.v2.reference import logs


class TestLogs(testing.TestBase):
    def before(self):
        self.conf = base.mock_config(self)
        self.logs_resource = logs.Logs()
        self.api.add_route(
            '/log/single',
            self.logs_resource
        )

    def test_should_fail_not_delegate_ok_cross_tenant_id(self):
        self.simulate_request(
            '/log/single',
            method='POST',
            query_string='tenant_id=1',
            headers={
                'Content-Type': 'application/json'
            }
        )
        self.assertEqual(falcon.HTTP_403, self.srmock.status)

    @mock.patch('monasca_log_api.v2.common.service.LogCreator')
    @mock.patch('monasca_log_api.v2.common.log_publisher.LogPublisher')
    def test_should_pass_empty_cross_tenant_id_wrong_role(self,
                                                          log_creator,
                                                          kafka_publisher):
        self.logs_resource._log_creator = log_creator
        self.logs_resource._kafka_publisher = kafka_publisher

        self.simulate_request(
            '/log/single',
            method='POST',
            headers={
                headers.X_ROLES.name: 'some_role',
                headers.X_DIMENSIONS.name: 'a:1',
                'Content-Type': 'application/json',
                'Content-Length': '0'
            }
        )
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        self.assertEqual(1, kafka_publisher.send_message.call_count)
        self.assertEqual(1, log_creator.new_log.call_count)
        self.assertEqual(1, log_creator.new_log_envelope.call_count)

    @mock.patch('monasca_log_api.v2.common.service.LogCreator')
    @mock.patch('monasca_log_api.v2.common.log_publisher.LogPublisher')
    def test_should_pass_empty_cross_tenant_id_ok_role(self,
                                                       log_creator,
                                                       kafka_publisher):
        self.logs_resource._log_creator = log_creator
        self.logs_resource._kafka_publisher = kafka_publisher

        self.simulate_request(
            '/log/single',
            method='POST',
            headers={
                headers.X_ROLES.name: logs_api.MONITORING_DELEGATE_ROLE,
                headers.X_DIMENSIONS.name: 'a:1',
                'Content-Type': 'application/json',
                'Content-Length': '0'
            }
        )
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        self.assertEqual(1, kafka_publisher.send_message.call_count)
        self.assertEqual(1, log_creator.new_log.call_count)
        self.assertEqual(1, log_creator.new_log_envelope.call_count)

    @mock.patch('monasca_log_api.v2.common.service.LogCreator')
    @mock.patch('monasca_log_api.v2.common.log_publisher.LogPublisher')
    def test_should_pass_delegate_cross_tenant_id_ok_role(self,
                                                          log_creator,
                                                          log_publisher):
        self.logs_resource._log_creator = log_creator
        self.logs_resource._kafka_publisher = log_publisher

        self.simulate_request(
            '/log/single',
            method='POST',
            query_string='tenant_id=1',
            headers={
                headers.X_ROLES.name: logs_api.MONITORING_DELEGATE_ROLE,
                headers.X_DIMENSIONS.name: 'a:1',
                'Content-Type': 'application/json',
                'Content-Length': '0'
            }
        )
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        self.assertEqual(1, log_publisher.send_message.call_count)
        self.assertEqual(1, log_creator.new_log.call_count)
        self.assertEqual(1, log_creator.new_log_envelope.call_count)

    @mock.patch('monasca_log_api.v2.common.service.rest_utils')
    def test_should_fail_empty_dimensions_delegate(self, rest_utils):
        rest_utils.read_body.return_value = True

        self.simulate_request(
            '/log/single',
            method='POST',
            headers={
                headers.X_ROLES.name: logs_api.MONITORING_DELEGATE_ROLE,
                headers.X_DIMENSIONS.name: '',
                'Content-Type': 'application/json',
                'Content-Length': '0'
            }
        )
        self.assertEqual(log_api_exceptions.HTTP_422, self.srmock.status)

    def test_should_fail_for_invalid_content_type(self):
        self.simulate_request(
            '/log/single',
            method='POST',
            headers={
                headers.X_ROLES.name: logs_api.MONITORING_DELEGATE_ROLE,
                headers.X_DIMENSIONS.name: '',
                'Content-Type': 'video/3gpp',
                'Content-Length': '0'
            }
        )
        self.assertEqual(falcon.HTTP_415, self.srmock.status)

    def test_should_pass_payload_size_not_exceeded(self):
        max_log_size = 1000
        content_length = max_log_size - 100
        self.conf.config(max_log_size=max_log_size, group='service')

        self.logs_resource._log_creator = mock.Mock()
        self.logs_resource._kafka_publisher = mock.Mock()

        self.simulate_request(
            '/log/single',
            method='POST',
            headers={
                headers.X_ROLES.name: logs_api.MONITORING_DELEGATE_ROLE,
                headers.X_DIMENSIONS.name: '',
                'Content-Type': 'application/json',
                'Content-Length': str(content_length)
            }
        )
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

    def test_should_fail_payload_size_exceeded(self):
        max_log_size = 1000
        content_length = max_log_size + 100
        self.conf.config(max_log_size=max_log_size, group='service')

        self.logs_resource._log_creator = mock.Mock()
        self.logs_resource._kafka_publisher = mock.Mock()

        self.simulate_request(
            '/log/single',
            method='POST',
            headers={
                headers.X_ROLES.name: logs_api.MONITORING_DELEGATE_ROLE,
                headers.X_DIMENSIONS.name: '',
                'Content-Type': 'application/json',
                'Content-Length': str(content_length)
            }
        )
        self.assertEqual(falcon.HTTP_413, self.srmock.status)

    def test_should_fail_payload_size_equal(self):
        max_log_size = 1000
        content_length = max_log_size
        self.conf.config(max_log_size=max_log_size, group='service')

        self.logs_resource._log_creator = mock.Mock()
        self.logs_resource._kafka_publisher = mock.Mock()

        self.simulate_request(
            '/log/single',
            method='POST',
            headers={
                headers.X_ROLES.name: logs_api.MONITORING_DELEGATE_ROLE,
                headers.X_DIMENSIONS.name: '',
                'Content-Type': 'application/json',
                'Content-Length': str(content_length)
            }
        )
        self.assertEqual(falcon.HTTP_413, self.srmock.status)

    def test_should_fail_content_length(self):
        self.simulate_request(
            '/log/single',
            method='POST',
            headers={
                headers.X_ROLES.name: logs_api.MONITORING_DELEGATE_ROLE,
                headers.X_DIMENSIONS.name: '',
                'Content-Type': 'application/json'
            }
        )
        self.assertEqual(falcon.HTTP_411, self.srmock.status)
