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
from falcon import testing
import mock
import unittest
import fixtures
import oslo_config
import json

from monasca_log_api.api import exceptions as log_api_exceptions
from monasca_log_api.api import headers
from monasca_log_api.reference.v3 import logs
from monasca_log_api.tests import base

from monasca_log_api.common.repositories import logs_repository

REPOSITORY = (
    'monasca_log_api.common.repositories.logs_repository:LogsRepository'
)

class TestLogsQueryBase(testing.TestBase,
                        oslo_config.fixture.Config,
                        fixtures.MockPatch):

    api_class = base.MockedAPI

    def _init_resource(self):
        self.resource = logs.Logs()
        self.api.add_route('/logs', self.resource)

    def setUp(self):
        super(TestLogsQueryBase, self).setUp()
        
        self.useFixture(fixtures.MockPatch(
            'monasca_log_api.'
            'reference.v3.common.bulk_processor.BulkProcessor'))
        self.useFixture(fixtures.MockPatch(
            'monasca_log_api.'
            'common.repositories.logs_repository.LogsRepository'))

        self.conf = self.useFixture(oslo_config.fixture.Config()).conf
        
    def do_get(self, query):
        response = self.simulate_request(
            path='/logs',
            query_string=query,
            method='GET',
            headers={
                headers.X_ROLES.name: 'rolebadger',
                headers.X_TENANT_ID.name: 'tenantbadger',
                'Content-Type': 'application/json'
            },
            decode='utf-8'
        )
        return json.loads(response) if response else None

    @property
    def list_logs_mock(self):
        return self.resource._logs_repo.list_logs


class TestLogsQueryNoRepositoryConfigured(TestLogsQueryBase):

    def setUp(self):
        super(TestLogsQueryNoRepositoryConfigured, self).setUp()
        self._init_resource()
    
    def test_should_fail_when_no_repository_configured(self):
        self.do_get('')
        self.assertEqual(falcon.HTTP_500, self.srmock.status)


class TestLogsQuery(TestLogsQueryBase):

    def setUp(self):
        super(TestLogsQuery, self).setUp()
        self.conf.set_override('logs_driver', REPOSITORY, group='repositories')
        self._init_resource()
        self.list_logs_mock.return_value = {}
        
    def test_should_not_fail_when_repository_configured(self):
        self.do_get('')        
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
       
    def test_should_call_repository_list_logs_once(self):
        self.do_get('')
        
        kwargs = {
            'tenant_id': 'tenantbadger',
            'dimensions': None,
            'start_time': None,
            'end_time': None,
            'offset': None,
            'limit': 10,
            'sort_by': None
        }
        
        self.list_logs_mock.assert_called_once_with(**kwargs)

    # Note we are not exhaustively testing the parsing of all the different
    # request strings here; this is done in test_query_requests.
        
    def test_should_pass_dimensions_to_repository_list_logs(self):
        self.do_get('dimensions=badger:x|y&offset=60')
        
        kwargs = {
            'tenant_id': 'tenantbadger',
            'dimensions': [('badger',['x','y'])],
            'start_time': None,
            'end_time': None,
            'offset': 60,
            'limit': 10,
            'sort_by': None
        }
        
        self.list_logs_mock.assert_called_once_with(**kwargs)

    def test_should_fail_with_unprocessable_entity_for_invalid_query(self):
        self.do_get('start_time=stupid')
        self.assertEqual(falcon.HTTP_422, self.srmock.status)
        
    def test_should_have_elements_field_with_list_logs_result(self):
        self.list_logs_mock.return_value = [{'some': 'data'}]
        response = self.do_get('')
        
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual({'elements': [{'some': 'data'}]}, response)
