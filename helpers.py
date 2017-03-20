from urllib.parse import urlparse
from email.utils import parseaddr
import hashlib
import os

"""
Helper methods
"""


def clean_url(url):
    """
    Validating url input
    """
    if type(url) != str:
        raise ValueError('URL must be a string')

    if not url.startswith(('http://', 'https://')):
        url = 'http://{}'.format(url)

    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError('URL is not valid')

    url = parsed.geturl().replace(' ', '')

    # removing last trailing slash if any
    if url.endswith('/'):
        url = url[:-1]

    return url


def clean_email(email):
    """
    Small helper function to check if email is valid
    """
    if type(email) != str:
        raise ValueError('Email must be a string')

    if '@' not in email:
        raise ValueError('Email is not valid')

    _, email = parseaddr(email)
    if not email:
        raise ValueError('Email is not valid')

    return email


def hash_password(email, salt):
    """
    Securely hash a password using a provided salt
    Hex encoded SHA512 hash of provided password
    """
    password = str(email).encode('utf-8')
    salt = str(salt).encode('utf-8')
    return hashlib.sha512(password + salt).hexdigest()


def gen_api_key(email):  # pragma: no cover
    """
    Create a random API key for a user
    """
    salt = str(os.urandom(64)).encode('utf-8')
    return hash_password(email, salt)
