# import psycopg2
from flask_cors import CORS
from jwt import ExpiredSignatureError
from psycopg2.pool import SimpleConnectionPool
from flask import Flask, request, jsonify
from flask_restful import Api
import flask_jwt_extended
import flask_mail
import boto3
import atexit

import redis
import razorpay

# local imports
from app.config import app_config
from app.resources.address import UserAddress
from app.resources.auth import (
    LoginAdmin,
    LoginCustomer,
    LoginSeller,
    RefreshToken,
    RegisterAdmin,
    RegisterCustomer,
    RegisterSeller,
    VerifyEmail,
)
from app.resources.auth_mfa import (
    MFABackupKey,
    MFAStatus,
    SetupTOTPAuthentication,
    TOTPAuthenticationLogin,
)
from app.resources.auth_otp import (
    GetMobileOtp,
    MobileOtpLoginAdmin,
    MobileOtpLoginCustomer,
    MobileOtpLoginSeller,
)
from app.resources.home import (
    Home,
    NewProducts,
    PopularProducts,
    RecommendedProductsForAnonymousCustomer,
    PersonalizedRecommendedProducts,
    ViewedProducts,
)
from app.resources.orders import OrderItems, Orders, CustomerOrders, SellerOrderList
from app.resources.payment import Payment, PaymentSuccessful
from app.resources.product_items import (
    ProductItems,
    ProductItemsBasicInfoByIds,
    SellersProductBaseItem,
    SellersProductItems,
)
from app.resources.products import (
    Products,
    ProductsAllDetails,
    ProductsByCategory,
    ProductsByQuery,
    SellersProducts,
)
from app.resources.search import Search, TopSearches
from app.resources.tags import Tags
from app.resources.user_profile import CustomerProfile, SellerProfile, AdminProfile
from app.resources.reset import (
    RequestResetEmail,
    RequestResetPassword,
    ResetEmail,
    ResetMobile,
    ResetPassword,
    ResetPasswordLoggedIn,
)
from app.resources.media import (
    BucketObjects,
    UploadImage,
    UploadAudio,
    UploadVideo,
    UploadFile,
    DeleteMedia,
)
from app.resources.categories import Categories
from app.resources.admin import CustomersInfo, PromoteToSeller, SellersInfo
from app.resources.super_admin import AdminsInfo, PromoteToAdmin
from app.resources.banners import Banners
from app.resources.seller_applicant_form import Seller_Applicant_Form
from app.resources.wishlist import IsItemInWishList, Wishlist
from app.resources.cart import Cart, CartItemsQuantity
from app.resources.product_reviews import (
    ProductReview,
    CustomerReviewOnProduct,
    # AddMediaInReview
)
from app.resources.seller_bank_details import Seller_Bank_Details

import app.app_globals as app_globals

# db_conn = psycopg2.connect()

# @app.get("/")  # http://127.0.0.1:5000/
# def get_index():
#     return "Welcome to task tracker app!!!"

# db_conn=None


def create_app(config_name):
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    api = Api(app)
    app.config.from_object(app_config[config_name])
    app.config.from_pyfile("config.py")

    app.logger.debug(app_config[config_name])
    app.logger.debug("DATABASE_URI=%s" % app.config["DATABASE_URI"])
    app.logger.debug("REDIS_URL=%s" % app.config["REDIS_URL"])
    # app.logger.debug("SECRET_KEY=%s" % app.config["SECRET_KEY"])

    # app_globals.db_conn = psycopg2.connect(app.config['DATABASE_URI'])

    keepalive_args = {
        # Controls whether client-side TCP keepalives are used. The default value is 1, meaning on, but you can change this to 0, meaning off, if keepalives are not wanted.
        "keepalives": 1,
        # Controls the number of seconds of inactivity after which TCP should send a keepalive message to the server. A value of zero uses the system default.
        "keepalives_idle": 25,
        # Controls the number of seconds after which a TCP keepalive message that is not acknowledged by the server should be retransmitted. A value of zero uses the system default.
        "keepalives_interval": 10,
        # Controls the number of TCP keepalives that can be lost before the client's connection to the server is considered dead. A value of zero uses the system default.
        "keepalives_count": 5,
    }
    # Connection pooling
    app_globals.db_conn_pool = SimpleConnectionPool(
        minconn=1, maxconn=10, dsn=app.config["DATABASE_URI"], **keepalive_args
    )

    app_globals.db_conn = app_globals.db_conn_pool.getconn()
    if app_globals.db_conn == None:
        app.logger.fatal("Database connection error")
    app_globals.db_conn.autocommit = True

    app_globals.redis_client = redis.Redis.from_url(url=app.config["REDIS_URL"])
    if not app_globals.redis_client.ping():
        app.logger.fatal("Redis connection error")
    app.config['PROPAGATE_EXCEPTIONS'] = True
    jwt = flask_jwt_extended.JWTManager(app)
    app_globals.mail = flask_mail.Mail(app)

    app_globals.s3 = boto3.client(
        "s3",
        endpoint_url=app.config["S3_ENDPOINT"],
        aws_access_key_id=app.config["S3_KEY"],
        aws_secret_access_key=app.config["S3_SECRET"],
    )
    response = app_globals.s3.list_buckets()
    print("Existing buckets:")
    for bucket in response["Buckets"]:
        print(f'{bucket["Name"]}')

    app_globals.payment_client = razorpay.Client(
        auth=(app.config["PAYMENT_API_KEY"], app.config["PAYMENT_SECRET_KEY"])
    )
    app_globals.payment_client.set_app_details(
        {"title": app.config["APP_NAME"], "version": app.config["APP_VERSION"]}
    )

    # Endpoints

    # Media
    api.add_resource(UploadImage, "/uploads/image")
    api.add_resource(UploadAudio, "/uploads/audio")
    api.add_resource(UploadVideo, "/uploads/video")
    api.add_resource(UploadFile, "/uploads/file")
    # only for testing purpose
    api.add_resource(DeleteMedia, "/uploads/media/<int:media_id>")
    api.add_resource(BucketObjects, "/uploads/media/all")

    # Auth
    api.add_resource(RegisterCustomer, "/customers/auth/register")
    api.add_resource(RegisterSeller, "/sellers/auth/register")
    api.add_resource(RegisterAdmin, "/admins/auth/register")

    api.add_resource(LoginCustomer, "/customers/auth/login")
    api.add_resource(LoginSeller, "/sellers/auth/login")
    api.add_resource(LoginAdmin, "/admins/auth/login")

    api.add_resource(RefreshToken, "/auth/refresh")
    api.add_resource(VerifyEmail, "/auth/verify-email")

    # MOTP
    api.add_resource(GetMobileOtp, "/auth/motp")
    api.add_resource(MobileOtpLoginCustomer, "/customers/auth/motp/login")
    api.add_resource(MobileOtpLoginSeller, "/sellers/auth/motp/login")
    api.add_resource(MobileOtpLoginAdmin, "/admins/auth/motp/login")

    # Reset
    api.add_resource(RequestResetEmail, "/reset-email/request")
    api.add_resource(ResetEmail, "/reset-email")
    api.add_resource(ResetMobile, "/reset-mobile")
    api.add_resource(RequestResetPassword, "/reset-password/request")
    api.add_resource(ResetPassword, "/reset-password")
    # user already logged in and using old password
    api.add_resource(ResetPasswordLoggedIn, "/reset-password/logged-in")

    # MFA (TOTP)
    api.add_resource(MFAStatus, "/auth/mfa/status")
    api.add_resource(SetupTOTPAuthentication, "/auth/setup/mfa/totp")
    api.add_resource(TOTPAuthenticationLogin, "/auth/mfa/totp/login")
    api.add_resource(MFABackupKey, "/auth/mfa/backup-key")

    # User Profile
    api.add_resource(CustomerProfile, "/customers/profile")
    api.add_resource(SellerProfile, "/sellers/profile")
    api.add_resource(AdminProfile, "/admins/profile")

    # Address
    api.add_resource(UserAddress, "/addresses", "/addresses/<int:address_id>")

    # Category & Subcategory
    api.add_resource(Categories, "/categories", "/categories/<int:category_id>")

    # Admin related endpoints
    api.add_resource(CustomersInfo, "/customers", "/customers/<int:customer_id>")
    api.add_resource(SellersInfo, "/sellers", "/sellers/<int:seller_id>")

    api.add_resource(PromoteToSeller, "/admins/sellers/promote")  # Deprecated

    # Super_Admin related endpoints
    api.add_resource(AdminsInfo, "/admins", "/admins/<int:admin_id>")
    api.add_resource(PromoteToAdmin, "/super-admins/admins/promote")  # Deprecated

    # Banners
    api.add_resource(Banners, "/banners", "/banners/<int:banner_id>")

    # Products
    api.add_resource(ProductsByCategory, "/categories/products")
    api.add_resource(ProductsByQuery, "/products")
    api.add_resource(Products, "/products/<int:product_id>")
    api.add_resource(ProductItems, "/product-items/<int:product_item_id>")
    api.add_resource(
        SellersProducts, "/sellers/products", "/sellers/products/<int:product_id>"
    )
    api.add_resource(
        SellersProductItems,
        "/sellers/product-items",
        "/sellers/product-items/<int:product_item_id>",
    )
    api.add_resource(SellersProductBaseItem, "/sellers/products/base-item")
    api.add_resource(ProductsAllDetails, "/products/<int:product_id>/all-details")
    api.add_resource(ProductItemsBasicInfoByIds, "/product-items/basic-info")

    # Tags
    api.add_resource(Tags, "/products/<int:product_id>/tags")

    # Seller_Applicant_Form
    api.add_resource(
        Seller_Applicant_Form, "/sellers-form", "/sellers-form/<int:seller_id>"
    )

    # Seller_Bank_Details
    api.add_resource(
        Seller_Bank_Details,
        "/sellers-bank-details",
        "/sellers-bank-details/<int:seller_id>",
        "/sellers-bank-details/<int:bank_detail_id>/bank",
    )

    # Wishlist
    api.add_resource(Wishlist, "/wishlists", "/wishlists/<int:product_item_id>")
    api.add_resource(IsItemInWishList, "/check-wishlists/<int:product_item_id>")

    # Cart
    api.add_resource(Cart, "/carts", "/carts/<int:product_item_id>")
    api.add_resource(CartItemsQuantity, "/carts/items-quantity")

    # Reviews
    api.add_resource(
        ProductReview,
        "/product-reviews",
        "/product-reviews/<int:review_id>",
        "/products/<int:product_id>/product-reviews",
    )
    api.add_resource(CustomerReviewOnProduct, "/product-review/<int:product_id>")
    # api.add_resource(AddMediaInReview, "/product-review/<int:review_id>")

    # Search
    api.add_resource(Search, "/search")
    api.add_resource(TopSearches, "/top-searches")

    # Payment
    api.add_resource(Payment, "/payment/order")
    api.add_resource(PaymentSuccessful, "/payment/success")

    # Orders
    api.add_resource(Orders, "/orders", "/orders/<int:order_id>")  # For POD
    api.add_resource(OrderItems, "/order-items/<int:order_item_id>")
    api.add_resource(CustomerOrders, "/customer-orders")
    api.add_resource(SellerOrderList,"/order-list-for-seller")
    

    # TODO: Homepage related endpoints
    # Home
    api.add_resource(Home, "/home")
    api.add_resource(
        RecommendedProductsForAnonymousCustomer,
        "/recommended-products",
        "/recommended-products/<int:recommended_product_id>",
    )
    api.add_resource(
        PersonalizedRecommendedProducts, "/recommended-products/personalized"
    )
    api.add_resource(PopularProducts, "/popular-products")
    api.add_resource(NewProducts, "/new-products")
    api.add_resource(
        ViewedProducts, "/viewed-products", "/viewed-products/<int:product_id>"
    )

    # @app.errorhandler(ExpiredSignatureError)
    # def handle_expired_token(e):
    #     response = jsonify({"msg": "Token has expired"})
    #     app.logger.debug("Token has expired")
    #     response.status_code = 401
    #     return response

    # to be exceuted at app exit for cleanups
    @atexit.register
    def close_connection_pool():
        # app.logger.debug(app_globals.db_conn_pool)
        if app_globals.db_conn_pool:
            app_globals.db_conn_pool.closeall()
        app.logger.debug("db connection pool closed")

    return app
