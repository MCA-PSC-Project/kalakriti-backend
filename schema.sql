BEGIN;
--------------TYPES----------------------
CREATE TYPE "media__type" AS ENUM ('image', 'audio', 'video', 'file');
CREATE TYPE "gender__type" AS ENUM ('male', 'female', 'other');
CREATE TYPE "product__status" AS ENUM (
	'published',
	'unpublished',
	'draft',
	'submitted_for_review',
	'review_rejected',
	'trashed'
);
CREATE TYPE "order__status" AS ENUM (
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
	'failure',
	'success'
);
CREATE TYPE "payment__status" AS ENUM ('failure', 'success', 'pending');
CREATE TYPE "approval__status" AS ENUM ('pending', 'approved', 'rejected');
CREATE TYPE "payment__mode" AS ENUM (
	'upi',
	'credit_card',
	'debit_card',
	'cash',
	'net_banking',
	'digital_wallet'
);
CREATE TYPE "account__type" AS ENUM ('savings', 'current', 'overdraft');
CREATE TYPE "two__fa__type" AS ENUM ('none', 'mobile_otp', 'totp');
-----------------------TABLES-------------------------------------------
CREATE TABLE "media"(
	"id" SERIAL PRIMARY KEY,
	"name" VARCHAR,
	"path" VARCHAR NOT NULL,
	"media_type" media__type NOT NULL,
	"added_at" TIMESTAMPTZ NOT NULL
);
CREATE TABLE "customers"(
	"id" SERIAL PRIMARY KEY,
	"first_name" VARCHAR NOT NULL,
	"last_name" VARCHAR NOT NULL,
	"email" VARCHAR NOT NULL UNIQUE,
	"hashed_password" VARCHAR NOT NULL,
	"phone" VARCHAR(15) UNIQUE,
	"dob" date NOT NULL,
	"gender" gender__type NOT NULL,
	"is_verified" boolean NOT NULL DEFAULT FALSE,
	"verified_at" TIMESTAMPTZ,
	"dp_id" INT,
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	"enabled" BOOLEAN NOT NULL DEFAULT TRUE,
	"trashed" boolean NOT NULL DEFAULT FALSE,
	"default_two_fa_type" two__fa__type DEFAULT 'none',
	"totp_secret_key" VARCHAR(32),
	FOREIGN KEY("dp_id") REFERENCES "media"("id") ON DELETE SET NULL
);
CREATE TABLE "admins"(
	"id" SERIAL PRIMARY KEY,
	"first_name" VARCHAR NOT NULL,
	"last_name" VARCHAR NOT NULL,
	"email" VARCHAR NOT NULL UNIQUE,
	"hashed_password" VARCHAR NOT NULL,
	"phone" VARCHAR(15) UNIQUE,
	"dob" date NOT NULL,
	"gender" gender__type NOT NULL,
	"is_verified" boolean NOT NULL DEFAULT FALSE,
	"verified_at" TIMESTAMPTZ,
	"dp_id" INT,
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	"enabled" BOOLEAN NOT NULL DEFAULT TRUE,
	"trashed" boolean NOT NULL DEFAULT FALSE,
	"is_super_admin" BOOLEAN DEFAULT FALSE,
	FOREIGN KEY("dp_id") REFERENCES "media"("id") ON DELETE SET NULL
);
CREATE TABLE "sellers"(
	"id" SERIAL PRIMARY KEY,
	"seller_name" VARCHAR NOT NULL,
	"email" VARCHAR NOT NULL UNIQUE,
	"hashed_password" VARCHAR NOT NULL,
	"phone" VARCHAR(15) UNIQUE,
	"GSTIN" VARCHAR(15) UNIQUE,
	"PAN" VARCHAR(10) NOT NULL UNIQUE,
	"is_verified" boolean NOT NULL DEFAULT FALSE,
	"verified_at" TIMESTAMPTZ,
	"dp_id" INT,
	"sign_id" INT,
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	"enabled" BOOLEAN NOT NULL DEFAULT TRUE,
	"trashed" boolean NOT NULL DEFAULT FALSE,
	FOREIGN KEY("dp_id") REFERENCES "media"("id") ON DELETE SET NULL,
	FOREIGN KEY("sign_id") REFERENCES "media"("id") ON DELETE SET NULL
);
CREATE TABLE "seller_bank_details"(
	"id" SERIAL PRIMARY KEY,
	"seller_id" INT,
	"account_holder_name" varchar NOT NULL,
	"account_no" varchar NOT NULL,
	"IFSC" varchar(11) NOT NULL,
	"account_type" account__type NOT NULL,
	FOREIGN KEY ("seller_id") REFERENCES "sellers" ("id") ON DELETE SET NULL
);
CREATE TABLE "addresses"(
	"id" SERIAL PRIMARY KEY,
	"address" VARCHAR NOT NULL,
	"district" VARCHAR NOT NULL,
	"city" VARCHAR NOT NULL,
	"state" VARCHAR NOT NULL,
	"country" VARCHAR NOT NULL,
	"pincode" VARCHAR NOT NULL,
	"landmark" VARCHAR(50),
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	"trashed" BOOLEAN DEFAULT FALSE
);
CREATE TABLE "customer_addresses"(
	"customer_id" INT,
	"address_id" INT,
	PRIMARY KEY("customer_id", "address_id"),
	FOREIGN KEY("customer_id") REFERENCES "customers"("id") ON DELETE CASCADE,
	FOREIGN KEY("address_id") REFERENCES "addresses"("id") ON DELETE CASCADE
);
CREATE TABLE "seller_addresses"(
	"seller_id" INT,
	"address_id" INT,
	PRIMARY KEY("seller_id", "address_id"),
	FOREIGN KEY("seller_id") REFERENCES "sellers"("id") ON DELETE CASCADE,
	FOREIGN KEY("address_id") REFERENCES "addresses"("id") ON DELETE CASCADE
);
CREATE TABLE "categories"(
	"id" SERIAL PRIMARY KEY,
	"name" VARCHAR NOT NULL UNIQUE,
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	"added_by" INT,
	"cover_id" INT,
	"parent_id" INT,
	FOREIGN KEY("added_by") REFERENCES "admins"("id") ON DELETE SET NULL,
	FOREIGN KEY("parent_id") REFERENCES "categories"("id") ON DELETE CASCADE,
	FOREIGN KEY("cover_id") REFERENCES "media"("id") ON DELETE SET NULL
);
CREATE TABLE "products"(
	"id" SERIAL PRIMARY KEY,
	"product_name" VARCHAR NOT NULL,
	"product_description" VARCHAR NOT NULL,
	"category_id" INT,
	"subcategory_id" INT,
	"seller_id" INT NOT NULL,
	"currency" varchar(5) DEFAULT 'INR',
	"product_status" product__status DEFAULT ('draft'),
	"min_order_quantity" INT NOT NULL DEFAULT 1,
	"max_order_quantity" INT NOT NULL,
	"tags" text [],
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	"trashed" BOOLEAN DEFAULT FALSE,
	FOREIGN KEY("category_id") REFERENCES "categories"("id") ON DELETE SET NULL,
	FOREIGN KEY("subcategory_id") REFERENCES "categories"("id") ON DELETE SET NULL,
	FOREIGN KEY("seller_id") REFERENCES "sellers"("id") ON DELETE CASCADE
);
CREATE TABLE "variants" (
	"id" SERIAL PRIMARY KEY,
	"variant" VARCHAR NOT NULL UNIQUE
);
CREATE TABLE "variant_values"(
	"id" SERIAL PRIMARY KEY,
	"variant_id" INT,
	"variant_value" VARCHAR(50) NOT NULL,
	FOREIGN KEY("variant_id") REFERENCES "variants"("id") ON DELETE CASCADE
);
CREATE TABLE "product_items"(
	"id" SERIAL PRIMARY KEY,
	"product_id" INT NOT NULL,
	"product_variant_name" VARCHAR(50) NOT NULL,
	"SKU" VARCHAR(50) UNIQUE NOT NULL,
	"original_price" NUMERIC NOT NULL,
	"offer_price" NUMERIC NOT NULL,
	"quantity_in_stock" INT NOT NULL,
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	"product_item_status" product__status DEFAULT ('draft'),
	"trashed" BOOLEAN DEFAULT FALSE,
	FOREIGN KEY("product_id") REFERENCES "products"("id") ON DELETE CASCADE
);
CREATE TABLE "product_base_item"(
	"product_id" INT NOT NULL UNIQUE,
	"product_item_id" INT NOT NULL UNIQUE,
	FOREIGN KEY("product_id") REFERENCES "products"("id") ON DELETE CASCADE,
	FOREIGN KEY("product_item_id") REFERENCES "product_items"("id") ON DELETE CASCADE
);
CREATE TABLE "product_item_values"(
	"id" SERIAL PRIMARY KEY,
	"product_item_id" INT,
	"variant_value_id" INT,
	FOREIGN KEY("product_item_id") REFERENCES "product_items"("id") ON DELETE CASCADE,
	FOREIGN KEY("variant_value_id") REFERENCES "variant_values"("id") ON DELETE CASCADE
);
CREATE TABLE "product_item_medias"(
	-- "id" SERIAL PRIMARY KEY,
	"media_id" INT NOT NULL,
	"product_item_id" INT NOT NULL,
	"display_order" SMALLINT NOT NULL,
	PRIMARY KEY("media_id", "product_item_id"),
	UNIQUE("product_item_id", "display_order"),
	FOREIGN KEY("media_id") REFERENCES "media"("id") ON DELETE SET NULL,
	FOREIGN KEY("product_item_id") REFERENCES "product_items"("id") ON DELETE CASCADE
);
CREATE TABLE "wishlists"(
	"customer_id" INT NOT NULL,
	"product_item_id" INT NOT NULL,
	"added_at" TIMESTAMPTZ NOT NULL,
	PRIMARY KEY("customer_id", "product_item_id"),
	FOREIGN KEY("customer_id") REFERENCES "customers"("id") ON DELETE CASCADE,
	FOREIGN KEY("product_item_id") REFERENCES "product_items"("id") ON DELETE CASCADE
);
CREATE TABLE "carts"(
	"id" SERIAL PRIMARY KEY,
	"customer_id" INT NOT NULL UNIQUE,
	FOREIGN KEY("customer_id") REFERENCES "customers"("id") ON DELETE CASCADE
);
CREATE TABLE "cart_items"(
	"cart_id" INT NOT NULL,
	"product_item_id" INT NOT NULL,
	"quantity" INT NOT NULL DEFAULT 1,
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	PRIMARY KEY("cart_id", "product_item_id"),
	FOREIGN KEY("cart_id") REFERENCES "carts"("id") ON DELETE CASCADE,
	FOREIGN KEY("product_item_id") REFERENCES "product_items"("id") ON DELETE CASCADE
);
CREATE TABLE "banners"(
	"id" SERIAL PRIMARY KEY,
	"media_id" INT,
	"redirect_type" VARCHAR,
	"redirect_url" VARCHAR NOT NULL,
	FOREIGN KEY("media_id") REFERENCES "media"("id") ON DELETE CASCADE
);
CREATE TABLE "orders"(
	"id" SERIAL PRIMARY KEY,
	"customer_id" INT,
	"shipping_address_id" INT,
	"phone" VARCHAR NOT NULL,
	"order_status" order__status DEFAULT 'initiated',
	"total_original_price" NUMERIC NOT NULL,
	"sub_total" NUMERIC NOT NULL,
	"total_discount" NUMERIC NOT NULL DEFAULT 0,
	"total_tax" NUMERIC NOT NULL DEFAULT 0,
	"grand_total" NUMERIC NOT NULL,
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	FOREIGN KEY("customer_id") REFERENCES "customers"("id") ON DELETE SET NULL,
	FOREIGN KEY("shipping_address_id") REFERENCES "addresses"("id") ON DELETE SET NULL
);
CREATE TABLE "order_items"(
	"id" SERIAL PRIMARY KEY,
	"order_id" INT,
	"product_item_id" INT,
	"quantity" INT NOT NULL,
	"original_price" NUMERIC NOT NULL,
	"offer_price" NUMERIC NOT NULL,
	"discount_percent" NUMERIC NOT NULL,
	"discount" NUMERIC NOT NULL,
	"tax" NUMERIC NOT NULL,
	UNIQUE("order_id", "product_item_id"),
	FOREIGN KEY("order_id") REFERENCES "orders"("id") ON DELETE SET NULL,
	FOREIGN KEY("product_item_id") REFERENCES "product_items"("id") ON DELETE SET NULL
);
CREATE TABLE "payments"(
	"id" SERIAL PRIMARY KEY,
	"order_id" INT,
	"provider" VARCHAR(50) NOT NULL,
	"provider_order_id" VARCHAR NOT NULL,
	"provider_payment_id" VARCHAR NOT NULL,
	"payment_mode" payment__mode,
	"payment_status" payment__status,
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ NOT NULL,
	FOREIGN KEY("order_id") REFERENCES "orders"("id") ON DELETE SET NULL
);
CREATE TABLE "product_item_reviews"(
	"id" SERIAL PRIMARY KEY,
	"customer_id" INT,
	"order_item_id" INT,
	"product_item_id" INT,
	"rating" NUMERIC(2, 1),
	"review" VARCHAR(500),
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	UNIQUE("customer_id", "order_item_id"),
	UNIQUE("customer_id", "product_item_id"),
	FOREIGN KEY("customer_id") REFERENCES "customers"("id") ON DELETE SET NULL,
	FOREIGN KEY("order_item_id") REFERENCES "order_items"("id") ON DELETE SET NULL,
	FOREIGN KEY("product_item_id") REFERENCES "product_items"("id") ON DELETE CASCADE
);
CREATE TABLE "seller_applicant_forms"(
	"id" SERIAL PRIMARY KEY,
	"name" VARCHAR NOT NULL,
	"email" VARCHAR NOT NULL UNIQUE,
	"phone" VARCHAR NOT NULL UNIQUE,
	"reviewed" BOOLEAN DEFAULT FALSE,
	"approval_status" approval__status DEFAULT 'pending',
	"description" VARCHAR,
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	"path" VARCHAR DEFAULT ''
);
CREATE TABLE "mobile_otp"(
	"mobile_no" VARCHAR(15) PRIMARY KEY,
	"otp" VARCHAR(6) NOT NULL,
	"expiry" INT
);
CREATE TABLE "top_searches"(
	"rank" smallint,
	"query" varchar,
	PRIMARY KEY("rank")
);
CREATE TABLE "products_tsv_store"(
	"product_id" integer,
	"tsv" tsvector,
	PRIMARY KEY("product_id"),
	FOREIGN KEY ("product_id") REFERENCES "products"("id") ON DELETE CASCADE
);

----- Indexes -----
CREATE INDEX ON "customers" ("email");
CREATE INDEX ON "sellers" ("email");
CREATE INDEX ON "admins" ("email");

CREATE INDEX ON "customers" ("phone");
CREATE INDEX ON "sellers" ("phone");
CREATE INDEX ON "admins" ("phone");

CREATE INDEX ON "categories" ("name");
CREATE INDEX ON "product_items" ("SKU");

----- Inserts -----
INSERT INTO "variants"("variant")
VALUES ('BASE');
INSERT INTO "variants"("variant")
VALUES ('COLOR');
INSERT INTO "variants"("variant")
VALUES ('MATERIAL');
INSERT INTO "variants"("variant")
VALUES ('SIZE');
----- tsv ----
CREATE OR REPLACE FUNCTION products_tsv_trigger() RETURNS trigger AS $$  
BEGIN  
    --code for Insert
    IF TG_OP = 'INSERT' THEN
      INSERT INTO "products_tsv_store" (product_id, tsv) 
      VALUES (
      NEW.id, setweight(to_tsvector('english', COALESCE(NEW.product_name,'')), 'A') || 
      setweight(to_tsvector('english', COALESCE(NEW.product_description,'')), 'B') || 
      setweight(to_tsvector('english', COALESCE(array_to_string(NEW.tags, ' '),'')), 'C')
      );

    --code for Update
    ELSIF TG_OP = 'UPDATE' THEN
        IF NEW.product_name <> OLD.product_name or NEW.product_description <> OLD.product_description or NEW.tags IS NOT NULL THEN
            UPDATE "products_tsv_store" SET tsv =
            setweight(to_tsvector('english', COALESCE(NEW.product_name,'')), 'A') || 
            setweight(to_tsvector('english', COALESCE(NEW.product_description,'')), 'B') || 
            setweight(to_tsvector('english', COALESCE(array_to_string(NEW.tags, ' '),'')), 'C') 
            WHERE product_id = NEW.id;
        END IF;
    END IF;
  RETURN NEW;
END  
$$ LANGUAGE plpgsql;


CREATE TRIGGER "insert_update_tsv_trigger" AFTER INSERT OR UPDATE  
ON products 
FOR EACH ROW EXECUTE PROCEDURE products_tsv_trigger(); 


CREATE OR REPLACE FUNCTION create_cart() RETURNS trigger AS $$  
BEGIN  
      INSERT INTO "carts" (customer_id) 
      VALUES (new.id);
	  RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER "create_cart_trigger" AFTER INSERT ON "customers" 
FOR EACH ROW EXECUTE PROCEDURE create_cart();

CREATE INDEX "tsv_index" ON "products_tsv_store" USING GIN ("tsv");

END;