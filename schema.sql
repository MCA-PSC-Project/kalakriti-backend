BEGIN;
--------------TYPES----------------------
CREATE type "media__type" as enum ('image', 'audio', 'video', 'file');
CREATE type "user__type" as enum ('customer', 'seller', 'admin', 'super_admin');
CREATE type "gender__type" as enum ('male', 'female', 'other');
CREATE type "order__status" as enum (
	'initiated',
	'pending',
	'confirmed_by_seller',
	'cancelled_by_seller',
	'cancelled_by_customer',
	'dispatched',
	'shipped',
	'delivered',
	'return_request',
	'return_apporved',
	'returned',
	'sold'
);
CREATE type "payment__status" as enum ('failure', 'success', 'pending');
CREATE type "approval__status" as enum ('pending', 'approved', 'rejected');
-----------------------TABLES-------------------------------------------
CREATE TABLE "media"(
	"id" serial PRIMARY KEY,
	"name" varchar,
	"path" varchar NOT NULL,
	"media_type" media__type NOT NULL,
	"added_at" TIMESTAMPTZ NOT NULL
);
CREATE TABLE "users"(
	"id" serial PRIMARY KEY,
	"first_name" varchar NOT NULL,
	"last_name" varchar NOT NULL,
	"user_type" user__type NOT NULL DEFAULT 'customer',
	"email" VARCHAR NOT NULL UNIQUE,
	"phone" VARCHAR(15) UNIQUE DEFAULT NULL,
	"password" varchar NOT NULL,
	"dob" date NOT NULL,
	"gender" gender__type NOT NULL,
	"added_at" timestamptz NOT NULL,
	"updated_at" timestamptz DEFAULT NULL,
	"dp_id" int DEFAULT NULL,
	"trash" boolean NOT NULL DEFAULT false,
	"is_verified" boolean NOT NULL DEFAULT false,
	"verified_at" timestamptz DEFAULT NULL,
	"enabled" BOOLEAN DEFAULT TRUE,
	FOREIGN KEY("dp_id") references "media"("id") ON DELETE
	SET NULL
);
CREATE TABLE "user_address"(
	"id" serial PRIMARY KEY,
	"user_id" integer,
	"address" varchar NOT NULL,
	"city" varchar NOT NULL,
	"state" varchar NOT NULL,
	"district" varchar NOT NULL,
	"country" varchar NOT NULL,
	"pincode" varchar NOT NULL,
	"added_at" timestamptz NOT NULL,
	"updated_at" timestamptz DEFAULT NULL,
	FOREIGN KEY("user_id") references "users"("id") ON DELETE CASCADE
);
CREATE TABLE "categories"(
	"id" serial PRIMARY KEY,
	"name" varchar NOT NULL UNIQUE,
	"added_at" timestamptz NOT NULL,
	"updated_at" timestamptz DEFAULT NULL,
	"added_by" int,
	"cover_id" int,
	"parent_id" int DEFAULT NULL,
	FOREIGN KEY("added_by") references "users"("id") ON DELETE
	SET NULL,
		FOREIGN KEY("parent_id") references "categories"("id") ON DELETE CASCADE,
		FOREIGN KEY("cover_id") references "media"("id") ON DELETE
	SET NULL
);
CREATE TABLE "products"(
	"id" serial PRIMARY KEY,
	"product_name" varchar NOT NULL,
	"product_description" varchar NOT NULL,
	"category_id" int NOT NULL,
	"subcategory_id" int,
	"original_price" FLOAT NOT NULL,
	"offer_price" FLOAT NOT NULL,
	"added_at" timestamptz NOT NULL,
	"updated_at" timestamptz DEFAULT NULL,
	"has_variants" BOOLEAN DEFAULT false,
	"quantity_in_stock" int NOT NULL,
	"SKU" varchar(50) UNIQUE NOT NULL,
	FOREIGN KEY("category_id") references "categories"("id") ON DELETE
	SET NULL,
		FOREIGN KEY("subcategory_id") references "categories"("id") ON DELETE
	SET NULL
);
CREATE TABLE "variants" (
	"id" serial primary key,
	"variant_type" VARCHAR NOT NULL
);
CREATE TABLE "variant_value"(
	"id" serial primary key,
	"variant_id" int,
	"value" varchar(50) NOT NULL,
	FOREIGN KEY("variant_id") references "variants"("id") ON DELETE CASCADE
);
CREATE TABLE "product_variants"(
	"id" serial primary key,
	"product_id" int,
	"product_variant_name" varchar(50) NOT NULL,
	"SKU" varchar(50) UNIQUE NOT NULL,
	"original_price" FLOAT NOT NULL,
	"offer_price" FLOAT NOT NULL,
	"quantity_in_stock" int NOT NULL,
	FOREIGN KEY("product_id") references "products"("id") ON DELETE CASCADE
);
CREATE TABLE "product_variants_values"(
	"id" serial primary key,
	"product_variants_id" int,
	"variant_value_id" int,
	FOREIGN KEY("product_variants_id") references "product_variants"("id") ON DELETE CASCADE,
	FOREIGN KEY("variant_value_id") references "variant_value"("id") ON DELETE CASCADE
);
CREATE TABLE "wishlists"(
	"user_id" int NOT NULL,
	"product_id" int NOT NULL,
	"product_variant_id" int,
	"added_at" timestamptz NOT NULL,
	-- PRIMARY KEY("user_id", "product_id"),
	UNIQUE("user_id", "product_id", "product_variant_id"),
	FOREIGN KEY("user_id") references "users"("id") ON DELETE
	SET NULL,
		FOREIGN KEY("product_id") references "products"("id") ON DELETE CASCADE,
		FOREIGN KEY("product_variant_id") references "product_variants"("id") ON DELETE CASCADE
);
CREATE TABLE "carts"(
	"id" serial PRIMARY KEY,
	"user_id" int,
	FOREIGN KEY("user_id") references "users"("id") ON DELETE
	SET NULL
);
CREATE TABLE "cart_products"(
	"cart_id" int NOT NULL,
	"product_id" int NOT NULL,
	"product_variant_id" int,
	"quantity" int DEFAULT 1,
	"added_at" timestamptz NOT NULL,
	"updated_at" timestamptz NOT NULL,
	-- PRIMARY KEY("cart_id", "product_id"),
	UNIQUE("cart_id", "product_id", "product_variant_id"),
	FOREIGN KEY("cart_id") references "carts"("id") ON DELETE CASCADE,
	FOREIGN KEY("product_id") references "products"("id") ON DELETE CASCADE,
	FOREIGN KEY("product_variant_id") references "product_variants"("id") ON DELETE CASCADE
);
CREATE TABLE "banners"(
	"id" serial PRIMARY KEY,
	"media_id" int,
	"redirect_type" varchar,
	"redirect_url" varchar NOT NULL,
	FOREIGN KEY("media_id") references "media"("id")
);
CREATE TABLE "orders"(
	"id" serial PRIMARY KEY,
	"user_id" integer,
	"address" varchar NOT NULL,
	"city" varchar NOT NULL,
	"state" varchar NOT NULL,
	"district" varchar NOT NULL,
	"country" varchar NOT NULL,
	"pincode" varchar NOT NULL,
	"phone" varchar NOT NULL,
	"ordered_at" timestamptz NOT NULL,
	"order_status" order__status,
	"updated_at" timestamptz DEFAULT NULL,
	"sub_total" numeric NOT NULL,
	"discount" numeric NOT NULL DEFAULT 0,
	"tax" numeric NOT NULL DEFAULT 0,
	"grand_total" numeric NOT NULL,
	FOREIGN KEY("user_id") references "users"("id") ON DELETE CASCADE
);
CREATE TABLE "ordered_products"(
	"order_id" int,
	"product_id" int,
	"SKU" varchar,
	"original_price" numeric NOT NULL,
	"offer_price" numeric NOT NULL,
	"discount" numeric NOT NULL,
	"tax" numeric NOT NULL,
	"quantity" numeric DEFAULT 1,
	FOREIGN KEY("order_id") references "orders"("id") ON DELETE
	SET NULL,
		FOREIGN KEY("product_id") references "products"("id") ON DELETE
	SET NULL
);
CREATE TABLE "product_reviews"(
	"product_id" int,
	"SKU" varchar,
	"user_id" int,
	"rating" numeric(2, 1),
	"review" varchar,
	"added_at" timestamptz NOT NULL,
	"updated_at" timestamptz NOT NULL,
	PRIMARY KEY("product_id", "user_id"),
	FOREIGN KEY("product_id") references "products"("id") ON DELETE
	SET NULL,
		FOREIGN KEY("user_id") references "users"("id") ON DELETE
	SET NULL
);
CREATE TABLE "payments"(
	"id" serial PRIMARY KEY,
	"order_id" int,
	"provider" varchar(50) NOT NULL,
	"provider_order_id" varchar NOT NULL,
	"provider_payment_id" varchar NOT NULL,
	"payment_status" payment__status,
	"added_at" timestamptz NOT NULL,
	"updated_at" timestamptz NOT NULL,
	FOREIGN KEY("order_id") references "orders"("id") ON DELETE
	SET NULL
);
CREATE TABLE "seller_applicant_forms"(
	"id" serial PRIMARY KEY,
	"name" varchar NOT NULL,
	"email" varchar NOT NULL,
	"mobile_no" varchar NOT NULL,
	"reviewed" BOOLEAN DEFAULT false,
	"added_at" timestamptz NOT NULL,
	"updated_at" timestamptz NOT NULL,
	"approval_status" approval__status DEFAULT 'pending',
	"description" varchar,
	"path" varchar DEFAULT ''
);
CREATE TABLE "mobile_otp"(
	"mobile_no" varchar(15) PRIMARY KEY,
	"otp" varchar(6) NOT NULL,
	"expiry" int
);
----- Indexes -----
CREATE INDEX ON "users" ("email");
CREATE INDEX ON "users" ("phone");
END;