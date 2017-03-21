import random
import string
import os

from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo.uri_parser import parse_uri


class DB:
    """
    Small wrapper for mongodb collection calls
    """
    def __init__(self, **kwargs):
        mongo_uri = os.environ.get('MONGODB_URI')
        parsed_host = parse_uri(mongo_uri)

        self.conn = MongoClient(mongo_uri)
        self.database = parsed_host['database']

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

    def find_urls(self, user_id):
        """
        Returns a list of user urls
        """
        return self.conn[self.database].urls.find({'created_by': ObjectId(user_id)})

    def insert_url(self, query):
        """
        wraps pymongo collection.insert_one for urls collection
        """
        query = self.sanitize_query(query)
        if not query:
            return None

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
        if not query:
            return None

        return self.conn[self.database].users.insert_one(query)

    def find_one_user(self, query):
        """
        wraps pymongo collection.find_one for users collection
        """
        query = self.sanitize_query(query)
        if not query:
            return None

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
        max_code_len = 9
        code = ''.join(random.choice(string.ascii_letters) for i in
                       range(max_code_len))
        exists = self.find_one_url({'code': code})
        while exists:
            code = ''.join(random.choice(string.ascii_letters) for i in
                           range(max_code_len))
            exists = self.find_one_url({'code': code})
        return code

    def close(self):
        """
        wraps connection.close() method
        """
        return self.conn.close()
