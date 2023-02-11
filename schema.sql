BEGIN;
--------------TYPES----------------------
CREATE type "media__type" as enum ('image');
CREATE type "gender__type" as enum ('male', 'female', 'other');
CREATE type "status__type" as enum ('in-progress', 'completed');
CREATE type "task__type" as enum ('my_day', 'planned', 'assigned', 'custom');
CREATE type "product__type" as enum ('grocery', 'stationery', 'electronics', 'other');
CREATE type "theme__type" as enum ('color', 'image', 'none');
CREATE type "mode__type" as enum ('light', 'dark');
CREATE type "top__task__type" as enum ('in-progress', 'completed', 'priority');
CREATE type "event__type" as enum (
	'birthday',
	'marriage_anniversary',
	'death_anniversary',
	'holiday',
	'meeting',
	'conference',
	'other'
);
CREATE type "item__type" as enum (
	'milk',
	'water',
	'newspaper',
	'clothes',
	'other'
);
-----------------------TABLES-------------------------------------------
CREATE TABLE "media"(
	"id" int PRIMARY KEY,
	"name" varchar(20),
	"path" varchar(50),
	"mediatype" media__type
);
CREATE TABLE "users"(
	"id" serial PRIMARY KEY,
	"name" varchar NOT NULL,
	"email" VARCHAR NOT NULL UNIQUE,
	"phone" VARCHAR(13) UNIQUE DEFAULT NULL,
	"password" varchar NOT NULL,
	"dob" date NOT NULL,
	"gender" gender__type NOT NULL,
	"added_at" timestamp NOT NULL,
	"updated_at" timestamp DEFAULT NULL,
	"dp_id" int,
	"trash" boolean DEFAULT false,
	"is_verified" boolean NOT NULL DEFAULT false,
	"verified_at" timestamp DEFAULT NULL,
	FOREIGN KEY("dp_id") references "media"("id") ON DELETE
	SET NULL
);
CREATE TABLE "lists"(
	"id" serial PRIMARY KEY,
	"user_id" integer,
	"name" varchar NOT NULL,
	"added_at" timestamp NOT NULL,
	"updated_at" timestamp DEFAULT NULL,
	FOREIGN KEY("user_id") references "users"("id") ON DELETE CASCADE
);
CREATE TABLE "tasks"(
	"id" serial PRIMARY KEY,
	"user_id" integer,
	"title" varchar NOT NULL,
	"description" varchar,
	"status" status__type NOT NULL DEFAULT 'in-progress',
	"added_at" timestamp NOT NULL,
	"updated_at" timestamp DEFAULT NULL,
	"plan_start_date" timestamp DEFAULT NULL,
	"plan_end_date" timestamp DEFAULT NULL,
	"actual_end_date" timestamp DEFAULT NULL,
	"duration" integer,
	"task_type" task__type NOT NULL,
	"notify" boolean DEFAULT true,
	"repeat" boolean DEFAULT false,
	"priority" boolean DEFAULT false,
	"list_id" integer,
	FOREIGN KEY("user_id") references "users"("id") ON DELETE CASCADE,
	FOREIGN KEY("list_id") references "lists"("id") ON DELETE CASCADE
);
CREATE TABLE "subtasks"(
	"id" serial PRIMARY KEY,
	"user_id" integer,
	"task_id" integer,
	"title" varchar NOT NULL,
	"description" varchar,
	"status" status__type NOT NULL DEFAULT 'in-progress',
	"added_at" timestamp NOT NULL,
	"updated_at" timestamp DEFAULT NULL,
	"plan_start_date" timestamp DEFAULT NULL,
	"plan_end_date" timestamp DEFAULT NULL,
	"actual_end_date" timestamp DEFAULT NULL,
	"duration" integer,
	"subtask_type" task__type NOT NULL,
	"notify" boolean DEFAULT true,
	"repeat" boolean DEFAULT false,
	"priority" boolean DEFAULT false,
	FOREIGN KEY("user_id") references "users"("id") ON DELETE CASCADE,
	FOREIGN KEY("task_id") references "tasks"("id") ON DELETE CASCADE
);
CREATE TABLE "assigned_tasks"(
	"assigner_user_id" integer,
	"assignee_user_id" integer,
	"task_id" integer,
	"assigned_at" timestamp NOT NULL,
	"status" status__type NOT NULL DEFAULT 'in-progress',
	PRIMARY KEY("assignee_user_id", "task_id"),
	FOREIGN KEY("assigner_user_id") references "users"("id") ON DELETE
	SET NULL,
		FOREIGN KEY("assignee_user_id") references "users"("id") ON DELETE
	SET NULL,
		FOREIGN KEY("task_id") references "tasks"("id") ON DELETE CASCADE
);
CREATE TABLE "baskets"(
	"id" serial PRIMARY KEY,
	"user_id" integer,
	"product_name" varchar NOT NULL,
	"status_type" status__type NOT NULL DEFAULT 'in-progress',
	"added_at" timestamp NOT NULL,
	"updated_at" timestamp DEFAULT NULL,
	"completed_at" timestamp DEFAULT NULL,
	"product_type" product__type NOT NULL,
	"repeat" boolean DEFAULT false,
	FOREIGN KEY("user_id") references "users"("id") ON DELETE CASCADE
);
CREATE TABLE "events"(
	"id" serial PRIMARY KEY,
	"name" varchar NOT NULL,
	"user_id" integer,
	"added_at" timestamp NOT NULL,
	"updated_at" timestamp DEFAULT NULL,
	"event_type" event__type NOT NULL,
	"event_date" timestamp NOT NULL,
	"event_end_date" timestamp DEFAULT NULL,
	"notify" boolean DEFAULT true,
	"repeat" boolean DEFAULT false,
	FOREIGN KEY("user_id") references "users"("id") ON DELETE CASCADE
);
CREATE TABLE "bills"(
	"id" serial PRIMARY KEY,
	"user_id" integer,
	"added_at" timestamp NOT NULL,
	"updated_at" timestamp DEFAULT NULL,
	"rate" float NOT NULL,
	"quantity" float NOT NULL,
	"item_type" item__type NOT NULL,
	"paid" boolean DEFAULT false,
	"paid_at" timestamp DEFAULT NULL,
	FOREIGN KEY("user_id") references "users"("id") ON DELETE CASCADE
);
CREATE TABLE "monthly_bills"(
	"id" serial PRIMARY KEY,
	"user_id" integer,
	"cost" float NOT NULL,
	"item_type" item__type NOT NULL,
	FOREIGN KEY("user_id") references "users"("id") ON DELETE CASCADE
);
CREATE TABLE "users_settings"(
	"id" serial PRIMARY KEY,
	"user_id" integer,
	"theme_type" theme__type NOT NULL DEFAULT 'color',
	"theme_color" varchar(10) DEFAULT 'white',
	"background_image_id" integer DEFAULT NULL,
	"confirm_deletion" boolean DEFAULT false,
	"top_task_type" top__task__type NOT NULL DEFAULT 'in-progress',
	"notify" boolean DEFAULT true,
	"mode" mode__type NOT NULL DEFAULT 'light',
	FOREIGN KEY("user_id") references "users"("id") ON DELETE CASCADE,
	FOREIGN KEY("background_image_id") references "media"("id") ON DELETE
	SET NULL
);

----- Indexes -----
CREATE INDEX ON "users" ("email");
CREATE INDEX ON "users" ("phone");

----- Triggers -----


---- todo: add trigger for completed at time when status is completed ----

-- trigger for creating a row in 'users_settings' table when new row is inserted in 'users' table  
CREATE OR REPLACE FUNCTION create_user_settings() RETURNS trigger AS $$  
BEGIN  
	INSERT INTO "users_settings" (user_id) 
	VALUES (NEW.id);
  RETURN NEW;
END; 
$$ LANGUAGE plpgsql;


CREATE TRIGGER "insert_into_users_settings_trigger" AFTER INSERT ON "users" 
FOR EACH ROW EXECUTE PROCEDURE create_user_settings(); 


END;