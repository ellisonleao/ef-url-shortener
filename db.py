import random
import string

from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from pymongo.uri_parser import parse_uri


class DB:
    """
    Small wrapper for mongodb collection calls
    """
    MAX_CODE_LEN = 9
    PAGE_SIZE = 5

    def __init__(self, mongo_uri):
        parsed_host = parse_uri(mongo_uri)

        self.conn = MongoClient(mongo_uri)
        self.database = parsed_host['database']

    def create_indexes(self):
        """
        adding mongo indexes for quick queries, and secure rules for users
        """
        db = self.conn[self.database]
        # email/api must be unique
        try:
            db.users.create_index([('email', 1), ('api_key', 1)], unique=True)
        except OperationFailure: # pragma: no cover
            # index already exists
            pass

        # adding index on `code` field
        try:
            db.urls.create_index('code', unique=True)
        except OperationFailure: # pragma: no cover
            # index already exists
            pass

    @staticmethod
    def sanitize_query(query):
        """
        Sanitize will validate the query param, returning false for bad params
        and adding ObjectId for _id fields
        """
        if type(query) != dict:
            return False

        if '_id' in query:
            query['_id'] = ObjectId(query['_id'])

        return query

    def find_one_url(self, query, projection=None):
        """
        wraps pymongo collection.find_one for urls collection
        """
        query = self.sanitize_query(query)
        if not query:
            return None

        res = self.conn[self.database].urls.find_one(query)
        return res

    def find_urls(self, user_id, page=1):
        """
        Returns a list of user urls, paginated
        """
        db = self.conn[self.database]
        skip = (page - 1) * self.PAGE_SIZE
        return db.urls.find(
            {'created_by': ObjectId(user_id)}
        ).skip(skip).limit(self.PAGE_SIZE).sort('created_at', -1)

    def insert_url(self, query):
        """
        wraps pymongo collection.insert_one for urls collection
        """
        query = self.sanitize_query(query)
        return self.conn[self.database].urls.insert_one(query)

    def update_url(self, query, change):
        """
        wraps collection.update for urls collection
        """
        return self.conn[self.database].urls.update(query, change)

    def insert_user(self, query):
        """
        wraps pymongo collection.insert_one for users collection
        """
        query = self.sanitize_query(query)
        return self.conn[self.database].users.insert_one(query)

    def find_one_user(self, query):
        """
        wraps pymongo collection.find_one for users collection
        """
        query = self.sanitize_query(query)
        return self.conn[self.database].users.find_one(query)

    def generate_url_code(self, host):
        """
        Helper method to create a short url code.
        host + code = 23 chars
        with 54 possible chars (string.ascii_letters)
        9 digit code = 54^9 possibilities
        +
        14 host len (including http scheme, dots and slash, eg. http://bit.ly/)
        """
        code = ''.join(random.choice(string.ascii_letters) for i in
                       range(self.MAX_CODE_LEN))
        exists = self.find_one_url({'code': code})
        while exists:
            code = ''.join(random.choice(string.ascii_letters) for i in
                           range(self.MAX_CODE_LEN))
            exists = self.find_one_url({'code': code})
        return code

    def close(self):
        """
        wraps connection.close() method
        """
        return self.conn.close()
