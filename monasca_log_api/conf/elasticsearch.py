# Copyright 2018 StackHPC Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_config import cfg
from oslo_config import types

elasticsearch_opts = [
    cfg.ListOpt('uris',
                default=['http://localhost:9200'],
                item_type=types.URI(),
                help='''
Comma separated list of URLs to ElasticSearch nodes.
'''),
    cfg.StrOpt('timestamp_field',
               default='@timestamp',
               help='''
Timestamp field name for ElasticSearch log record.
'''),
    cfg.StrOpt('message_field',
               default='message',
               help='''
Log message field name for ElasticSearch log record.
'''),
    cfg.StrOpt('dimensions_field',
               default='dimensions',
               help='''
Dimensions field name for ElasticSearch log record.
''')
]

elasticsearch_group = cfg.OptGroup(name='elasticsearch', title='elasticsearch')


def register_opts(conf):
    conf.register_group(elasticsearch_group)
    conf.register_opts(elasticsearch_opts, elasticsearch_group)


def list_opts():
    return elasticsearch_group, elasticsearch_opts
