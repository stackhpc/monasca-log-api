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
List of Elasticsearch URIs.
'''),
    cfg.StrOpt('index_pattern',
               default='monasca-{tenant_id}-*',
               help='''
A template describing the Elasticseach index pattern. The template should
support specifying the OpenStack project id. This is used as the basis
for tenant isolation.
'''),
    cfg.StrOpt('region_field',
               default='meta.region',
               help='''
Region field name for Elasticsearch log record.
'''),
    cfg.StrOpt('timestamp_field',
               default='@timestamp',
               help='''
Timestamp field name for Elasticsearch log record.
'''),
    cfg.StrOpt('message_field',
               default='log.message',
               help='''
Log message field name for Elasticsearch log record.
'''),
    cfg.StrOpt('dimensions_field',
               default='log.dimensions',
               help='''
Dimensions field name for Elasticsearch log record.
''')
]

elasticsearch_group = cfg.OptGroup(name='elasticsearch', title='elasticsearch')


def register_opts(conf):
    conf.register_group(elasticsearch_group)
    conf.register_opts(elasticsearch_opts, elasticsearch_group)


def list_opts():
    return elasticsearch_group, elasticsearch_opts
