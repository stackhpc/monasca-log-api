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

import unittest

from monasca_log_api.common.repositories import logs_repository
from monasca_log_api.common.repositories.elasticsearch import search_builder


Dimension = logs_repository.Dimension
SortBy = logs_repository.SortBy

def query_args(**kwargs):
    """Test helper to give valid defaults for each argument."""

    defaults = {
        'tenant_id': 'abc123',
        'limit': 10,
        'dimensions': None,
        'start_time': None,
        'end_time': None,
        'offset': None,
        'sort_by': None
    }
    defaults.update(kwargs)
    return defaults


class TestInvalidConfig(object):
    pass


class TestWithNormalInstance(unittest.TestCase):

    def setUp(self):
        super(TestWithNormalInstance, self).setUp()
        self.instance = search_builder.SearchBuilder(
            index_pattern=u'monasca-{tenant_id}-*',
            timestamp_field=u'@timestamp',
            message_field=u'message',
            dimensions_field=u'dimensions'
        )


class TestBasicParameters(TestWithNormalInstance):

    def setUp(self):
        super(TestBasicParameters, self).setUp()

    def test_should_specify_index_and_size_with_minimum_valid_query(self):
        args = query_args()
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10
            }
        }

        self.assertEqual(expected, self.instance.build_list_logs(**args))

    def test_should_specify_from_when_offset_given(self):
        args = query_args(offset=66)
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'from': 66,
                u'size': 10
            }
        }

        self.assertEqual(expected, self.instance.build_list_logs(**args))


class TestSearchBodyFilters(TestWithNormalInstance):

    def setUp(self):
        super(TestSearchBodyFilters, self).setUp()
        
    def test_should_not_have_query_in_body_if_dimensions_list_is_empty(self):
        args = query_args(dimensions=[])
        result = self.instance.build_list_logs(**args)

        self.assertNotIn(u'query', result[u'body'])

    def test_should_contain_body_with_terms_bool_filter_for_dimension(self):
        args = query_args(dimensions=[Dimension(u'foo', [u'bar'])])
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'query': {
                    u'bool': {u'filter': [
                        {u'terms': {u'dimensions.foo': [u'bar']}}
                    ]}
                }
            }
        }

        self.assertEqual(expected, self.instance.build_list_logs(**args))

    def test_should_contain_terms_filter_for_each_dimension(self):
        args = query_args(dimensions=[Dimension(u'd1', [u'v1']),
                                      Dimension(u'd2', [u'v2'])])
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'query': {
                    u'bool': {u'filter': [
                        {u'terms': {u'dimensions.d1': [u'v1']}},
                        {u'terms': {u'dimensions.d2': [u'v2']}}
                    ]}
                }
            }
        }

        self.assertEqual(expected, self.instance.build_list_logs(**args))

    def test_should_contain_range_gte_timestamp_for_start_time(self):
        args = query_args(start_time=123)
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'query': {
                    u'bool': {u'filter': [
                        {u'range': {u'@timestamp': {
                            u'format': 'epoch_second',
                            u'gte': 123
                        }}}
                    ]}
                }
            }
        }

        self.assertEqual(expected, self.instance.build_list_logs(**args))

    def test_should_contain_range_lte_timestamp_for_end_time(self):
        args = query_args(end_time=456)
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'query': {
                    u'bool': {u'filter': [
                        {u'range': {u'@timestamp': {
                            u'format': 'epoch_second',
                            u'lte': 456
                        }}}
                    ]}
                }
            }
        }

        self.assertEqual(expected, self.instance.build_list_logs(**args))

    def test_should_contain_range_gte_lte_timestamp_for_start_end_time(self):
        args = query_args(start_time=123,
                          end_time=456)
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'query': {
                    u'bool': {u'filter': [
                        {u'range': {u'@timestamp': {
                            u'format': 'epoch_second',
                            u'gte': 123,
                            u'lte': 456
                        }}}
                    ]}
                }
            }
        }

        self.assertEqual(expected, self.instance.build_list_logs(**args))

    def test_should_contain_one_filter_list_if_has_dimensions_and_times(self):
        args = query_args(start_time=u'2017-01-01T18:00:00',
                          dimensions=[Dimension(u'foo', [u'bar'])])
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'query': {
                    u'bool': {u'filter': [
                        {u'terms': {u'dimensions.foo': [u'bar']}},
                        {u'range': {u'@timestamp': {
                            u'format': 'epoch_second',
                            u'gte': u'2017-01-01T18:00:00'
                        }}}
                    ]}
                }
            }
        }

        self.assertEqual(expected, self.instance.build_list_logs(**args))


class TestSortBy(TestWithNormalInstance):

    def setUp(self):
        super(TestSortBy, self).setUp()

    def test_should_specify_sort_on_timestamp_when_sort_by_given_as_such(self):
        args = query_args(sort_by=[SortBy('timestamp', 'asc')])
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'sort': [
                    {u'@timestamp': {u'order': 'asc'}}
                ]
            }
        }

        self.assertEqual(expected, self.instance.build_list_logs(**args))

    def test_should_specify_sort_desc_when_sort_by_descending_given(self):
        args = query_args(sort_by=[SortBy('timestamp', 'desc')])
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'sort': [
                    {u'@timestamp': {u'order': 'desc'}}
                ]
            }
        }

        self.assertEqual(expected, self.instance.build_list_logs(**args))

    def test_should_specify_comma_separated_sorts_when_many_sorts_given(self):
        args = query_args(sort_by=[SortBy('timestamp', 'desc'),
                                   SortBy('timestamp', 'asc')])
        expected = {
            u'index': u'monasca-abc123-*',
            u'body': {
                u'size': 10,
                u'sort': [
                    {u'@timestamp': {u'order': 'desc'}},
                    {u'@timestamp': {u'order': 'asc'}}
                ]
            }
        }

        self.assertEqual(expected, self.instance.build_list_logs(**args))
