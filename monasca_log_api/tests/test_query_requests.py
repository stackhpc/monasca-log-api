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

from mock import Mock

import falcon
from monasca_log_api.api import exceptions
from monasca_log_api.reference.v3.common import query_requests
from monasca_log_api.common.repositories import logs_repository

def make_req(q, project_id=None):
    req = Mock()
    req.query_string = q
    req.project_id = project_id
    return req


class TestGetListLogsQuery(unittest.TestCase):

    def test_should_return_default_limit_with_no_params(self):
        req = make_req(q='')
        result = query_requests.get_list_logs_query(req)
        expected = {
            'tenant_id': None,
            'dimensions': None,
            'start_time': None,
            'end_time': None,
            'offset': None,
            'limit': 10,
            'sort_by': None
        }
        self.assertEqual(result, expected)

    def test_should_return_tenant_id_specified_by_project_id_in_request(self):
        req = make_req(q='', project_id='abcdef')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['tenant_id'], 'abcdef')

    def test_should_return_specified_limit_when_explicitly_given(self):
        req = make_req(q='limit=50')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['limit'], 50)

    def test_should_return_limit_as_int(self):
        req = make_req(q='limit=50')
        result = query_requests.get_list_logs_query(req)
        self.assertIsInstance(result['limit'], int)
        
    def test_should_raise_when_limit_is_non_integer(self):
        req = make_req(q='limit=a')
        self.assertRaises(exceptions.HTTPUnprocessableEntity,
                          query_requests.get_list_logs_query,
                          req)

    def test_should_return_specified_offset_when_given(self):
        req = make_req(q='offset=40')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['offset'], 40)

    def test_should_return_offset_as_int(self):
        req = make_req(q='offset=40')
        result = query_requests.get_list_logs_query(req)
        self.assertIsInstance(result['offset'], int)
        
    def test_should_raise_when_offset_is_non_integer(self):
        req = make_req(q='offset=b')
        self.assertRaises(exceptions.HTTPUnprocessableEntity,
                          query_requests.get_list_logs_query,
                          req)

    def test_should_return_dimension_as_logs_repository_dimension_type(self):
        req = make_req(q='dimensions=key')
        result = query_requests.get_list_logs_query(req)
        self.assertIsInstance(result['dimensions'][0],
                              logs_repository.Dimension)
        
    def test_should_return_dimension_with_none_for_no_value(self):
        req = make_req(q='dimensions=key')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['dimensions'], [('key', None)])

    def test_should_raise_when_given_dimension_starting_with_underscore(self):
        req = make_req(q='dimensions=_invalid')
        self.assertRaises(exceptions.HTTPUnprocessableEntity,
                          query_requests.get_list_logs_query,
                          req)

    def test_should_return_no_dimensions_when_all_names_are_empty(self):
        req = make_req(q='dimensions=,')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['dimensions'], None)

    def test_should_return_dimension_with_one_item_list_for_single_value(self):
        req = make_req(q='dimensions=key:value')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['dimensions'], [('key', ['value'])])

    def test_should_return_one_dimension_when_given_after_empty_name(self):
        req = make_req(q='dimensions=,key:value')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['dimensions'], [('key', ['value'])])

    def test_should_return_one_dimension_when_given_before_empty_name(self):
        req = make_req(q='dimensions=key:value,')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['dimensions'], [('key', ['value'])])

    def test_should_return_dimension_with_list_for_each_of_many_values(self):
        req = make_req(q='dimensions=key:v1|v2')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['dimensions'], [('key', ['v1', 'v2'])])

    def test_should_return_each_dimension_when_many_given_without_values(self):
        req = make_req(q='dimensions=key1,key2')
        result = query_requests.get_list_logs_query(req)
        dimensions = sorted(result['dimensions'], key=lambda x: x[0])
        self.assertEqual(dimensions, [('key1', None), ('key2', None)])

    def test_should_return_each_dimension_when_many_given_with_values(self):
        req = make_req(q='dimensions=key1:v1|v2,key2:v3')
        result = query_requests.get_list_logs_query(req)
        dimensions = sorted(result['dimensions'], key=lambda x: x[0])
        self.assertEqual(dimensions, [('key1', ['v1', 'v2']), ('key2', ['v3'])])

    def test_should_return_each_dimension_when_many_given_partial_values(self):
        req = make_req(q='dimensions=key1,key2:v3')
        result = query_requests.get_list_logs_query(req)
        dimensions = sorted(result['dimensions'], key=lambda x: x[0])
        self.assertEqual(dimensions, [('key1', None), ('key2', ['v3'])])
       
    def test_should_return_start_time_as_epoch_seconds_when_given(self):
        req = make_req(q='start_time=2017-01-01T05:00:00Z')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['start_time'], 1483246800)

    def test_should_return_end_time_as_epoch_seconds_when_given(self):
        req = make_req(q='end_time=2017-01-02T13:00:00Z')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['end_time'], 1483362000)

    def test_should_return_start_time_as_int(self):
        req = make_req(q='start_time=2017-01-01T05:00:00Z')
        result = query_requests.get_list_logs_query(req)
        self.assertIsInstance(result['start_time'], int)

    def test_should_return_end_time_as_int(self):
        req = make_req(q='end_time=2017-01-02T13:00:00Z')
        result = query_requests.get_list_logs_query(req)
        self.assertIsInstance(result['end_time'], int)
        
    def test_should_return_both_start_and_end_time_when_start_lt_end(self):
        req = make_req(q='start_time=2017-01-01T05:00:00Z'
                       '&end_time=2017-01-02T13:00:00Z')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['start_time'], 1483246800)
        self.assertEqual(result['end_time'], 1483362000)

    def test_should_raise_when_start_time_after_end_time(self):
        req = make_req(q='start_time=2017-01-02T13:00:00Z'
                       '&end_time=2017-01-01T05:00:00Z')
        self.assertRaises(falcon.HTTPBadRequest,
                          query_requests.get_list_logs_query,
                          req)
        
    def test_should_return_sort_by_none_for_empty_sort_by(self):
        req = make_req(q='sort_by=')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['sort_by'], None)

    def test_should_return_sort_by_none_for_multiple_empty_sort_by(self):
        req = make_req(q='sort_by=,')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['sort_by'], None)

    def test_should_return_sort_by_as_logs_repository_sort_by_type(self):
        req = make_req(q='sort_by=timestamp asc')
        result = query_requests.get_list_logs_query(req)
        self.assertIsInstance(result['sort_by'][0],
                              logs_repository.SortBy)
        
    def test_should_return_sort_by_when_given_timestamp_ascending(self):
        req = make_req(q='sort_by=timestamp asc')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['sort_by'], [ ('timestamp', 'asc') ])

    def test_should_return_sort_by_when_given_timestamp_descending(self):
        req = make_req(q='sort_by=timestamp desc')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['sort_by'], [ ('timestamp', 'desc') ])

    def test_should_return_sort_by_for_each_in_order_when_given_multiple(self):
        req = make_req(q='sort_by=timestamp desc,timestamp asc')
        result = query_requests.get_list_logs_query(req)
        self.assertEqual(result['sort_by'],
                         [ ('timestamp', 'desc'), ('timestamp', 'asc') ])

    def test_should_raise_when_given_sort_by_with_too_many_spaces(self):
        req = make_req(q='sort_by=timestamp desc timestamp')
        self.assertRaises(exceptions.HTTPUnprocessableEntity,
                          query_requests.get_list_logs_query,
                          req)
        
    def test_should_raise_when_given_sort_by_with_invalid_field(self):
        req = make_req(q='sort_by=badger desc')
        self.assertRaises(exceptions.HTTPUnprocessableEntity,
                          query_requests.get_list_logs_query,
                          req)

    def test_should_raise_when_given_sort_by_with_invalid_direction(self):
        req = make_req(q='sort_by=timestamp badger')
        self.assertRaises(exceptions.HTTPUnprocessableEntity,
                          query_requests.get_list_logs_query,
                          req)
