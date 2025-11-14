--
-- PostgreSQL database dump
--


-- Dumped from database version 18.0 (Debian 18.0-1.pgdg12+3)
-- Dumped by pg_dump version 18.0

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: bot_request_usage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bot_request_usage (
    id bigint NOT NULL,
    tenant_id bigint NOT NULL,
    bucket_date date NOT NULL,
    request_count bigint DEFAULT 0 NOT NULL,
    last_request_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: bot_request_usage_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bot_request_usage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bot_request_usage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bot_request_usage_id_seq OWNED BY public.bot_request_usage.id;


--
-- Name: contact_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contact_link (
    id bigint NOT NULL,
    chatwoot_id bigint,
    crm_id bigint
);


--
-- Name: contact_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contact_link_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contact_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contact_link_id_seq OWNED BY public.contact_link.id;


--
-- Name: crm; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.crm (
    id bigint NOT NULL,
    tenant_id bigint NOT NULL,
    params jsonb,
    modified_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: crm_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.crm_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: crm_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.crm_id_seq OWNED BY public.crm.id;


--
-- Name: data_rag_vectors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_rag_vectors (
    id bigint NOT NULL,
    text character varying NOT NULL,
    metadata_ json,
    node_id character varying,
    embedding public.vector(1536)
);


--
-- Name: data_rag_vectors_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.data_rag_vectors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: data_rag_vectors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.data_rag_vectors_id_seq OWNED BY public.data_rag_vectors.id;


--
-- Name: data_tenant_1_vectors_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.data_tenant_1_vectors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: llm; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm (
    id bigint NOT NULL,
    tenant_id bigint NOT NULL,
    params jsonb,
    modified_at timestamp with time zone DEFAULT now()
);


--
-- Name: llm_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.llm_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: llm_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.llm_id_seq OWNED BY public.llm.id;


--
-- Name: omnichannel; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.omnichannel (
    id bigint NOT NULL,
    tenant_id bigint NOT NULL,
    params jsonb,
    modified_at timestamp with time zone DEFAULT now()
);


--
-- Name: omnichannel_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.omnichannel_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: omnichannel_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.omnichannel_id_seq OWNED BY public.omnichannel.id;


--
-- Name: tenants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants (
    id bigint NOT NULL,
    email text,
    omnichannel_id bigint,
    crm_id bigint,
    modified_at timestamp with time zone DEFAULT now()
);


--
-- Name: tenants_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tenants_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tenants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tenants_id_seq OWNED BY public.tenants.id;


--
-- Name: veriops_users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.veriops_users (
    id bigint NOT NULL,
    tenant_id bigint,
    email text NOT NULL,
    is_admin boolean DEFAULT false,
    password_hash text NOT NULL,
    modified_at timestamp with time zone DEFAULT now()
);


--
-- Name: veriops_users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.veriops_users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: veriops_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.veriops_users_id_seq OWNED BY public.veriops_users.id;


--
-- Name: bot_request_usage id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bot_request_usage ALTER COLUMN id SET DEFAULT nextval('public.bot_request_usage_id_seq'::regclass);


--
-- Name: contact_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_link ALTER COLUMN id SET DEFAULT nextval('public.contact_link_id_seq'::regclass);


--
-- Name: crm id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crm ALTER COLUMN id SET DEFAULT nextval('public.crm_id_seq'::regclass);


--
-- Name: data_rag_vectors id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_rag_vectors ALTER COLUMN id SET DEFAULT nextval('public.data_rag_vectors_id_seq'::regclass);


--
-- Name: llm id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm ALTER COLUMN id SET DEFAULT nextval('public.llm_id_seq'::regclass);


--
-- Name: omnichannel id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.omnichannel ALTER COLUMN id SET DEFAULT nextval('public.omnichannel_id_seq'::regclass);


--
-- Name: tenants id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants ALTER COLUMN id SET DEFAULT nextval('public.tenants_id_seq'::regclass);


--
-- Name: veriops_users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.veriops_users ALTER COLUMN id SET DEFAULT nextval('public.veriops_users_id_seq'::regclass);


--
-- Name: bot_request_usage bot_request_usage_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bot_request_usage
    ADD CONSTRAINT bot_request_usage_pkey PRIMARY KEY (id);


--
-- Name: contact_link contact_link_chatwoot_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_link
    ADD CONSTRAINT contact_link_chatwoot_id_key UNIQUE (chatwoot_id);


--
-- Name: contact_link contact_link_crm_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_link
    ADD CONSTRAINT contact_link_crm_id_key UNIQUE (crm_id);


--
-- Name: contact_link contact_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_link
    ADD CONSTRAINT contact_link_pkey PRIMARY KEY (id);


--
-- Name: crm crm_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crm
    ADD CONSTRAINT crm_pkey PRIMARY KEY (id);


--
-- Name: data_rag_vectors data_rag_vectors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_rag_vectors
    ADD CONSTRAINT data_rag_vectors_pkey PRIMARY KEY (id);


--
-- Name: llm llm_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm
    ADD CONSTRAINT llm_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);


--
-- Name: veriops_users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.veriops_users
    ADD CONSTRAINT veriops_users_email_key UNIQUE (email);


--
-- Name: veriops_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.veriops_users
    ADD CONSTRAINT veriops_users_pkey PRIMARY KEY (id);


--
-- Name: bot_request_usage_tenant_bucket_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX bot_request_usage_tenant_bucket_idx ON public.bot_request_usage USING btree (tenant_id, bucket_date);


--
-- Name: rag_vectors_idx_1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX rag_vectors_idx_1 ON public.data_rag_vectors USING btree (((metadata_ ->> 'ref_doc_id'::text)));


--
-- Name: rag_vectors_idx_tenant_id_text; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX rag_vectors_idx_tenant_id_text ON public.data_rag_vectors USING btree ((((metadata_ ->> 'tenant_id'::text))::character varying));


--
-- Name: veriops_users_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.veriops_users
    ADD CONSTRAINT veriops_users_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

