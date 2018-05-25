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

import unittest

import mock
from oslo_config import cfg

from monasca_log_api.db.common import model
from monasca_log_api.db.repo.elasticsearch import logs_repository as es_repo


def _query_helper(**kwargs):
    """Test helper to give valid defaults for each argument."""

    defaults = {
        'tenant_id': 'abc123',
        'limit': 10,
        'dimensions': None,
        'start_time': None,
        'end_time': None,
        'offset': None,
        'region': 'RegionOne',
        'sort_by': None
    }
    defaults.update(kwargs)
    return defaults


class TestWithNormalInstance(unittest.TestCase):

    @mock.patch('elasticsearch.Elasticsearch')
    def setUp(self, mock_es_client):
        super(TestWithNormalInstance, self).setUp()
        es_conf = cfg.CONF.elasticsearch
        es_conf.uris = ['http://192.168.1.1:9200', 'http://192.168.1.2:9200']
        es_conf.index_pattern = 'monasca-{tenant_id}-*'
        es_conf.region_field = 'region'
        es_conf.message_field = 'message'
        es_conf.timestamp_field = '@timestamp'
        es_conf.dimensions_field = 'dimensions'
        self.repo = es_repo.LogsRepository()
        self.mock_es_client = mock_es_client


class TestBasicParameters(TestWithNormalInstance):

    def setUp(self):
        super(TestBasicParameters, self).setUp()

    def test_query_size(self):
        args = _query_helper()
        self.repo.list_logs(**args)
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'query': {
                    u'bool': {u'filter': [{u'term': {'region': 'RegionOne'}}]}
                },
                u'size': 10
            }
        }
        self.mock_es_client.return_value.search.assert_called_with(**expected)

    def test_query_offset(self):
        args = _query_helper(offset=66)
        self.repo.list_logs(**args)
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'from': 66,
                u'query': {
                    u'bool': {u'filter': [{u'term': {'region': 'RegionOne'}}]}
                },
                u'size': 10
            }
        }
        self.mock_es_client.return_value.search.assert_called_with(**expected)


class TestLogsRepository(TestWithNormalInstance):

    def setUp(self):
        super(TestLogsRepository, self).setUp()

    def test_instantiate(self):
        self.mock_es_client.assert_called_with(cfg.CONF.elasticsearch.uris)

    @mock.patch('elasticsearch.Elasticsearch')
    def test_fail_to_instantiate(self, mock_es):
        msg = "Invalid URIs"
        mock_es.side_effect = Exception(msg)
        self.assertRaisesRegexp(Exception, msg,
                                es_repo.LogsRepository)

    def test_list_logs(self):
        args = _query_helper()
        self.repo.list_logs(**args)
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'query': {
                    u'bool': {
                        u'filter': [
                            {u'term': {'region': 'RegionOne'}},
                        ]}
                }
            }
        }
        self.mock_es_client.return_value.search.assert_called_with(**expected)

    def test_list_logs_failure(self):
        msg = "Server on fire"
        self.mock_es_client.return_value.search.side_effect = Exception(msg)
        args = _query_helper()
        self.assertRaisesRegexp(Exception, msg, self.repo.list_logs, **args)


class TestSearchBodyFilters(TestWithNormalInstance):
    def setUp(self):
        super(TestSearchBodyFilters, self).setUp()

    def test_filter_by_dimension(self):
        args = _query_helper(dimensions=[model.Dimension(u'foo', [u'bar'])])
        self.repo.list_logs(**args)
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'query': {
                    u'bool': {
                        u'filter': [
                            {u'term': {'region': 'RegionOne'}},
                            {u'terms': {u'dimensions.foo': [u'bar']}}
                        ]}
                }
            }
        }
        self.mock_es_client.return_value.search.assert_called_with(**expected)

    def test_filter_by_multiple_dimensions(self):
        args = _query_helper(dimensions=[model.Dimension(u'd1', [u'v1']),
                                         model.Dimension(u'd2', [u'v2'])])
        self.repo.list_logs(**args)
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'query': {
                    u'bool': {
                        u'filter': [
                            {u'term': {'region': 'RegionOne'}},
                            {u'terms': {u'dimensions.d1': [u'v1']}},
                            {u'terms': {u'dimensions.d2': [u'v2']}}
                        ]}
                }
            }
        }
        self.mock_es_client.return_value.search.assert_called_with(**expected)

    def test_filter_by_start_time(self):
        args = _query_helper(start_time=123)
        self.repo.list_logs(**args)
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'query': {
                    u'bool': {
                        u'filter': [
                            {u'term': {'region': 'RegionOne'}},
                            {
                                u'range': {
                                    u'@timestamp': {
                                        u'format': 'epoch_second',
                                        u'gte': 123
                                    }}}
                        ]}
                }
            }
        }
        self.mock_es_client.return_value.search.assert_called_with(**expected)

    def test_filter_by_end_time(self):
        args = _query_helper(end_time=456)
        self.repo.list_logs(**args)
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'query': {
                    u'bool': {
                        u'filter': [
                            {u'term': {'region': 'RegionOne'}},
                            {
                                u'range': {
                                    u'@timestamp': {
                                        u'format': 'epoch_second',
                                        u'lte': 456
                                    }}}
                        ]}
                }
            }
        }
        self.mock_es_client.return_value.search.assert_called_with(**expected)

    def test_filter_by_start_and_end_time(self):
        args = _query_helper(start_time=123,
                             end_time=456)
        self.repo.list_logs(**args)
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'query': {
                    u'bool': {
                        u'filter': [
                            {u'term': {'region': 'RegionOne'}},
                            {
                                u'range': {
                                    u'@timestamp': {
                                        u'format': 'epoch_second',
                                        u'gte': 123,
                                        u'lte': 456
                                    }}}
                        ]}
                }
            }
        }
        self.mock_es_client.return_value.search.assert_called_with(**expected)

    def test_filter_by_dimensions(self):
        args = _query_helper(start_time=12345,
                             dimensions=[model.Dimension(u'foo', [u'bar'])])
        self.repo.list_logs(**args)
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'query': {
                    u'bool': {
                        u'filter': [
                            {u'term': {'region': 'RegionOne'}},
                            {u'terms': {u'dimensions.foo': [u'bar']}},
                            {
                                u'range': {
                                    u'@timestamp': {
                                        u'format': 'epoch_second',
                                        u'gte': 12345}}
                            }
                        ]}
                }
            }
        }
        self.mock_es_client.return_value.search.assert_called_with(**expected)


class TestSortBy(TestWithNormalInstance):
    def setUp(self):
        super(TestSortBy, self).setUp()

    def test_sort_ascending(self):
        args = _query_helper(sort_by=[model.SortBy('timestamp', 'asc')])
        self.repo.list_logs(**args)
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'query': {
                    u'bool': {u'filter': [{u'term': {'region': 'RegionOne'}}]}
                },
                u'sort': [
                    {u'@timestamp': {u'order': 'asc'}}
                ]
            }
        }
        self.mock_es_client.return_value.search.assert_called_with(**expected)

    def test_sort_descending(self):
        args = _query_helper(sort_by=[model.SortBy('timestamp', 'desc')])
        self.repo.list_logs(**args)
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'query': {
                    u'bool': {u'filter': [{u'term': {'region': 'RegionOne'}}]}
                },
                u'sort': [
                    {u'@timestamp': {u'order': 'desc'}}
                ]
            }
        }
        self.mock_es_client.return_value.search.assert_called_with(**expected)

    def test_multiple_sort_orders(self):
        # This will make more sense when fields other than 'timestamp' are
        # supported.
        args = _query_helper(sort_by=[model.SortBy('timestamp', 'desc'),
                                      model.SortBy('timestamp', 'asc')])
        self.repo.list_logs(**args)
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'query': {
                    u'bool': {u'filter': [{u'term': {'region': 'RegionOne'}}]}
                },
                u'sort': [
                    {u'@timestamp': {u'order': 'desc'}},
                    {u'@timestamp': {u'order': 'asc'}}
                ]
            }
        }
        self.mock_es_client.return_value.search.assert_called_with(**expected)


class TestWithNonNestedFields(unittest.TestCase):

    def setUp(self):
        super(TestWithNonNestedFields, self).setUp()
        es_conf = cfg.CONF.elasticsearch
        es_conf.timestamp_field = 'creation_time'
        es_conf.message_field = 'msg'
        es_conf.dimensions_field = 'dims'

    def test_should_return_empty_list_when_no_hit(self):
        data = {'hits': {'hits': []}}

        result = es_repo.LogsRepository._transform_list_logs_result(data)
        self.assertEqual([], result)

    def test_standardise_field_naming(self):
        data = {'hits': {'hits': [
            {'_source': {
                'creation_time': 'some-time',
                'msg': 'some-message',
                'dims': {'some-dimension': 'some-value'}
            }}
        ]}}
        expected = [
            {
                'timestamp': 'some-time',
                'message': 'some-message',
                'dimensions': {'some-dimension': 'some-value'}
            }
        ]

        result = es_repo.LogsRepository._transform_list_logs_result(data)
        self.assertEqual(expected, result)

    def test_remove_extraneous_fields_from_outside_source(self):
        data = {'hits': {'hits': [
            {
                '_source': {
                    'creation_time': 'some-time',
                    'msg': 'some-message',
                    'dims': {'some-dimension': 'some-value'},
                },
                '_extraneous': '_data'
            }
        ]}}
        expected = [
            {
                'timestamp': 'some-time',
                'message': 'some-message',
                'dimensions': {'some-dimension': 'some-value'}
            }
        ]

        result = es_repo.LogsRepository._transform_list_logs_result(data)
        self.assertEqual(expected, result)

    def test_remove_extraneous_fields_from_inside_source(self):
        data = {'hits': {'hits': [
            {'_source': {
                'creation_time': 'some-time',
                'msg': 'some-message',
                'dims': {'some-dimension': 'some-value'},
                'extraneous': 'data'
            }}
        ]}}
        expected = [
            {
                'timestamp': 'some-time',
                'message': 'some-message',
                'dimensions': {'some-dimension': 'some-value'}
            }
        ]

        result = es_repo.LogsRepository._transform_list_logs_result(data)
        self.assertEqual(expected, result)


class TestWithNestedFields(unittest.TestCase):

    def setUp(self):
        super(TestWithNestedFields, self).setUp()
        es_conf = cfg.CONF.elasticsearch
        es_conf.timestamp_field = 'unusually.nested.timestamp'
        es_conf.message_field = 'log.message'
        es_conf.dimensions_field = 'log.dimensions'

    def test_remove_field_nesting(self):
        data = {'hits': {'hits': [
            {'_source': {
                'unusually': {'nested': {'timestamp': 'some-time'}},
                'log': {
                    'message': 'some-message',
                    'dimensions': {'some-dimension': 'some-value'}
                }
            }}
        ]}}
        expected = [
            {
                'timestamp': 'some-time',
                'message': 'some-message',
                'dimensions': {'some-dimension': 'some-value'}
            }
        ]

        result = es_repo.LogsRepository._transform_list_logs_result(data)
        self.assertEqual(expected, result)
