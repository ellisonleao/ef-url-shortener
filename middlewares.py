import os

from db import DB


class HostEnvMiddleware:
    MAX_HOST_LEN = 15

    def process_request(self, request, response):
        host = os.environ.get('HOST')
        if len(host) == 0 or len(host) > self.MAX_HOST_LEN:
            raise Exception('HOST env var len is greater than '
                            'max size={}'.format(self.MAX_HOST_LEN))

        request.context['host'] = host


class MongoMiddleware:
    def __init__(self, **kwargs):
        mongo_uri = os.environ.get('MONGODB_URI')
        self.db = DB(mongo_uri)
        self.db.create_indexes()

    def process_request(self, request, response):
        request.context['db'] = self.db

    def process_response(self, request, response, resource):
        self.db.close()
        request.context['db'] = None
