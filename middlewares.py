import os


class ENVMiddleware:
    MAX_HOST_LEN = 15

    def process_request(self, request, response):
        host = os.environ.get('HOST')
        if len(host) == 0 or len(host) > self.MAX_HOST_LEN:
            raise Exception('HOST env var len is greater than '
                            'max size={}'.format(self.MAX_HOST_LEN))
        request.context['host'] = host
