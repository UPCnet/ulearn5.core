import httpretty
import json
import re


def http_mock_hub_syncacl(acl, uri, status=200):
    httpretty.register_uri(
        httpretty.POST, re.compile('{}/api/domains/\w+/services/syncacl'.format(uri)),
        body=json.dumps(acl),
        status=status,
        content_type='application/json'
    )
