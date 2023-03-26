from datetime import datetime
from flask import request, abort
from flask_restful import Resource
import psycopg2
import app.app_globals as app_globals
import flask_jwt_extended as f_jwt
import json
from flask import current_app as app


class Home(Resource):
    def get(self):
        pass

class RecommendedProducts(Resource):
    def get(self):
        pass

class PopularProducts(Resource):
    def get(self):
        pass

class NewProducts(Resource):
    def get(self):
        pass
