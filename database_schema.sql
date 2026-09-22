--
-- PostgreSQL database dump
--

\restrict 0u51JP2w06FVoCCnyP8np7etFWtaeJHCjWP05ZAkRy4K52BPm6CPx3T1EGL8Ush

-- Dumped from database version 15.14
-- Dumped by pg_dump version 15.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: update_conversation_timestamp(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_conversation_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE conversations 
    SET updated_at = NOW() 
    WHERE chat_id = NEW.chat_id;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_conversation_timestamp() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: conversations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.conversations (
    chat_id uuid NOT NULL,
    sender_linkedin_id character varying(255) NOT NULL,
    recipient_linkedin_id character varying(255) NOT NULL,
    unipile_account_id character varying(255) NOT NULL,
    calendar_account_id character varying(255),
    calendar_id character varying(255),
    job_id character varying(255) NOT NULL,
    stage character varying(50) DEFAULT 'initial_outreach'::character varying NOT NULL,
    ai_enabled boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.conversations OWNER TO postgres;

--
-- Name: messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.messages (
    message_id uuid NOT NULL,
    chat_id uuid NOT NULL,
    sender_linkedin_id character varying(255) NOT NULL,
    recipient_linkedin_id character varying(255) NOT NULL,
    unipile_account_id character varying(255) NOT NULL,
    job_id character varying(255) NOT NULL,
    message text NOT NULL,
    direction character varying(20) NOT NULL,
    message_type character varying(20) DEFAULT 'message'::character varying NOT NULL,
    is_initial_reachout boolean DEFAULT false NOT NULL,
    status character varying(20),
    scheduled_at timestamp without time zone,
    retry_count integer DEFAULT 0,
    error_message text,
    conversation_stage character varying(50),
    has_attachment boolean DEFAULT false,
    attachment_info text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    sent_at timestamp without time zone,
    CONSTRAINT messages_direction_check CHECK (((direction)::text = ANY ((ARRAY['outbound'::character varying, 'inbound'::character varying])::text[]))),
    CONSTRAINT messages_message_type_check CHECK (((message_type)::text = ANY ((ARRAY['message'::character varying, 'invite'::character varying])::text[]))),
    CONSTRAINT messages_status_check CHECK (((status)::text = ANY ((ARRAY['scheduled'::character varying, 'sending'::character varying, 'sent'::character varying, 'cancelled'::character varying, 'error'::character varying, 'history'::character varying])::text[])))
);


ALTER TABLE public.messages OWNER TO postgres;

--
-- Name: job_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.job_settings (
    job_id character varying(255) NOT NULL,
    ai_enabled boolean DEFAULT true NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.job_settings OWNER TO postgres;

--
-- Name: active_queue; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.active_queue AS
 SELECT m.message_id,
    m.chat_id,
    m.sender_linkedin_id,
    m.recipient_linkedin_id,
    m.unipile_account_id,
    m.job_id,
    m.message,
    m.direction,
    m.message_type,
    m.is_initial_reachout,
    m.status,
    m.scheduled_at,
    m.retry_count,
    m.error_message,
    m.conversation_stage,
    m.has_attachment,
    m.attachment_info,
    m.created_at,
    m.sent_at,
    c.stage AS current_conversation_stage
   FROM (public.messages m
     JOIN public.conversations c ON ((m.chat_id = c.chat_id)))
  WHERE ((m.status)::text = ANY ((ARRAY['scheduled'::character varying, 'sending'::character varying])::text[]))
  ORDER BY m.scheduled_at;


ALTER TABLE public.active_queue OWNER TO postgres;

--
-- Name: conversation_messages; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.conversation_messages AS
 SELECT m.message_id,
    m.chat_id,
    m.sender_linkedin_id,
    m.recipient_linkedin_id,
    m.unipile_account_id,
    m.job_id,
    m.message,
    m.direction,
    m.message_type,
    m.is_initial_reachout,
    m.status,
    m.scheduled_at,
    m.retry_count,
    m.error_message,
    m.conversation_stage,
    m.has_attachment,
    m.attachment_info,
    m.created_at,
    m.sent_at,
    c.stage AS current_conversation_stage
   FROM (public.messages m
     JOIN public.conversations c ON ((m.chat_id = c.chat_id)))
  ORDER BY m.created_at;


ALTER TABLE public.conversation_messages OWNER TO postgres;

--
-- Name: conversation_summary; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.conversation_summary AS
SELECT
    NULL::uuid AS chat_id,
    NULL::character varying(255) AS sender_linkedin_id,
    NULL::character varying(255) AS recipient_linkedin_id,
    NULL::character varying(255) AS unipile_account_id,
    NULL::character varying(255) AS job_id,
    NULL::character varying(50) AS stage,
    NULL::timestamp without time zone AS created_at,
    NULL::timestamp without time zone AS updated_at,
    NULL::bigint AS message_count,
    NULL::timestamp without time zone AS last_message_at,
    NULL::text AS last_message_preview;


ALTER TABLE public.conversation_summary OWNER TO postgres;

--
-- Data for Name: conversations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.conversations (chat_id, sender_linkedin_id, recipient_linkedin_id, unipile_account_id, job_id, stage, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: messages; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.messages (message_id, chat_id, sender_linkedin_id, recipient_linkedin_id, unipile_account_id, job_id, message, direction, message_type, is_initial_reachout, status, scheduled_at, retry_count, error_message, conversation_stage, has_attachment, attachment_info, created_at, sent_at) FROM stdin;
\.


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (chat_id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (message_id);


--
-- Name: job_settings job_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.job_settings
    ADD CONSTRAINT job_settings_pkey PRIMARY KEY (job_id);


--
-- Name: conversations unique_conversation; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT unique_conversation UNIQUE (sender_linkedin_id, recipient_linkedin_id);


--
-- Name: idx_conversations_account; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_conversations_account ON public.conversations USING btree (unipile_account_id);


--
-- Name: idx_conversations_job; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_conversations_job ON public.conversations USING btree (job_id);


--
-- Name: idx_conversations_sender_recipient; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_conversations_sender_recipient ON public.conversations USING btree (sender_linkedin_id, recipient_linkedin_id);


--
-- Name: idx_messages_account; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_messages_account ON public.messages USING btree (unipile_account_id);


--
-- Name: idx_messages_chat; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_messages_chat ON public.messages USING btree (chat_id);


--
-- Name: idx_messages_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_messages_created ON public.messages USING btree (created_at);


--
-- Name: idx_messages_direction; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_messages_direction ON public.messages USING btree (direction);


--
-- Name: idx_messages_job; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_messages_job ON public.messages USING btree (job_id);


--
-- Name: idx_messages_recipient; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_messages_recipient ON public.messages USING btree (recipient_linkedin_id);


--
-- Name: idx_messages_scheduled; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_messages_scheduled ON public.messages USING btree (scheduled_at) WHERE (scheduled_at IS NOT NULL);


--
-- Name: idx_messages_sender; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_messages_sender ON public.messages USING btree (sender_linkedin_id);


--
-- Name: idx_messages_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_messages_status ON public.messages USING btree (status) WHERE (status IS NOT NULL);


--
-- Name: conversation_summary _RETURN; Type: RULE; Schema: public; Owner: postgres
--

CREATE OR REPLACE VIEW public.conversation_summary AS
 SELECT c.chat_id,
    c.sender_linkedin_id,
    c.recipient_linkedin_id,
    c.unipile_account_id,
    c.job_id,
    c.stage,
    c.created_at,
    c.updated_at,
    count(m.message_id) AS message_count,
    max(m.created_at) AS last_message_at,
    ( SELECT m2.message
           FROM public.messages m2
          WHERE (m2.chat_id = c.chat_id)
          ORDER BY m2.created_at DESC
         LIMIT 1) AS last_message_preview
   FROM (public.conversations c
     LEFT JOIN public.messages m ON ((c.chat_id = m.chat_id)))
  GROUP BY c.chat_id
  ORDER BY (max(m.created_at)) DESC NULLS LAST;


--
-- Name: messages trigger_update_conversation_timestamp; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_update_conversation_timestamp AFTER INSERT ON public.messages FOR EACH ROW EXECUTE FUNCTION public.update_conversation_timestamp();


--
-- Name: messages messages_chat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_chat_id_fkey FOREIGN KEY (chat_id) REFERENCES public.conversations(chat_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 0u51JP2w06FVoCCnyP8np7etFWtaeJHCjWP05ZAkRy4K52BPm6CPx3T1EGL8Ush

