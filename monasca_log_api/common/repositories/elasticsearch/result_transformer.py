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


class ResultTransformer(object):

    def __init__(self, timestamp_field, message_field, dimensions_field):

        self._timestamp_field = timestamp_field
        self._message_field = message_field
        self._dimensions_field = dimensions_field

    def transform_list_logs_result(self, result):
        """Tidy up the raw Elasticsearch result of a log listing search."""
        
        def get(doc, field):
            parts = field.split('.', 1)
            doc = doc[parts[0]]
            
            # If there are no more dots, then we have traversed the entire path.
            if len(parts) == 1:
                return doc
            return get(doc, parts[1])

        def tidy(doc):
            return {
                u'timestamp': get(doc, self._timestamp_field),
                u'message': get(doc, self._message_field),
                u'dimensions': get(doc, self._dimensions_field)
            }
        
        return [ tidy(hit['_source']) for hit in result['hits']['hits'] ]
