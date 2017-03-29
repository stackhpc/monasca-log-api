# Copyright 2017 StackHPC
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
from oslo_log import log

from monasca_log_api.common.repositories.elasticsearch import result_transformer
from monasca_log_api.common.repositories.elasticsearch import search_builder
import elasticsearch

LOG = log.getLogger(__name__)
CONF = cfg.CONF

elasticsearch_opts = [
    cfg.ListOpt('uris',
                default=['localhost:9200'],
                help='List of <hostname>:<port> pairs to Elasticsearch nodes'),
    cfg.BoolOpt('use_ssl',
                default=False,
                help='turn on SSL'),
    cfg.BoolOpt('verify_certs',
                default=False,
                help='make sure we verify SSL certificates'),
    cfg.StrOpt('ca_certs',
               default=None,
               help='provide a path to CA certs on disk'),
    cfg.StrOpt('client_cert',
               default=None,
               help='PEM formatted SSL client certificate'),
    cfg.StrOpt('client_key',
               default=None,
               help='PEM formatted SSL client key'),
    cfg.StrOpt('index_pattern',
               default='{tenant_id}-*',
               help=''),
    cfg.StrOpt('timestamp_field',
               default='@timestamp',
               help=''),
    cfg.StrOpt('message_field',
               default='message',
               help=''),
    cfg.StrOpt('dimensions_field',
               default='dimensions',
               help='')
]
elasticsearch_group = cfg.OptGroup(name='elasticsearch',
                                   title='elasticsearch')

cfg.CONF.register_group(elasticsearch_group)
cfg.CONF.register_opts(elasticsearch_opts, elasticsearch_group)


class ESRepository(object):

    def __init__(self):
        # try stuff
        super(ESRepository, self).__init__()

        es_conf = cfg.CONF.elasticsearch

        self._es = elasticsearch.Elasticsearch(
            es_conf.uris,
            use_ssl=es_conf.use_ssl,
            verify_certs=es_conf.verify_certs,
            ca_certs=es_conf.ca_certs,
            client_cert=es_conf.client_cert,
            client_key=es_conf.client_key
        )

        self._builder = search_builder.SearchBuilder(
            index_pattern=es_conf.index_pattern,
            timestamp_field=es_conf.timestamp_field,
            message_field=es_conf.message_field,
            dimensions_field=es_conf.dimensions_field
        )

        self._transformer = result_transformer.ResultTransformer(
            timestamp_field=es_conf.timestamp_field,
            message_field=es_conf.message_field,
            dimensions_field=es_conf.dimensions_field
        )
        
        #        except Exception as ex:
        #            LOG.exception(ex)
        #            raise exceptions.RepositoryException(ex)
