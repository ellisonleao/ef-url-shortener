# defaults
MONGODB_URI?=mongodb://localhost:27017/ef_shortener
MONGODB_URI_TEST?=mongodb://localhost:27017/ef_test
HOST?=http://ef.me
PORT?=5001

run:
	MONGODB_URI=${MONGODB_URI} HOST=${HOST} hug -f api.py -p ${PORT}

run-prod:
	MONGODB_URI=${MONGODB_URI} HOST=${HOST} gunicorn -b 0.0.0.0:${PORT} -w 3 --worker-class="egg:meinheld#gunicorn_worker" api:__hug_wsgi__

test:
	MONGODB_URI_TEST=${MONGODB_URI_TEST} pytest --cov-report term-missing --cov .
