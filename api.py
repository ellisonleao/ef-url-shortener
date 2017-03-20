import datetime

import hug
from falcon import HTTP_400, HTTP_409, HTTP_201, HTTP_404, HTTP_500

from db import DB
from middlewares import ENVMiddleware
from helpers import clean_url, clean_email, gen_api_key

"""
EF URL SHORTENER API
~~~~~~~~~~~~~~~~~~~~

routes:
    GET /api/short
        - params: long_url=x - requires api_token
    GET /api/expand?short_url=x - requires api_token
    GET /api/info?short_url=x- requires api_token
    GET /api/urls/- requires api_token
    POST /api/user/ - create user
    GET /s/:code - redirect to long_url

schemas:
    - url
    {
        'user_id': 'some_user_id',
        'short_url': 'some_url',
        'long_url': 'long_url_version',
        'code': 'short_url code',
        'created_at': 'timestamp',
        'created_by': 'user_id',
        'url_access': [
            {'date': 'timestamp'},
            ...
        ]
    }

    - user
    {
        'email': 'some@email.com',
        'api_key': 'api_key'
    }

"""

"""
Auth layer
"""


def authenticate_api_key(key):
    db = DB()
    user = db.find_one_user({'api_key': key})
    if not user:
        return False
    return user


api_key_auth = hug.authentication.api_key(authenticate_api_key)


"""
API endpoints implementations
"""

api = hug.API(__name__)

# adding environment middleware
api.http.add_middleware(ENVMiddleware())


@hug.get('/api/short', example='?long_url=http://www.google.com',
         requires=api_key_auth)
def short_url(request, response):
    """
    Handles url shortening
    """
    db = DB()
    host = request.context['host']

    # check long_url param
    if 'long_url' not in request.params:
        response.status = HTTP_400
        return {'error': 'long_url GET param missing'}

    long_url = request.params['long_url']

    # validate url
    try:
        long_url = clean_url(long_url)
    except ValueError:
        response.status = HTTP_400
        return {'error': 'long_url URL is not valid'}

    # check if url already exists
    exists = db.find_one_url({'long_url': long_url})
    if exists:
        response.status = HTTP_409
        return {'error': 'long_url already exists'}

    # create url
    code = db.generate_url_code(host)
    short_url = '{}/{}'.format(host, code)
    url = {
        'short_url': short_url,
        'long_url': long_url,
        'code': code,
        'url_access': [],
        'created_at': datetime.datetime.now(),
        'created_by': request.context['user']['_id'],
    }

    db.insert_url(url)

    response.status = HTTP_201
    db.close()
    return {'short_url': short_url}


@hug.get('/api/expand', example='?short_url=http://host/s/code',
         requires=api_key_auth)
def expand_url(request, response):
    """
    Handle url expanding. Returns limited url info
    """
    db = DB()

    # validating query params
    if 'short_url' not in request.params:
        response.status = HTTP_400
        return {'error': 'short_url GET param missing'}

    # check if url exists
    url = db.find_one_url({'short_url': request.params['short_url']})
    if not url:
        response.status = HTTP_404
        return {'error': 'long_url does not exist'}

    db.close()
    return {
        'short_url': request.params['short_url'],
        'long_url': url['long_url'],
    }


@hug.get('/api/urls', requires=api_key_auth)
def get_user_urls(request, response):
    """
    Return user created urls
    """
    db = DB()
    urls = db.find_urls(request.context['user']['_id'])
    serialized = []
    for url in urls:
        serialized.append({
            'long_url': url['long_url'],
            'short_url': url['short_url'],
            'url_access': url['url_access'],
            'total_accesses': len(url['url_access']),
        })

    return serialized


@hug.post('/api/user')
def user(body, request, response):
    """
    Creates a new user
    """
    db = DB()
    # validate body
    if not body or 'email' not in body:
        response.status = HTTP_400
        return {'error': 'Missing email on body request'}

    # validate email
    try:
        email = clean_email(body['email'])
    except ValueError:
        response.status = HTTP_400
        return {'error': 'Email not valid'}

    user = {
        'email': email,
        'api_key': gen_api_key(email),
        'created_at': datetime.datetime.now()
    }

    # creating user
    result = db.insert_user(user)
    if not result.inserted_id:
        response.status = HTTP_500
        return {'error': 'Error on creating user. Internal Error'}

    db.close()
    return {'api_key': user['api_key']}


"""
short url redirect endpoint
"""


@hug.get('/s/{code}')
def go_to(request, response, code):
    """
    HOST/{code} proxy pass
    """
    db = DB()

    # checking if url exists
    url = db.find_one_url({'code': code})
    if not url:
        response.status = HTTP_404
        return {'error': 'URL not found'}

    # add url access log
    access = {'date': datetime.datetime.now()}
    db.update_url({'_id': url['_id']}, {'$addToSet': {'url_access': access}})

    db.close()
    # redirecting user to url
    return hug.redirect.permanent(url['long_url'])
