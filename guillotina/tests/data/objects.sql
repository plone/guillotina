--
-- PostgreSQL database dump
--

-- Dumped from database version 9.6.6
-- Dumped by pg_dump version 10.1

-- Started on 2018-03-16 09:00:53 EDT

--
-- TOC entry 185 (class 1259 OID 16385)
-- Name: objects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE IF NOT EXISTS objects (
    zoid character varying(32) NOT NULL,
    tid bigint NOT NULL,
    state_size bigint NOT NULL,
    part bigint NOT NULL,
    resource boolean NOT NULL,
    of character varying(32),
    otid bigint,
    parent_id character varying(32),
    id text,
    type text NOT NULL,
    json jsonb,
    state bytea
);


ALTER TABLE objects OWNER TO postgres;

--
-- TOC entry 2136 (class 0 OID 16385)
-- Dependencies: 185
-- Data for Name: objects; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO objects
SELECT 'DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD', 0, 0, 0, false, NULL, NULL, NULL, NULL, 'TRASH_REF', NULL, NULL
WHERE
  NOT EXISTS (
      SELECT zoid FROM objects WHERE zoid = 'DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD'
  );

INSERT INTO objects
SELECT '00000000000000000000000000000000', 1, 64, 0, false, NULL, NULL, NULL, NULL, 'guillotina.db.db.Root', 'null', '\x80049535000000000000008c106775696c6c6f74696e612e64622e6462948c04526f6f749493942981947d948c095f5f64625f69645f5f948c0264629473622e'
WHERE
  NOT EXISTS (
      SELECT zoid FROM objects WHERE zoid = '00000000000000000000000000000000'
  );

INSERT INTO objects VALUES ('8128663836da43acb490446f098da1df', 2, 486, 0, true, NULL, NULL, '00000000000000000000000000000000', 'guillotina', 'Container', '{"id": "guillotina", "path": "/", "uuid": "8128663836da43acb490446f098da1df", "depth": 1, "title": "Guillotina Container", "type_name": "Container", "parent_uuid": "00000000000000000000000000000000", "access_roles": ["guillotina.Reader", "guillotina.Reviewer", "guillotina.Owner", "guillotina.Editor", "guillotina.ContainerAdmin"], "access_users": ["root"], "creation_date": "2018-03-16T12:56:01.525098+00:00", "modification_date": "2018-03-16T12:56:01.525098+00:00"}', '\x800495db010000000000008c126775696c6c6f74696e612e636f6e74656e74948c09436f6e7461696e65729493942981947d94288c09747970655f6e616d659468018c0d6372656174696f6e5f64617465948c086461746574696d65948c086461746574696d65949394430a07e203100c380108032a948c0e646174657574696c2e747a2e747a948c05747a757463949394298194869452948c116d6f64696669636174696f6e5f646174659468108c057469746c65948c144775696c6c6f74696e6120436f6e7461696e6572948c0b6465736372697074696f6e948c204465736372697074696f6e204775696c6c6f74696e6120436f6e7461696e6572948c075f5f61636c5f5f947d948c087072696e726f6c65948c1f6775696c6c6f74696e612e73656375726974792e73656375726974796d6170948c0b53656375726974794d61709493942981947d94288c065f6279726f77947d94288c196775696c6c6f74696e612e436f6e7461696e657241646d696e947d948c04726f6f74948c1e6775696c6c6f74696e612e696e74657266616365732e7365637572697479948c05416c6c6f77949394738c106775696c6c6f74696e612e4f776e6572947d946822682573758c065f6279636f6c947d9468227d94286820682568266825757375627375622e');
INSERT INTO objects VALUES ('8ab4d9007c8f4323844b627624882db8', 2, 205, 0, false, '8128663836da43acb490446f098da1df', NULL, NULL, '_registry', 'guillotina.registry.Registry', 'null', '\x800495c2000000000000008c136775696c6c6f74696e612e7265676973747279948c0852656769737472799493942981947d94288c0464617461947d94288c346775696c6c6f74696e612e696e74657266616365732e72656769737472792e494c61796572732e6163746976655f6c6179657273942891948c2e6775696c6c6f74696e612e696e74657266616365732e72656769737472792e494164646f6e732e656e61626c6564946808758c026964948c095f7265676973747279948c085f5f6e616d655f5f94680b75622e');


--
-- TOC entry 2016 (class 2606 OID 16392)
-- Name: objects objects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE blobs DROP CONSTRAINT IF EXISTS blobs_zoid_fkey;
ALTER TABLE objects DROP CONSTRAINT IF EXISTS objects_of_fkey;
ALTER TABLE objects DROP CONSTRAINT IF EXISTS objects_parent_id_fkey;
ALTER TABLE objects DROP CONSTRAINT IF EXISTS objects_pkey;
ALTER TABLE ONLY objects
    ADD CONSTRAINT objects_pkey PRIMARY KEY (zoid);


--
-- TOC entry 2009 (class 1259 OID 16418)
-- Name: object_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX IF NOT EXISTS object_id ON objects USING btree (id);


--
-- TOC entry 2010 (class 1259 OID 16415)
-- Name: object_of; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX IF NOT EXISTS object_of ON objects USING btree (of);


--
-- TOC entry 2011 (class 1259 OID 16417)
-- Name: object_parent; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX IF NOT EXISTS object_parent ON objects USING btree (parent_id);


--
-- TOC entry 2012 (class 1259 OID 16416)
-- Name: object_part; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX IF NOT EXISTS object_part ON objects USING btree (part);


--
-- TOC entry 2013 (class 1259 OID 16414)
-- Name: object_tid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX IF NOT EXISTS object_tid ON objects USING btree (tid);


--
-- TOC entry 2014 (class 1259 OID 16419)
-- Name: object_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX IF NOT EXISTS object_type ON objects USING btree (type);


--
-- TOC entry 2017 (class 2606 OID 16393)
-- Name: objects objects_of_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY objects
    ADD CONSTRAINT objects_of_fkey FOREIGN KEY (of) REFERENCES objects(zoid) ON DELETE CASCADE;


--
-- TOC entry 2018 (class 2606 OID 16398)
-- Name: objects objects_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY objects
    ADD CONSTRAINT objects_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES objects(zoid) ON DELETE CASCADE;


-- Completed on 2018-03-16 09:00:53 EDT

--
-- PostgreSQL database dump complete
--
