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

from monasca_log_api.common.repositories.elasticsearch import result_transformer


class TestWithNonNestedFields(unittest.TestCase):

    def setUp(self):
        super(TestWithNonNestedFields, self).setUp()
        self.instance = result_transformer.ResultTransformer(
            timestamp_field=u'@timestamp',
            message_field=u'msg',
            dimensions_field=u'dims'
        )

    def test_should_return_empty_list_when_no_hit(self):
        data = {'hits': {'hits': [] }}

        result = self.instance.transform_list_logs_result(data)
        self.assertEqual([], result)

    def test_should_return_renamed_subset_of_fields_from_source_for_hit(self):
        data = {'hits': {'hits': [
            {'_source': {
                '@timestamp': 'some-time',
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
        
        result = self.instance.transform_list_logs_result(data)
        self.assertEqual(expected, result)

    def test_should_ignore_extraneous_fields_from_outside_source(self):
        data = {'hits': {'hits': [
            {
                '_source': {
                    '@timestamp': 'some-time',
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
        
        result = self.instance.transform_list_logs_result(data)
        self.assertEqual(expected, result)
        
    def test_should_ignore_extraneous_fields_from_inside_source(self):
        data = {'hits': {'hits': [
            {'_source': {
                '@timestamp': 'some-time',
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
        
        result = self.instance.transform_list_logs_result(data)
        self.assertEqual(expected, result)

        
class TestWithNestedFields(unittest.TestCase):

    def setUp(self):
        super(TestWithNestedFields, self).setUp()
        self.instance = result_transformer.ResultTransformer(
            timestamp_field=u'unusually.nested.timestamp',
            message_field=u'log.message',
            dimensions_field=u'log.dimensions'
        )

    def test_should_return_renamed_subset_of_fields_from_source_for_hit(self):
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
        
        result = self.instance.transform_list_logs_result(data)
        self.assertEqual(expected, result)
