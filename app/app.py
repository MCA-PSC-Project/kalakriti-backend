# import psycopg2
from psycopg2.pool import SimpleConnectionPool
from flask import Flask, request
from flask_restful import Api
import flask_jwt_extended
import flask_mail
import boto3
import atexit

# local imports
from app.config import app_config
from app.resources.auth import Register, Login, RefreshToken, VerifyEmail
from app.resources.product_items import ProductItems, SellersProductItems
from app.resources.products import Products, SellersProducts
from app.resources.search import Search, TopSearches
from app.resources.tags import Tags
from app.resources.user import UserProfile, ResetEmail, ResetPhone, ResetPassword
from app.resources.media import UploadImage, UploadAudio, UploadVideo, UploadFile, DeleteMedia
from app.resources.categories import Categories
from app.resources.admin import GetSeller, GetCustomer, EnableDisableUser, PromoteToSeller
from app.resources.super_admin import GetAllAdmins, PromoteToAdmin
from app.resources.banners import Banners
from app.resources.seller_applicant_form import Seller_Applicant_Form
from app.resources.wishlists import Wishlists

import app.app_globals as app_globals

# db_conn = psycopg2.connect()

# @app.get("/")  # http://127.0.0.1:5000/
# def get_index():
#     return "Welcome to task tracker app!!!"

# db_conn=None


def create_app(config_name):
    app = Flask(__name__)
    api = Api(app)

    app.config.from_object(app_config[config_name])
    app.config.from_pyfile('config.py')

    app.logger.debug(app_config[config_name])
    app.logger.debug('DATABASE_URI=%s ' % app.config['DATABASE_URI'])
    app.logger.debug('SECRET_KEY=%s ' % app.config['SECRET_KEY'])

    # app_globals.db_conn = psycopg2.connect(app.config['DATABASE_URI'])

    # Connection pooling
    app_globals.db_conn_pool = SimpleConnectionPool(
        minconn=1, maxconn=10, dsn=app.config['DATABASE_URI'])
    app_globals.db_conn = app_globals.db_conn_pool.getconn()
    if app_globals.db_conn == None:
        app.logger.fatal('Database connection error')
    app_globals.db_conn.autocommit = True

    jwt = flask_jwt_extended.JWTManager(app)
    app_globals.mail = flask_mail.Mail(app)

    app_globals.s3 = boto3.client(
        "s3",
        endpoint_url=app.config['S3_ENDPOINT'],
        aws_access_key_id=app.config['S3_KEY'],
        aws_secret_access_key=app.config['S3_SECRET']
    )

    response = app_globals.s3.list_buckets()
    print('Existing buckets:')
    for bucket in response['Buckets']:
        print(f'  {bucket["Name"]}')
    # Endpoints

    # Media
    api.add_resource(UploadImage, '/uploads/image')
    api.add_resource(UploadAudio, '/uploads/audio')
    api.add_resource(UploadVideo, '/uploads/video')
    api.add_resource(UploadFile, '/uploads/file')
    # only for testing purpose
    api.add_resource(DeleteMedia, '/uploads/media/<int:media_id>')

    # Auth
    api.add_resource(Register, '/auth/register')
    api.add_resource(Login, '/auth/login')
    api.add_resource(RefreshToken, '/auth/refresh')
    api.add_resource(VerifyEmail, '/auth/verify-email')

    # todo: Resets
    api.add_resource(ResetEmail, '/reset-email')
    api.add_resource(ResetPhone, '/reset-phone')
    api.add_resource(ResetPassword, '/reset-password')

    # User Profile
    api.add_resource(UserProfile, '/users/profile')

    # Category & Subcategory
    api.add_resource(Categories, '/categories',
                     '/categories/<int:category_id>')

    # Admin related endpoints
    api.add_resource(GetSeller, '/sellers')
    api.add_resource(GetCustomer, '/customers')
    api.add_resource(EnableDisableUser, '/users/<int:users_id>/status')
    api.add_resource(PromoteToSeller, '/admin/sellers/promote')

    # Super_Admin related endpoints
    api.add_resource(GetAllAdmins, '/admins')
    api.add_resource(PromoteToAdmin, '/super-admin/admin/promote')

    # Banners
    api.add_resource(Banners, '/banners',
                     '/banners/<int:banner_id>')

    # Products
    api.add_resource(Products, '/products/<int:product_id>')

    api.add_resource(ProductItems, '/product-items/<int:product_item_id>')

    api.add_resource(SellersProducts, '/sellers/products',
                     '/sellers/products/<int:product_id>')

    api.add_resource(SellersProductItems, '/sellers/product-items',
                     '/sellers/product-items/<int:product_item_id>')

    # Tags
    api.add_resource(Tags, '/products/<int:product_id>/tags')

    # Seller_Applicant_Form
    api.add_resource(Seller_Applicant_Form, '/sellers-form',
                     '/sellers-form/<int:seller_id>')
    
    #Wishlists
    api.add_resource(Wishlists, '/wishlists',
                       '/wishlists/<int:product_item_id>')

    # Search
    api.add_resource(Search, '/search')
    api.add_resource(TopSearches, '/top-searches')

    # to be exceuted at app exit for cleanups
    @atexit.register
    def close_connection_pool():
        # app.logger.debug(app_globals.db_conn_pool)
        if app_globals.db_conn_pool:
            app_globals.db_conn_pool.closeall()
        app.logger.debug("Connection pool closed")
    return app
