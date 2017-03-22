from collections import namedtuple
import os
# from unittest.mock import patch
import datetime
import random

import pytest
import hug
from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo.uri_parser import parse_uri

from helpers import clean_url, clean_email, hash_password
from db import DB
from middlewares import HostEnvMiddleware, MongoMiddleware

"""
API endpoints test
"""

TEST_MONGO_URL = os.environ.get('MONGODB_URI_TEST')

USERS = (
    {'email': 'testuser1@email.com', 'api_key': 'apikey1'},
    {'email': 'testuser2@email.com', 'api_key': 'apikey2'},
)


def create_fixtures():
    """
    Creating user fixtures for tests
    """
    remove_fixtures()
    with MongoClient(TEST_MONGO_URL) as conn:
        parsed = parse_uri(TEST_MONGO_URL)
        db = conn[parsed['database']]
        # adding user and one url for each user
        for i, user in enumerate(USERS):
            user_id = db.users.insert(user)
            db.urls.insert({
                'code': 'user{}'.format(i),
                'short_url': 'http://ef.me/user{}'.format(i),
                'long_url': 'http://user{}.com'.format(i),
                'url_access': [],
                'created_at': datetime.datetime.now(),
                'created_by': user_id
            })


def remove_fixtures():
    """
    Removing fixtures
    """
    with MongoClient(TEST_MONGO_URL) as conn:
        parsed = parse_uri(TEST_MONGO_URL)
        db = conn[parsed['database']]

        emails = [i['email'] for i in USERS]
        emails.append('testuser3@email.com')
        query = {'email': {'$in': emails}}
        user_ids = [i['_id'] for i in list(db.users.find(query, {'_id': 1}))]
        # removing urls
        db.urls.remove({'created_by': {'$in': user_ids}}, {'multi': True})

        # removing users
        db.users.remove({'_id': {'$in': user_ids}}, {'multi': True})


def setup():
    """
    Creating initial fixtures for tests
    """
    os.environ['MONGODB_URI'] = TEST_MONGO_URL
    os.environ['HOST'] = 'http://ef.me'
    create_fixtures()


def teardown():
    """
    Clear fixtures for tests
    """
    os.environ['MONGODB_URI'] = ''
    os.environ['HOST'] = ''
    remove_fixtures()


def test_short_url():
    """
    test /api/short endpoint
    """
    setup()
    import api
    # bad request without long_url query param
    request_url = '/api/short'
    headers = {'X-Api-Key': 'apikey1'}
    response = hug.test.get(api, request_url, headers=headers)
    assert response.data['error'] == 'long_url GET param missing'

    # bad request without authentication header
    response = hug.test.get(api, request_url)
    assert response.status == '401 Unauthorized'

    # bad request with inexistent authentication header
    headers = {'X-Api-Key': 'not-exists'}
    response = hug.test.get(api, request_url, headers=headers)
    assert response.status == '401 Unauthorized'

    # bad request with invalid url
    headers = {'X-Api-Key': 'apikey1'}
    response = hug.test.get(api, request_url, headers=headers,
                            long_url=(1, 2, 3))
    assert response.data['error'] == 'long_url is not a valid URL'

    # bad request with long code
    headers = {'X-Api-Key': 'apikey1'}
    response = hug.test.get(api, request_url, headers=headers,
                            long_url='www.google.com',
                            code='lllllllllllllllongggggggggg')
    assert response.data['error'] == 'Code param must have a max length of 9'

    #  good request with code generating short_url
    request_url = '/api/short'
    headers = {'X-Api-Key': 'apikey1'}
    response = hug.test.get(api, request_url, headers=headers,
                            long_url='www.google.com', code='abcd')
    assert response.data['short_url'] == 'http://ef.me/abcd'

    # good request for same long url will raise a 409 error
    request_url = '/api/short'
    headers = {'X-Api-Key': 'apikey1'}
    response = hug.test.get(api, request_url, headers=headers,
                            long_url='www.google.com', code='abcd')
    assert response.data['error'] == 'long_url already exists'

    #  good request without generating short_url
    request_url = '/api/short'
    headers = {'X-Api-Key': 'apikey1'}
    response = hug.test.get(api, request_url, headers=headers,
                            long_url='www.google.com/123')
    assert 'short_url' in response.data

    teardown()


def test_expand_url():
    """
    /api/expand endpoint tests
    """
    setup()
    import api

    # bad request with missing short_url
    request_url = '/api/expand'
    headers = {'X-Api-Key': 'apikey1'}
    response = hug.test.get(api, request_url, headers=headers)
    assert response.data['error'] == 'short_url GET param missing'

    # bad request with a not valid url
    request_url = '/api/expand'
    headers = {'X-Api-Key': 'apikey1'}
    response = hug.test.get(api, request_url, headers=headers,
                            short_url=(1, 2, 3))
    assert response.data['error'] == 'short_url is not a valid URL'

    # bad request with a inexistent url
    request_url = '/api/expand'
    headers = {'X-Api-Key': 'apikey1'}
    response = hug.test.get(api, request_url, headers=headers,
                            short_url='http://ef.me/noex')
    assert response.data['error'] == 'short_url does not exist'

    # valid request
    request_url = '/api/expand'
    headers = {'X-Api-Key': 'apikey1'}
    response = hug.test.get(api, request_url, headers=headers,
                            short_url='http://ef.me/user0')
    assert response.data['short_url'] == 'http://ef.me/user0'
    assert response.data['long_url'] == 'http://user0.com'

    teardown()


def test_go_to_url():
    """
    testing /s/:code endpoint
    """
    setup()
    import api

    # test not found
    response = hug.test.get(api, '/s/123')
    assert response.status == '404 Not Found'

    # test 301 response
    response = hug.test.get(api, '/s/user1')
    assert response.status == '301 Moved Permanently'

    teardown()


def test_create_user():
    """
    testing /api/user endpoint
    """
    setup()
    import api

    # bad request with no payload
    response = hug.test.post(api, '/api/user')
    assert response.data['error'] == 'Missing email on body request'

    # bad request with bad email payload
    payload = {'email': (1, 2, 3)}
    response = hug.test.post(api, '/api/user', payload)
    assert response.data['error'] == 'Email not valid'

    # bad request with already added user
    payload = {'email': 'testuser1@email.com'}
    response = hug.test.post(api, '/api/user', payload)
    assert response.data['error'] == 'User already exists'

    # good request with valid payload
    payload = {'email': 'testuser3@email.com'}
    response = hug.test.post(api, '/api/user', payload)
    assert response.status == '200 OK'
    assert 'api_key' in response.data

    teardown()


def test_get_user_urls():
    """
    testing /api/urls endpoint
    """
    setup()
    import api

    # bad request without auth
    response = hug.test.get(api, '/api/urls')
    assert response.status == '401 Unauthorized'

    # get all urls from user1
    headers = {'X-Api-Key': 'apikey1'}
    response = hug.test.get(api, '/api/urls', headers=headers).data

    assert len(response) == 1
    assert response[0]['short_url'] == 'http://ef.me/user0'
    assert response[0]['long_url'] == 'http://user0.com'
    assert response[0]['code'] == 'user0'
    assert response[0]['total_accesses'] == 0

    # add one more access to url on user0 and check the results
    hug.test.get(api, '/s/user0')
    response = hug.test.get(api, '/api/urls', headers=headers).data

    assert len(response) == 1
    assert response[0]['total_accesses'] == 1

    # test pagination
    # adding more urls for user0 and retrieve it
    for i in range(10):
        code = random.randint(4, 99999)
        resp = hug.test.get(api, '/api/short', headers=headers,
                            long_url='http://{}.com'.format(code))
        assert resp.status == '201 Created'

    response = hug.test.get(api, '/api/urls', headers=headers).data
    assert len(response) == 5

    # get page 2
    response = hug.test.get(api, '/api/urls', headers=headers, page=2).data
    assert len(response) == 5

    # get page 3. Should have 1 url only
    response = hug.test.get(api, '/api/urls', headers=headers, page=3).data
    assert len(response) == 1

    teardown()


def test_get_user_url():
    """
    test /api/urls/{code} endpoint
    """
    setup()
    import api

    # bad request without auth
    response = hug.test.get(api, '/api/urls/123')
    assert response.status == '401 Unauthorized'

    # good request with user url
    headers = {'X-Api-Key': 'apikey1'}
    response = hug.test.get(api, '/api/urls/user0', headers=headers)
    assert response.data['short_url'] == 'http://ef.me/user0'
    assert response.data['long_url'] == 'http://user0.com'
    assert response.data['total_accesses'] == 0

    # get url from other user returns 404
    headers = {'X-Api-Key': 'apikey1'}
    response = hug.test.get(api, '/api/urls/user1', headers=headers)
    assert response.data['error'] == 'URL does not exist'

    teardown()


"""
Helpers test
"""


def test_clean_url():
    """
    testing clean_url helper
    """
    bad = 123
    bad2 = ''
    good = 'http://google.com'
    without_scheme = 'google.com'
    with_trailing_slash = 'google.com/'

    with pytest.raises(ValueError):
        clean_url(bad)

    with pytest.raises(ValueError):
        clean_url(bad2)

    assert clean_url(good) == good
    assert clean_url(without_scheme) == good
    assert clean_url(with_trailing_slash) == good


def test_clean_email():
    """
    testing clean_email helper
    """
    bad = '123'
    bad2 = 123
    bad3 = '<<@>>'
    good = 'test@email.com'

    with pytest.raises(ValueError):
        clean_email(bad)

    with pytest.raises(ValueError):
        clean_email(bad2)

    with pytest.raises(ValueError):
        clean_email(bad3)

    assert clean_email(good) == good


def test_hash_password():
    expected = 'd0088c5e26b377da76477cda8d7d2f2e5a3723176eb2a1ddf6c4719d567c3bfe7141f1998a1e3a3cbec86c96740d7d25bc954e2970d4974b66193a9ea210a8af'

    assert hash_password('test@email.com', 'salt123') == expected


"""
Middleware test
"""


def test_env_middleware():
    os.environ['HOST'] = 'http://bit.ly'

    fake_request = namedtuple('Request', 'context')
    fake_response = {}
    req = fake_request(context={})

    e = HostEnvMiddleware()
    e.process_request(req, fake_response)
    assert req.context['host'] == 'http://bit.ly'

    os.environ['HOST'] = 'biggggggggggggghosttttttttttttttt.com'
    e = HostEnvMiddleware()
    req = fake_request(context={})
    with pytest.raises(Exception):
        e.process_request(req, fake_response)

    os.environ['HOST'] = ''


def test_mongo_middleware():
    os.environ['MONGODB_URI'] = TEST_MONGO_URL
    parsed = parse_uri(TEST_MONGO_URL)

    fake_request = namedtuple('Request', 'context')
    fake_response = {}
    req = fake_request(context={})

    m = MongoMiddleware()
    m.process_request(req, fake_response)
    assert isinstance(req.context['db'], DB)
    assert req.context['db'].database == parsed['database']

    m.process_response(req, {}, {})
    assert req.context['db'] is None

    os.environ['MONGODB_URI'] = ''


"""
DB test
"""


def test_sanitize_query():
    bad = ''
    good = {}
    good2 = {'_id': '58d0211ea1711d51401aee4c'}
    assert DB.sanitize_query(bad) is False
    assert DB.sanitize_query(good) == {}
    assert DB.sanitize_query(good2) == {'_id': ObjectId('58d0211ea1711d51401aee4c')}
