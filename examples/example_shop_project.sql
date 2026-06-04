-- SQL dialect: PostgreSQL

CREATE TABLE "Users" (
    "id" INTEGER PRIMARY KEY,
    "login" VARCHAR(255) NOT NULL UNIQUE,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "password_hash" VARCHAR(255) NOT NULL,
    "created_at" DATE NOT NULL,
    "is_active" BOOLEAN NOT NULL
);

CREATE TABLE "Roles" (
    "id" INTEGER PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE "UserRoles" (
    "id" INTEGER PRIMARY KEY,
    "user_id" INTEGER NOT NULL,
    "role_id" INTEGER NOT NULL,
    "assigned_at" DATE NOT NULL
);

CREATE TABLE "Categories" (
    "id" INTEGER PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "description" TEXT
);

CREATE TABLE "Products" (
    "id" INTEGER PRIMARY KEY,
    "category_id" INTEGER NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "sku" VARCHAR(255) NOT NULL UNIQUE,
    "price" NUMERIC NOT NULL,
    "in_stock" BOOLEAN NOT NULL
);

CREATE TABLE "Orders" (
    "id" INTEGER PRIMARY KEY,
    "user_id" INTEGER NOT NULL,
    "order_date" DATE NOT NULL,
    "status" VARCHAR(255) NOT NULL,
    "total" NUMERIC NOT NULL
);

CREATE TABLE "OrderItems" (
    "id" INTEGER PRIMARY KEY,
    "order_id" INTEGER NOT NULL,
    "product_id" INTEGER NOT NULL,
    "quantity" INTEGER NOT NULL,
    "price" NUMERIC NOT NULL
);

CREATE TABLE "Payments" (
    "id" INTEGER PRIMARY KEY,
    "order_id" INTEGER NOT NULL,
    "amount" NUMERIC NOT NULL,
    "paid_at" DATE NOT NULL,
    "method" VARCHAR(255) NOT NULL,
    "status" VARCHAR(255) NOT NULL
);

-- Связи (FOREIGN KEY)
ALTER TABLE "UserRoles" ADD CONSTRAINT "fk_UserRoles_Users" FOREIGN KEY ("user_id") REFERENCES "Users"("id");
ALTER TABLE "UserRoles" ADD CONSTRAINT "fk_UserRoles_Roles" FOREIGN KEY ("role_id") REFERENCES "Roles"("id");
ALTER TABLE "Products" ADD CONSTRAINT "fk_Products_Categories" FOREIGN KEY ("category_id") REFERENCES "Categories"("id");
ALTER TABLE "Orders" ADD CONSTRAINT "fk_Orders_Users" FOREIGN KEY ("user_id") REFERENCES "Users"("id");
ALTER TABLE "OrderItems" ADD CONSTRAINT "fk_OrderItems_Orders" FOREIGN KEY ("order_id") REFERENCES "Orders"("id");
ALTER TABLE "OrderItems" ADD CONSTRAINT "fk_OrderItems_Products" FOREIGN KEY ("product_id") REFERENCES "Products"("id");
ALTER TABLE "Payments" ADD CONSTRAINT "fk_Payments_Orders" FOREIGN KEY ("order_id") REFERENCES "Orders"("id");
