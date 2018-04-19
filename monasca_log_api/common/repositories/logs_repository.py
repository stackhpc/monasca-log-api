# Copyright 2017 StackHPC Ltd.
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

import abc
import collections
import six

Dimension = collections.namedtuple('Dimension', 'name values')
SortBy = collections.namedtuple('SortBy', 'field direction')


@six.add_metaclass(abc.ABCMeta)
class AbstractLogsRepository(object):

    @abc.abstractmethod
    def list_logs(self, tenant_id, dimensions, start_time, end_time, offset,
                  limit, sort_by):
        """Obtain log listing based on simple criteria of dimension values.

        Performs queries on the underlying log storage against a time range and
        set of dimension values. Additionally, it is possible to optionally
        sort results by timestamp.

        :param tenant_id:
            Tenant/project id for which to obtain logs (required).
        :param dimensions:
            List of Dimension tuples containing pairs of dimension names and
            optional lists of dimension values. These will be used to filter
            the logs returned. When multiple values are given, the dimension
            must match any of the given values. If None is given, logs with any
            value for the dimension will be returned.
        :param start_time:
            Starting time in UNIX time (seconds, inclusive).
        :param end_time:
            Ending time in UNIX time (seconds, inclusive).
        :param offset:
            Number of matching results to skip past.
        :param limit:
            Number of matching results to return.
        :param sort_by:
            List of SortBy tuples specifying fields to sort by and the
            direction to sort the result set by. e.g. ('timestamp','asc'). The
            direction is specified by either the string 'asc' for ascending
            direction, or 'desc' for descending.

        :type tenant_id: str
        :type dimensions: None or list[Dimension[str, list[str] or None]]
        :type start_time: None or int
        :type end_time: None or int
        :type offset: None or int
        :type limit: None or int
        :type sort_by: None or list[SortBy[str, str]]

        :return:
            Log messages matching the given criteria. The dict representing
            each message entry will contain attributes extracted from the
            underlying structure; 'message', 'timestamp' and 'dimensions'.

        :rtype: list[dict]
        """
        pass
