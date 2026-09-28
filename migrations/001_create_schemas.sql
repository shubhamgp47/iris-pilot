-- Enable PostGIS extension in public schema
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create staging and core namespaces
CREATE SCHEMA IF NOT EXISTS iris_staging;
CREATE SCHEMA IF NOT EXISTS iris_core;