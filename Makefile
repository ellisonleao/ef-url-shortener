# defaults
MONGO_URL?=mongodb://localhost:27017/ef_shortener
HOST?=http://ef.me
PORT?=5001

run:
	MONGO_URL=${MONGO_URL} HOST=${HOST} hug -f api.py -p ${PORT}

run-prod:
	MONGO_URL=${MONGO_URL} gunicorn -b 0.0.0.0:${PORT} -w 3 api:__hug_wsgi__

test:
	py.test --cov-report term-missing --cov .
