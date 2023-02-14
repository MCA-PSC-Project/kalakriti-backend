BEGIN;
--------------TYPES----------------------
CREATE type "media__type" as enum ('image', 'audio', 'video', 'doc', 'pdf');
CREATE type "user__type" as enum ('customer', 'seller', 'admin', 'super_admin');
CREATE type "gender__type" as enum ('male', 'female', 'other');
-----------------------TABLES-------------------------------------------
CREATE TABLE "media"(
	"id" int PRIMARY KEY,
	"name" varchar,
	"path" varchar NOT NULL,
	"mediatype" media__type
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
	"dp_id" int,
	"trash" boolean NOT NULL DEFAULT false,
	"is_verified" boolean NOT NULL DEFAULT false,
	"verified_at" timestamptz DEFAULT NULL,
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
	"pincode" varchar NOT NULL,
	"country" varchar NOT NULL,
	"added_at" timestamptz NOT NULL,
	"updated_at" timestamptz DEFAULT NULL,
	FOREIGN KEY("user_id") references "users"("id") ON DELETE CASCADE
);
CREATE TABLE "categories"(
	"id" serial PRIMARY KEY,
	"name" varchar NOT NULL,
	"added_at" timestamptz NOT NULL,
	"updated_at" timestamptz DEFAULT NULL,
	"added_by" int,
	"cover_id" int,
	"parent_id" int DEFAULT NULL,
	FOREIGN KEY("added_by") references "users"("id") ON DELETE CASCADE,
	FOREIGN KEY("parent_id") references "categories"("id"),
	FOREIGN KEY("cover_id") references "media"("id") ON DELETE
	SET NULL
);
CREATE TABLE "products"(
	"id" serial PRIMARY KEY,
	"name" varchar NOT NULL,
	"description" varchar NOT NULL,
	"category_id" int,
	"subcategory_id" int,
    "original_price" decimal(10,2) NOT NULL,
	"offer_price" decimal(10,2) NOT NULL,
	"added_at" timestamptz NOT NULL,
	"updated_at" timestamptz DEFAULT NULL,
	"has_variants" BOOLEAN DEFAULT false,
	"SKU" varchar UNIQUE,
	"stock" int,
	FOREIGN KEY("category_id") references "categories"("id") ON DELETE SET NULL,
	FOREIGN KEY("subcategory_id") references "categories"("id") ON DELETE SET NULL
);
CREATE TABLE "wishlists"(
    "user_id" int ,
	"product_id" int,
	"added_at" timestamptz NOT NULL,
	FOREIGN KEY("user_id") references "users"("id") ON DELETE SET NULL,
	FOREIGN KEY("product_id") references "products"("id") ON DELETE SET NULL,
	PRIMARY KEY(user_id,product_id)
);
CREATE TABLE "carts"(
    "user_id" int PRIMARY KEY ,
	"product_ids" int[],
	"added_at" timestamptz NOT NULL,
	"updated_at" timestamptz NOT NULL,
	FOREIGN KEY("user_id") references "users"("id") ON DELETE SET NULL,
	FOREIGN KEY("product_id") references "products"("id") ON DELETE SET NULL,
);
CREATE TABLE "banners"(
	"id" serial PRIMARY KEY,
	"media_id" int,
	"redirect_type" varchar,
	"redirect_url" varchar NOT NULL,
	FOREIGN KEY("media_id") references "media"("id")
)
----- Indexes -----
CREATE INDEX ON "users" ("email");
CREATE INDEX ON "users" ("phone");
END;