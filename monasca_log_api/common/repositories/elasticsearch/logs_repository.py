# Copyright 2017-2018 StackHPC
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

import elasticsearch
from oslo_config import cfg
from oslo_log import log

from monasca_common.repositories.exceptions import RepositoryException
from monasca_log_api.common.repositories import logs_repository

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class LogsRepository(logs_repository.AbstractLogsRepository):
    def __init__(self):

        try:
            self._es = elasticsearch.Elasticsearch(
                cfg.CONF.elasticsearch.uris
            )
        except Exception as e:
            LOG.exception(e)
            raise RepositoryException(e)

    def list_logs(self, **kwargs):
        search_kwargs = LogsRepository._build_list_logs(**kwargs)
        try:
            result = self._es.search(**search_kwargs)
        except Exception as e:
            LOG.exception(e)
            raise RepositoryException(e)
        return LogsRepository._transform_list_logs_result(result)

    @staticmethod
    def _transform_list_logs_result(result):
        """Tidy up the raw Elasticsearch result of a log listing search."""

        def get(doc, field):
            parts = field.split('.', 1)
            doc = doc[parts[0]]

            # If there are no more dots, then we have traversed the entire
            # path.
            if len(parts) == 1:
                return doc
            return get(doc, parts[1])

        def tidy(doc):
            return {
                u'timestamp': get(doc, cfg.CONF.elasticsearch.timestamp_field),
                u'message': get(doc, cfg.CONF.elasticsearch.message_field),
                u'dimensions': get(doc, cfg.CONF.elasticsearch.dimensions_field)
            }

        return [tidy(hit['_source']) for hit in result['hits']['hits']]

    @staticmethod
    def _build_list_logs(tenant_id, dimensions, start_time, end_time,
                         offset, limit, sort_by):
        """Construct Elasticsearch search arguments.

        Construct arguments which can be directly passed to the search API of
        the Elasticsearch Python module. Currently this only and always returns
        two arguments, index and body. Minimal example usage:

            es = elasticsearch.Elasticsearch()
            sb = SearchBuilder(...)
            kwargs = sb.build_list_logs(tenant_id='xyz', limit=5)
            es.search(**kwargs)

        """
        # TODO: Is this not the project ID most of the time?
        index = LogsRepository._index(tenant_id)
        body = LogsRepository._body(dimensions, start_time, end_time, offset,
                                    limit,
                                    sort_by)

        return {u'index': index, u'body': body}

    @staticmethod
    def _index(tenant_id):
        """Format the index according to the configured pattern."""

        assert (tenant_id is not None)
        assert '{tenant_id}' in cfg.CONF.elasticsearch.index_pattern
        return cfg.CONF.elasticsearch.index_pattern.format(tenant_id=tenant_id)

    @staticmethod
    def _sort(sort_by):
        """Build the sort clauses to apply for the search."""

        return [LogsRepository._sort_clause(s) for s in sort_by]

    @staticmethod
    def _filters(dimensions, start_time, end_time):
        """Build filter clauses based on dimensions and time range."""

        filters = []

        if dimensions:
            filters += [LogsRepository._terms_clause(d) for d in dimensions]

        time_spec = {}
        if start_time:
            time_spec[u'gte'] = start_time
        if end_time:
            time_spec[u'lte'] = end_time

        if time_spec:
            time_spec[u'format'] = 'epoch_second'
            time_filter = {
                u'range': {cfg.CONF.elasticsearch.timestamp_field: time_spec}}

            filters.append(time_filter)

        return filters

    @staticmethod
    def _body(dimensions, start_time, end_time, offset, limit, sort_by):
        """Build the search query body."""

        body = {}

        # Limit must always be specified.
        assert (limit is not None)
        body[u'size'] = limit

        # Apply the offset if supplied.
        if offset:
            body[u'from'] = offset

        # Construct the query clause if we had any filters to apply.
        filters = LogsRepository._filters(dimensions, start_time, end_time)
        if filters:
            body[u'query'] = {u'bool': {u'filter': filters}}

        # Add sort_by field if supplied.
        if sort_by:
            body[u'sort'] = LogsRepository._sort(sort_by)

        return body

    @staticmethod
    def _terms_clause(dimension):
        """Construct a terms clause to apply a dimension filter."""

        field = u'{field}.{name}'.format(
            field=cfg.CONF.elasticsearch.dimensions_field,
            name=dimension.name)

        return {u'terms': {field: dimension.values}}

    @staticmethod
    def _sort_clause(sort):
        """Construct a sort clause to pass in the search body."""

        # Currently only timestamp is a valid field. This may be extened
        # with other fields and dimensions in the future.
        assert (sort.field == u'timestamp')
        field = cfg.CONF.elasticsearch.timestamp_field

        # Derive the correct string used to specify sort direction.
        # Luckily, the API designations are the same as for Elastic.
        assert (sort.direction in [u'asc', u'desc'])

        return {field: {u'order': sort.direction}}
