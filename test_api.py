from collections import namedtuple
import os

import pytest

from helpers import clean_url, clean_email, hash_password
from middlewares import ENVMiddleware


"""
API endpoints test
"""

def test_short_url():
    pass


def test_expand_url():
    pass


def test_go_to_url():
    pass


def test_create_user():
    pass


def test_get_user_urls():
    pass


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

    e = ENVMiddleware()
    e.process_request(req, fake_response)
    assert req.context['host'] == 'http://bit.ly'

    os.environ['HOST'] = 'biggggggggggggghosttttttttttttttt.com'
    e = ENVMiddleware()
    req = fake_request(context={})
    with pytest.raises(Exception):
        e.process_request(req, fake_response)
