BEGIN;
--------------TYPES----------------------
CREATE type "media__type" as enum ('image', 'audio', 'video', 'file');
CREATE type "user__type" as enum ('customer', 'seller', 'admin', 'super_admin');
CREATE type "gender__type" as enum ('male', 'female', 'other');
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
	"added_at" timestamp NOT NULL,
	"updated_at" timestamp DEFAULT NULL,
	"dp_id" int,
	"trash" boolean NOT NULL DEFAULT false,
	"is_verified" boolean NOT NULL DEFAULT false,
	"verified_at" timestamp DEFAULT NULL,
	FOREIGN KEY("dp_id") references "media"("id") ON DELETE
	SET NULL
);
----- Indexes -----
CREATE INDEX ON "users" ("email");
CREATE INDEX ON "users" ("phone");
----- Triggers -----
END;