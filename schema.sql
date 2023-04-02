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
CREATE TYPE "mfa__type" AS ENUM ('motp', 'totp', 'biometric', 'face_recognition');
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
	"mobile_no" VARCHAR(15) UNIQUE,
	"dob" date NOT NULL,
	"gender" gender__type NOT NULL,
	"is_verified" boolean NOT NULL DEFAULT FALSE,
	"verified_at" TIMESTAMPTZ,
	"dp_id" INT,
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	"enabled" BOOLEAN NOT NULL DEFAULT TRUE,
	"trashed" BOOLEAN NOT NULL DEFAULT FALSE,
	"mfa_enabled" BOOLEAN NOT NULL DEFAULT FALSE,
	"hashed_backup_key" VARCHAR,
	FOREIGN KEY("dp_id") REFERENCES "media"("id") ON DELETE
	SET NULL
);
CREATE TABLE "customers_mfa"(
	"id" SERIAL PRIMARY KEY,
	"customer_id" INT,
	"mfa_type" mfa__type NOT NULL DEFAULT 'totp',
	"secret_key" VARCHAR,
	"is_default" BOOLEAN CHECK("is_default" != false),
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	UNIQUE("customer_id", "mfa_type"),
	UNIQUE("customer_id", "is_default"),
	FOREIGN KEY("customer_id") REFERENCES "customers"("id") ON DELETE CASCADE
);
CREATE TABLE "admins"(
	"id" SERIAL PRIMARY KEY,
	"first_name" VARCHAR NOT NULL,
	"last_name" VARCHAR NOT NULL,
	"email" VARCHAR NOT NULL UNIQUE,
	"hashed_password" VARCHAR NOT NULL,
	"mobile_no" VARCHAR(15) UNIQUE,
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
	"mfa_enabled" BOOLEAN NOT NULL DEFAULT FALSE,
	"hashed_backup_key" VARCHAR,
	FOREIGN KEY("dp_id") REFERENCES "media"("id") ON DELETE
	SET NULL
);
CREATE TABLE "admins_mfa"(
	"id" SERIAL PRIMARY KEY,
	"admin_id" INT,
	"mfa_type" mfa__type NOT NULL DEFAULT 'totp',
	"secret_key" VARCHAR,
	"is_default" BOOLEAN CHECK("is_default" != false),
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	UNIQUE("admin_id", "mfa_type"),
	UNIQUE("admin_id", "is_default"),
	FOREIGN KEY("admin_id") REFERENCES "admins"("id") ON DELETE CASCADE
);
CREATE TABLE "sellers"(
	"id" SERIAL PRIMARY KEY,
	"seller_name" VARCHAR NOT NULL,
	"email" VARCHAR NOT NULL UNIQUE,
	"hashed_password" VARCHAR NOT NULL,
	"mobile_no" VARCHAR(15) UNIQUE,
	"GSTIN" VARCHAR(15) UNIQUE CHECK(LENGTH("GSTIN") = 15),
	"PAN" VARCHAR(10) NOT NULL UNIQUE CHECK(LENGTH("PAN") = 10),
	"is_verified" boolean NOT NULL DEFAULT FALSE,
	"verified_at" TIMESTAMPTZ,
	"dp_id" INT,
	"sign_id" INT,
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	"enabled" BOOLEAN NOT NULL DEFAULT TRUE,
	"trashed" boolean NOT NULL DEFAULT FALSE,
	"mfa_enabled" BOOLEAN NOT NULL DEFAULT FALSE,
	"hashed_backup_key" VARCHAR,
	FOREIGN KEY("dp_id") REFERENCES "media"("id") ON DELETE
	SET NULL,
		FOREIGN KEY("sign_id") REFERENCES "media"("id") ON DELETE
	SET NULL
);
CREATE TABLE "sellers_mfa"(
	"id" SERIAL PRIMARY KEY,
	"seller_id" INT,
	"mfa_type" mfa__type NOT NULL DEFAULT 'totp',
	"secret_key" VARCHAR,
	"is_default" BOOLEAN CHECK("is_default" != false),
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	UNIQUE("seller_id", "mfa_type"),
	UNIQUE("seller_id", "is_default"),
	FOREIGN KEY("seller_id") REFERENCES "sellers"("id") ON DELETE CASCADE
);
CREATE TABLE "seller_bank_details"(
	"id" SERIAL PRIMARY KEY,
	"seller_id" INT,
	"account_holder_name" varchar NOT NULL,
	"account_no" varchar NOT NULL,
	"IFSC" varchar(11) NOT NULL CHECK(LENGTH("IFSC") = 11),
	"account_type" account__type NOT NULL,
	FOREIGN KEY ("seller_id") REFERENCES "sellers" ("id") ON DELETE CASCADE
);
CREATE TABLE "addresses"(
	"id" SERIAL PRIMARY KEY,
	"address_line1" VARCHAR(500) NOT NULL,
	"address_line2" VARCHAR(500) NOT NULL,
	"district" VARCHAR(25) NOT NULL,
	"city" VARCHAR(25) NOT NULL,
	"state" VARCHAR(25) NOT NULL,
	"country" VARCHAR(25) NOT NULL,
	"pincode" VARCHAR(10) NOT NULL,
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
CREATE TABLE "admin_addresses"(
	"admin_id" INT,
	"address_id" INT,
	PRIMARY KEY("admin_id", "address_id"),
	FOREIGN KEY("admin_id") REFERENCES "admins"("id") ON DELETE CASCADE,
	FOREIGN KEY("address_id") REFERENCES "addresses"("id") ON DELETE CASCADE
);
CREATE TABLE "categories"(
	"id" SERIAL PRIMARY KEY,
	"name" VARCHAR NOT NULL UNIQUE,
	"added_by" INT,
	"cover_id" INT,
	"parent_id" INT,
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	FOREIGN KEY("added_by") REFERENCES "admins"("id") ON DELETE
	SET NULL,
		FOREIGN KEY("parent_id") REFERENCES "categories"("id") ON DELETE CASCADE,
		FOREIGN KEY("cover_id") REFERENCES "media"("id") ON DELETE
	SET NULL
);
CREATE TABLE "products"(
	"id" SERIAL PRIMARY KEY,
	"product_name" VARCHAR(250) NOT NULL,
	"product_description" VARCHAR(1000) NOT NULL,
	"category_id" INT NOT NULL,
	"subcategory_id" INT,
	"seller_id" INT NOT NULL,
	"currency" varchar(5) NOT NULL DEFAULT 'INR',
	"product_status" product__status DEFAULT ('draft'),
	"min_order_quantity" INT NOT NULL DEFAULT 1,
	"max_order_quantity" INT NOT NULL,
	"tags" text [] CHECK (array_length(tags, 1) <= 15),
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	FOREIGN KEY("category_id") REFERENCES "categories"("id") ON DELETE RESTRICT,
	FOREIGN KEY("subcategory_id") REFERENCES "categories"("id") ON DELETE RESTRICT,
	FOREIGN KEY("seller_id") REFERENCES "sellers"("id") ON DELETE CASCADE,
	CONSTRAINT "order_quantity_check" CHECK("min_order_quantity" <= "max_order_quantity")
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
	"quantity_in_stock" INT NOT NULL CHECK("quantity_in_stock" >= 0),
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	"product_item_status" product__status DEFAULT ('draft'),
	FOREIGN KEY("product_id") REFERENCES "products"("id") ON DELETE CASCADE,
	CONSTRAINT "offer_price_le_original_price" CHECK("offer_price" <= "original_price")
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
	"product_item_id" INT NOT NULL,
	"media_id" INT NOT NULL,
	"display_order" SMALLINT NOT NULL CHECK("display_order" > 0),
	PRIMARY KEY("media_id", "product_item_id"),
	UNIQUE("product_item_id", "display_order"),
	FOREIGN KEY("media_id") REFERENCES "media"("id") ON DELETE
	SET NULL,
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
	"quantity" INT NOT NULL DEFAULT 1 CHECK("quantity" > 0),
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
	"shipping_address_id" INT NOT NULL,
	"mobile_no" VARCHAR NOT NULL,
	"order_status" order__status DEFAULT 'initiated',
	"total_original_price" NUMERIC NOT NULL CHECK ("total_original_price" >= 0),
	"sub_total" NUMERIC NOT NULL CHECK ("sub_total" >= 0),
	"total_discount" NUMERIC NOT NULL DEFAULT 0 CHECK ("total_discount" >= 0),
	"total_tax" NUMERIC NOT NULL DEFAULT 0 CHECK ("total_tax" >= 0),
	"grand_total" NUMERIC NOT NULL CHECK ("grand_total" >= 0),
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	FOREIGN KEY("customer_id") REFERENCES "customers"("id") ON DELETE
	SET NULL,
		FOREIGN KEY("shipping_address_id") REFERENCES "addresses"("id"),
		CONSTRAINT "sub_total_le_total_original_price" CHECK("sub_total" <= "total_original_price")
);
CREATE TABLE "order_items"(
	"id" SERIAL PRIMARY KEY,
	"order_id" INT NOT NULL,
	"product_item_id" INT,
	"quantity" INT NOT NULL CHECK("quantity" > 0),
	"original_price" NUMERIC NOT NULL CHECK ("original_price" >= 0),
	"offer_price" NUMERIC NOT NULL CHECK ("offer_price" >= 0),
	"discount_percent" NUMERIC NOT NULL CHECK ("discount_percent" >= 0),
	"discount" NUMERIC NOT NULL CHECK ("discount" >= 0),
	"tax" NUMERIC NOT NULL CHECK ("tax" >= 0),
	UNIQUE("order_id", "product_item_id"),
	FOREIGN KEY("order_id") REFERENCES "orders"("id"),
	FOREIGN KEY("product_item_id") REFERENCES "product_items"("id") ON DELETE
	SET NULL,
		CONSTRAINT "offer_price_le_original_price" CHECK("offer_price" <= "original_price")
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
	FOREIGN KEY("order_id") REFERENCES "orders"("id") ON DELETE
	SET NULL
);
CREATE TABLE "product_item_reviews"(
	"id" SERIAL PRIMARY KEY,
	"customer_id" INT,
	"order_item_id" INT,
	"product_item_id" INT,
	"rating" NUMERIC(2, 1) CHECK("rating" <= 5),
	"review" VARCHAR(500),
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	UNIQUE("customer_id", "order_item_id"),
	UNIQUE("customer_id", "product_item_id"),
	FOREIGN KEY("customer_id") REFERENCES "customers"("id") ON DELETE
	SET NULL,
		FOREIGN KEY("order_item_id") REFERENCES "order_items"("id") ON DELETE
	SET NULL,
		FOREIGN KEY("product_item_id") REFERENCES "product_items"("id") ON DELETE CASCADE
);
CREATE TABLE "seller_applicant_forms"(
	"id" SERIAL PRIMARY KEY,
	"name" VARCHAR NOT NULL,
	"email" VARCHAR NOT NULL UNIQUE,
	"mobile_no" VARCHAR(15) NOT NULL UNIQUE,
	"reviewed" BOOLEAN DEFAULT FALSE,
	"approval_status" approval__status DEFAULT 'pending',
	"description" VARCHAR,
	"added_at" TIMESTAMPTZ NOT NULL,
	"updated_at" TIMESTAMPTZ,
	"path" VARCHAR DEFAULT ''
);
CREATE TABLE "mobile_otp"(
	"mobile_no" VARCHAR(15) PRIMARY KEY,
	"motp" VARCHAR(6) NOT NULL,
	"expiry_at" TIMESTAMPTZ NOT NULL
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
CREATE INDEX ON "customers" ("mobile_no");
CREATE INDEX ON "sellers" ("mobile_no");
CREATE INDEX ON "admins" ("mobile_no");
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