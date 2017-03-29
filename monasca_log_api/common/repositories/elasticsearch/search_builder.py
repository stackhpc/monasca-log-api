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


class SearchBuilder(object):

    def __init__(self, index_pattern, timestamp_field,
                 message_field, dimensions_field):
        assert '{tenant_id}' in index_pattern

        self._index_pattern = index_pattern
        self._timestamp_field = timestamp_field
        self._message_field = message_field
        self._dimensions_field = dimensions_field

    def build_list_logs(self, tenant_id, dimensions, start_time, end_time,
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

        index = self._index(tenant_id)
        body = self._body(dimensions, start_time, end_time, offset, limit,
                          sort_by)

        return {u'index': index, u'body': body}

    def _index(self, tenant_id):
        """Format the index according to the configured pattern."""

        assert(tenant_id is not None)
        return self._index_pattern.format(tenant_id=tenant_id)

    def _sort(self, sort_by):
        """Build the sort clauses to apply for the search."""

        return [self._sort_clause(s) for s in sort_by]

    def _filters(self, dimensions, start_time, end_time):
        """Build filter clauses based on dimensions and time range."""

        filters = []

        if dimensions:
            filters += [self._terms_clause(d) for d in dimensions]

        time_spec = {}
        if start_time:
            time_spec[u'gte'] = start_time
        if end_time:
            time_spec[u'lte'] = end_time

        if time_spec:
            time_spec[u'format'] = 'epoch_second'
            time_filter = {u'range': {self._timestamp_field: time_spec}}

            filters.append(time_filter)

        return filters

    def _body(self, dimensions, start_time, end_time, offset, limit, sort_by):
        """Build the search query body."""

        body = {}

        # Limit must always be specified.
        assert(limit is not None)
        body[u'size'] = limit

        # Apply the offset if supplied.
        if offset:
            body[u'from'] = offset

        # Construct the query clause if we had any filters to apply.
        filters = self._filters(dimensions, start_time, end_time)
        if filters:
            body[u'query'] = {u'bool': {u'filter': filters}}

        # Add sort_by field if supplied.
        if sort_by:
            body[u'sort'] = self._sort(sort_by)

        return body

    def _terms_clause(self, dimension):
        """Construct a terms clause to apply a dimension filter."""

        field = u'{field}.{name}'.format(field=self._dimensions_field,
                                         name=dimension.name)

        return {u'terms': {field: dimension.values}}

    def _sort_clause(self, sort):
        """Cosntruct a sort clause to pass in the search body."""

        # Currently only timestamp is a valid field. This may be extened
        # with other fields and dimensions in the future.
        assert(sort.field == u'timestamp')
        field = self._timestamp_field

        # Derive the correct string used to specify sort direction.
        # Luckily, the API designations are the same as for Elastic.
        assert(sort.direction in [u'asc', u'desc'])

        return {field: {u'order': sort.direction}}
