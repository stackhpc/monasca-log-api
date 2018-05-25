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

import json

import falcon
import fixtures
import oslo_config
import six

from monasca_log_api.app.controller.api import headers
from monasca_log_api.app.controller.v3 import logs
from monasca_log_api.app.controller.v3.schemas import log_query_schema
from monasca_log_api.db.common import model
from monasca_log_api.tests import base

REPOSITORY = (
    'monasca_log_api.db.repo.logs_repository:'
    'AbstractLogsRepository'
)


class TestLogsQueryBase(falcon.testing.TestBase,
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
            'app.controller.v3.aid.bulk_processor.BulkProcessor'))
        self.useFixture(fixtures.MockPatch(
            'monasca_log_api.'
            'db.repo.logs_repository.AbstractLogsRepository'))

        self.conf = self.useFixture(oslo_config.fixture.Config()).conf

    def do_get(self, query, role='agent'):
        response = self.simulate_request(
            path='/logs',
            query_string=query,
            method='GET',
            headers={
                headers.X_ROLES.name: role,
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
        self.conf.set_override(
            'default_roles', 'agent', group='roles_middleware')
        self.conf.set_override(
            'delegate_roles', 'agent', group='roles_middleware')
        self._init_resource()
        self.list_logs_mock.return_value = {}

    def _test_validation_helper(self, **kwargs):
        expected_kwargs = {
            'tenant_id': 'tenantbadger',
            'dimensions': None,
            'start_time': None,
            'end_time': None,
            'offset': int(log_query_schema.DEFAULT_OFFSET),
            'limit': int(log_query_schema.DEFAULT_LIMIT),
            'region': None,
            'sort_by': None
        }
        expected_kwargs.update(kwargs)
        self.list_logs_mock.assert_called_once()
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Compare the arguments one by one
        actual_kwargs = self.list_logs_mock.call_args[1]
        for key, value in expected_kwargs.items():
            expected_value = actual_kwargs[key]
            try:
                iter(value)
            except TypeError:
                # Not iterable
                self.assertEqual(value, expected_value)
            else:
                # Iterable - we don't care about the ordering
                six.assertCountEqual(self, value, expected_value)

    def test_validation_default_params(self):
        self.do_get('')
        self._test_validation_helper()

    def test_validation_unknown_field(self):
        self.do_get('discombobulate=no')
        # Don't accept anything not in the schema
        self.assertEqual(falcon.HTTP_UNPROCESSABLE_ENTITY, self.srmock.status)

    def test_should_have_elements_field_with_list_logs_result(self):
        self.list_logs_mock.return_value = [{'some': 'data'}]
        response = self.do_get('')

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual({'elements': [{'some': 'data'}]}, response)

    def test_cross_tenant_query(self):
        # Peek at bigbadger's logs. It's ok because our role is in the delegate
        # roles list.
        self.do_get('tenant_id=bigbadger')
        self._test_validation_helper(tenant_id='bigbadger')

    def test_cross_tenant_query_prohibited(self):
        # Our role isn't in the delegate roles list, so we're not allowed
        # to look at logs from other projects.
        self.do_get('tenant_id=bigbadger', role='bodger')
        self.assertEqual(falcon.HTTP_UNAUTHORIZED, self.srmock.status)

    def test_validation_limit_param_float_string(self):
        self.do_get('limit=123.456')
        self._test_validation_helper(limit=123)

    def test_validation_limit_param_invalid(self):
        self.do_get('limit=invalid')
        self.assertEqual(falcon.HTTP_UNPROCESSABLE_ENTITY, self.srmock.status)

    def test_validation_offset_param(self):
        self.do_get('offset=123')
        self._test_validation_helper(offset=123)

    def test_validation_offset_param_float_string(self):
        self.do_get('offset=123.456')
        self._test_validation_helper(offset=123)

    def test_validation_offset_param_invalid(self):
        self.do_get('offset=invalid')
        self.assertEqual(falcon.HTTP_UNPROCESSABLE_ENTITY, self.srmock.status)

    def test_validation_start_time_as_epoch_seconds(self):
        self.do_get('start_time=2017-01-01T05:00:00Z')
        self._test_validation_helper(start_time=1483246800)

    def test_validation_bad_start_time(self):
        self.do_get('start_time=invalid')
        self.assertEqual(falcon.HTTP_UNPROCESSABLE_ENTITY, self.srmock.status)

    def test_validation_end_time_as_epoch_seconds(self):
        self.do_get('end_time=2017-01-02T13:00:00Z')
        self._test_validation_helper(end_time=1483362000)

    def test_validation_bad_end_time(self):
        self.do_get('end_time=invalid')
        self.assertEqual(falcon.HTTP_UNPROCESSABLE_ENTITY, self.srmock.status)

    def test_validation_start_and_end_time_ordered(self):
        self.do_get('start_time=2017-01-01T05:00:00Z'
                    '&end_time=2017-01-02T13:00:00Z')
        self._test_validation_helper(start_time=1483246800,
                                     end_time=1483362000)

    def test_validation_start_and_end_time_invalid_order(self):
        self.do_get('start_time=2017-01-02T13:00:00Z'
                    '&end_time=2017-01-01T05:00:00Z')
        self.assertEqual(falcon.HTTP_UNPROCESSABLE_ENTITY, self.srmock.status)

    def test_validation_dimension(self):
        self.do_get('dimensions=dimension')
        self._test_validation_helper(dimensions=[model.Dimension(
            name='dimension', values=None)])

    def test_validation_invalid_dimension_underscore(self):
        self.do_get('dimensions=_dimension')
        self.assertEqual(falcon.HTTP_UNPROCESSABLE_ENTITY, self.srmock.status)

    def test_validation_dimension_name_empty(self):
        self.do_get('dimensions=,')
        self._test_validation_helper(dimensions=None)

    def test_validation_dimension_with_value(self):
        self.do_get('dimensions=source:stdout')
        self._test_validation_helper(dimensions=[model.Dimension(
            name='source', values=['stdout'])])

    def test_validation_dimension_name_empty_proceeding(self):
        self.do_get('dimensions=source:stdout,')
        self._test_validation_helper(dimensions=[model.Dimension(
            name='source', values=['stdout'])])

    def test_validation_dimension_name_empty_preceding(self):
        self.do_get('dimensions=,source:stdout')
        self._test_validation_helper(dimensions=[model.Dimension(
            name='source', values=['stdout'])])

    def test_validation_dimension_with_multi_value(self):
        self.do_get('dimensions=source:stdout|file|syslog')
        self._test_validation_helper(dimensions=[model.Dimension(
            name='source', values=['stdout', 'file', 'syslog'])])

    def test_validation_dimension_multiple_with_values(self):
        self.do_get('dimensions=source:stdout|file|syslog,level:error|warn')
        self._test_validation_helper(dimensions=[
            model.Dimension(
                name='source', values=['stdout', 'file', 'syslog']),
            model.Dimension(
                name='level', values=['error', 'warn'])
        ])

    def test_validation_dimension_multiple_without_values(self):
        self.do_get('dimensions=source,level')
        self._test_validation_helper(dimensions=[
            model.Dimension(
                name='source', values=None),
            model.Dimension(
                name='level', values=None)
        ])

    def test_validation_dimension_multiple_with_some_values(self):
        self.do_get('dimensions=source,level:error')
        self._test_validation_helper(dimensions=[
            model.Dimension(
                name='source', values=None),
            model.Dimension(
                name='level', values=['error'])
        ])

    def test_validation_sort_by_empty(self):
        self.do_get('sort_by=')
        self._test_validation_helper()

    def test_validation_sort_by_multiple_empty(self):
        self.do_get('sort_by=,')
        self._test_validation_helper()

    def test_validation_sort_by_timestamp_no_direction(self):
        self.do_get('sort_by=timestamp')
        self._test_validation_helper(sort_by=[
            model.SortBy(
                field='timestamp',
                direction='desc'
            )
        ])

    def test_validation_sort_by_timestamp_ascending(self):
        self.do_get('sort_by=timestamp asc')
        self._test_validation_helper(sort_by=[
            model.SortBy(
                field='timestamp',
                direction='asc'
            )
        ])

    def test_validation_sort_by_timestamp_descending(self):
        self.do_get('sort_by=timestamp desc')
        self._test_validation_helper(sort_by=[
            model.SortBy(
                field='timestamp',
                direction='desc'
            )
        ])

    def test_validation_sort_by_timestamp_multiple(self):
        self.do_get('sort_by=timestamp desc, timestamp asc')
        self._test_validation_helper(sort_by=[
            model.SortBy(
                field='timestamp',
                direction='desc'
            ),
            model.SortBy(
                field='timestamp',
                direction='asc'
            )
        ])

    def test_validation_sort_by_invalid_field(self):
        self.do_get('sort_by=size asc')
        self.assertEqual(falcon.HTTP_UNPROCESSABLE_ENTITY, self.srmock.status)

    def test_validation_sort_by_invalid_direction(self):
        self.do_get('sort_by=timestamp sideways')
        self.assertEqual(falcon.HTTP_UNPROCESSABLE_ENTITY, self.srmock.status)

    def test_validation_sort_by_bad_list(self):
        self.do_get('sort_by=timestamp desc timestamp')
        self.assertEqual(falcon.HTTP_UNPROCESSABLE_ENTITY, self.srmock.status)

    def test_validation_all_args(self):
        self.do_get(
            'tenant_id=bigbadger&'
            'start_time=2018-05-21T10:36:38.103Z&'
            'end_time=2018-05-21T10:51:38.103Z&'
            'dimensions=source:stdout&'
            'limit=100'
            '&sort_by=timestamp%20desc'
            '&offset=123')

        self._test_validation_helper(
            tenant_id='bigbadger',
            start_time=1526898998,
            end_time=1526899898,
            dimensions=[
                model.Dimension(name='source', values=['stdout'])],
            limit=100,
            sort_by=[
                model.SortBy(field='timestamp', direction='desc')],
            offset=123)

    def test_list_logs_throws_exception(self):
        self.list_logs_mock.side_effect = falcon.HTTPServiceUnavailable()
        self.do_get('')
        self.assertEqual(falcon.HTTP_503, self.srmock.status)
