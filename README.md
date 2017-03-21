EF URL Shortener
================

A URL Shortening microservice API

## Prerequisites:

- MongoDB
- Python 3

Installing:


- With pip

```
pip install git+git://github.com/ellisonleao/ef-url-shortener.git
```

- Cloning

A [virtualenv](https://pypi.python.org/pypi/virtualenv) is recommended

```bash
git clone github.com/ellisonleao/ef-url-shortener
cd ef-url-shortener
pip install -r requirements.txt
```

## Running:

Some env vars are required for the service:

- **`HOST`** - Shortening URL Host
- **`MONGO_URL`** - MongoDB url

There is also a optional:

- **`PORT`** - Run the service on http port


To run the project, execute the following:

```bash
export HOST="http://somehost"
export MONGO_URL="mongodb://mongourl"

make run
```

you can also use just

```
make run
```

which will default the `HOST` to `http://ef.me` and `MONGO_URL` to `mongodb://localhost:27017/ef_shortener` and

## Endpoints:

- All API requests must pass a `X-Api-Key` header with the generated api key for the user.
- All API requests must use `application/json` as payload content-type on post requests

### POST /api/user

**Add user**

Parameters:

- `email` : A valid email address

Example request:

```bash
curl -XPOST http://host/api/user -d '{"email": "a valid email"} -H 'Content-Type: application/json'
```

Example response:

```
HTTP/1.0 200 OK
Date: GMT Date
Server: Some web server
content-length: 143
content-type: application/json

{
    "api_key": "4cc5963bf4682d1cd6d855f3cd45cb765d2f743f883f459cc6c7ee421d9ee927e89a5357bd04586483ea00094c8b6656bbbfaca3c8b7513d6507a85f16ebcdcd"
}
```

### GET /api/short

**Short url**

This endpoint creates a short url, given a long one

Parameters:

- `long_url` - Valid URL

Example request:

```bash
curl http://host/api/short?long_url=http://google.com
```

Example response

```
HTTP/1.0 201 Created
Date: GMT Date
Server: Some web server
content-length: 39
content-type: application/json

{
    "short_url": "http://host/XYZCxoXeS"
}
```

Other responses:

- `409` - Already added long_url
- `400` - Bad request
- `401` - Unauthorized request


### GET /api/expand

**Expand url**

This endpoint returns information about the original url and the short url.

Parameters:

- `short_url` - Valid URL

Example request:

```bash
curl http://host/api/expand?short_url=http://host/code
```

Example response

```
HTTP/1.0 200 OK
Date: GMT Date
Server: Some web server
content-length: 75
content-type: application/json

{
    "long_url": "http://somelongurl.com",
    "short_url": "http://host/code"
}
```

Other responses:

- `404` - Short url not found
- `400` - Bad request
- `401` - Unauthorized request

### GET /api/urls

**User urls**

This endpoint returns a list of urls for a determinated user.


Parameters:

- `page` - Get specific page

Example request:

```bash
curl http://host/api/user
```

Example response

```
HTTP/1.0 200 OK
Date: GMT Datetime
Server: Some web server
content-length: 591
content-type: application/json

[
    {
        "long_url": "http://www.google.com/123",
        "short_url": "http://host/somecode",
        "total_accesses": 6,
        "url_access": [
            {
                "date": "2017-03-20T17:06:41.876000"
            },
            {
                "date": "2017-03-20T17:06:43.402000"
            },
            {
                "date": "2017-03-20T17:06:44.232000"
            },
            {
                "date": "2017-03-20T17:15:29.990000"
            },
            {
                "date": "2017-03-20T17:15:30.911000"
            },
            {
                "date": "2017-03-20T17:15:31.747000"
            }
        ]
    },
    {
        "long_url": "http://www.g1.com.br",
        "short_url": "http://host/code",
        "total_accesses": 0,
        "url_access": []
    }
]
```

Other responses:

- `401` - Unauthorized request


## Improvements Roadmap

Several things could be added as improvements:

- **Pagination** - List of urls can have pagination for better response time and scalability.
- **OAuth2 for authentication** - using a client secret with a client id the user could generate a token for requests. That token should be invalidated at some point. Some social auth could be added too
- **Caching** - Adding a caching layer on top of the api will improve the response time. Varnish cache could be an option.
- **Use Nginx** - Nginx could be used for web server, load balancer and reverse proxy to configure the short url host.
