# defaults
MONGODB_URI?=mongodb://localhost:27017/ef_shortener
HOST?=http://ef.me
PORT?=5001

run:
	MONGODB_URI=${MONGODB_URI} HOST=${HOST} hug -f api.py -p ${PORT}

run-prod:
	MONGODB_URI=${MONGODB_URI} HOST=${HOST} gunicorn -b 0.0.0.0:${PORT} -w 3 api:__hug_wsgi__

test:
	py.test --cov-report term-missing --cov .
