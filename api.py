import datetime

import hug
from falcon import HTTP_400, HTTP_409, HTTP_201, HTTP_404, HTTP_500

from db import DB
from bson.objectid import ObjectId
from middlewares import HostEnvMiddleware, MongoMiddleware
from helpers import clean_url, clean_email, gen_api_key, serialize_url

"""
EF URL SHORTENER API
~~~~~~~~~~~~~~~~~~~~

Routes
------

    GET  /api/short?long_url=URL
    GET  /api/expand?short_url=URL
    GET  /api/urls/{code}
    GET  /api/urls/
    POST /api/user/
    GET  /s/:code


Schemas
-------
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


@hug.authentication.authenticator
def api_key(request, response, verify_user, **kwargs):
    """API Key Header Authentication
    The verify_user function passed in to ths authenticator shall receive an
    API key as input, and return a user object to store in the request context
    if the request was successful.
    """
    api_key = request.get_header('X-Api-Key')

    if not api_key:
        return None
    return verify_user(request)


def verify(request):
    """
    auth challenge function
    """
    api_key = request.get_header('X-Api-Key')
    db = request.context['db']
    user = db.find_one_user({'api_key': api_key})
    if not user:
        return False
    return user


auth_user = api_key(verify)


"""
Middlewares
"""


api = hug.API(__name__)

# adding host on request.context
api.http.add_middleware(HostEnvMiddleware())

# adding mongodb connection to request.context
api.http.add_middleware(MongoMiddleware())


"""
API endpoints implementations
"""


@hug.get('/api/short', requires=auth_user)
def short_url(request, response):
    """
    Handles url shortening
    """
    db = request.context['db']
    user = request.context['user']
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
        return {'error': 'long_url is not a valid URL'}

    # validate code
    code = request.params.get('code')
    if code and len(code) > DB.MAX_CODE_LEN:
        response.status = HTTP_400
        return {'error': 'Code param must have a max length of 9'}

    # check if url already exists
    if code:
        query = db.find_one_url({'code': code,
                                 'created_by': ObjectId(user['_id'])})
    else:
        query = db.find_one_url({'long_url': long_url,
                                 'created_by': ObjectId(user['_id'])})

    exists = db.find_one_url(query)
    if exists:
        response.status = HTTP_409
        return {'error': 'long_url already exists'}

    # create url
    code = code or db.generate_url_code(host)
    short_url = '{}/{}'.format(host, code)
    url = {
        'short_url': short_url,
        'long_url': long_url,
        'code': code,
        'url_access': [],
        'created_at': datetime.datetime.now(),
        'created_by': ObjectId(user['_id']),
    }

    db.insert_url(url)

    response.status = HTTP_201
    return {'short_url': short_url}


@hug.get('/api/expand', requires=auth_user)
def expand_url(request, response):
    """
    Handle url expanding. Returns limited url info
    """
    db = request.context['db']
    user = request.context['user']

    # validating query params
    if 'short_url' not in request.params:
        response.status = HTTP_400
        return {'error': 'short_url GET param missing'}

    # validate url
    try:
        short_url = clean_url(request.params['short_url'])
    except ValueError:
        response.status = HTTP_400
        return {'error': 'short_url is not a valid URL'}

    # check if url exists
    url = db.find_one_url({'short_url': short_url,
                           'created_by': ObjectId(user['_id'])})
    if not url:
        response.status = HTTP_404
        return {'error': 'short_url does not exist'}

    return {
        'short_url': request.params['short_url'],
        'long_url': url['long_url'],
    }


@hug.get('/api/urls', requires=auth_user)
def get_user_urls(request, response):
    """
    Return user created urls
    """
    db = request.context['db']
    try:
        page = int(request.params.get('page', 1))
    except ValueError:
        response.status = HTTP_400
        return {'error': 'page GET param is not valid'}

    urls = db.find_urls(request.context['user']['_id'], page=page)
    serialized = []
    for url in urls:
        serialized.append(serialize_url(url))

    return serialized


@hug.get('/api/urls/{code}', requires=auth_user)
def get_user_url(request, response, code):
    """
    return user url by code
    """
    db = request.context['db']
    url = db.find_one_url({
        'code': code,
        'created_by': ObjectId(request.context['user']['_id'])
    })
    if not url:
        response.status = HTTP_404
        return {'error': 'URL does not exist'}

    return serialize_url(url)


@hug.post('/api/user')
def create_user(body, request, response):
    """
    Creates a new user
    """
    db = request.context['db']
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

    # check if user exists
    exists = db.find_one_user({'email': email})
    if exists:
        response.status = HTTP_409
        return {'error': 'User already exists'}

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

    return {'api_key': user['api_key']}


"""
short url redirect endpoint
"""


@hug.get('/s/{code}')
def go_to(request, response, code):
    """
    HOST/{code} proxy pass
    """
    db = request.context['db']

    # checking if url exists
    url = db.find_one_url({'code': code})
    if not url:
        response.status = HTTP_404
        return {'error': 'URL not found'}

    # add url access log
    access = {'date': datetime.datetime.now()}
    db.update_url({'_id': url['_id']}, {'$addToSet': {'url_access': access}})

    # redirecting user to url
    return hug.redirect.permanent(url['long_url'])
