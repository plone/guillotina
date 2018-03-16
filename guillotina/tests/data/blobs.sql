--
-- PostgreSQL database dump
--

-- Dumped from database version 9.6.6
-- Dumped by pg_dump version 10.1

-- Started on 2018-03-16 08:41:38 EDT

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- TOC entry 186 (class 1259 OID 16403)
-- Name: blobs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE blobs (
    bid character varying(32) NOT NULL,
    zoid character varying(32) NOT NULL,
    chunk_index integer NOT NULL,
    data bytea
);


ALTER TABLE blobs OWNER TO postgres;

--
-- TOC entry 2130 (class 0 OID 16403)
-- Dependencies: 186
-- Data for Name: blobs; Type: TABLE DATA; Schema: public; Owner: postgres
--


--
-- TOC entry 2009 (class 1259 OID 16420)
-- Name: blob_bid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX blob_bid ON blobs USING btree (bid);


--
-- TOC entry 2010 (class 1259 OID 16422)
-- Name: blob_chunk; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX blob_chunk ON blobs USING btree (chunk_index);


--
-- TOC entry 2011 (class 1259 OID 16421)
-- Name: blob_zoid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX blob_zoid ON blobs USING btree (zoid);


--
-- TOC entry 2012 (class 2606 OID 16409)
-- Name: blobs blobs_zoid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY blobs
    ADD CONSTRAINT blobs_zoid_fkey FOREIGN KEY (zoid) REFERENCES objects(zoid) ON DELETE CASCADE;


-- Completed on 2018-03-16 08:41:38 EDT

--
-- PostgreSQL database dump complete
--
