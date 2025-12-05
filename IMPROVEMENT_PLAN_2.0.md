# AgroWise: Improvement Plan 2.0

## 1. Executive Summary

**Goal:** Transform the current MVP from a single-turn, high-latency system into a fast, intelligent, and continuous conversational advisory agent.

**Core Constraint:** The system will utilize robust **REST APIs** and standard webhooks (avoiding complex WebSockets) to ensure stability and ease of debugging for the hackathon presentation.

**Key Upgrades:**
- **Speed:** Drastically reduce response latency from ~25s to <8s by switching to faster service providers.
- **Intelligence:** Integrate Supabase (RAG) to ground answers in verified agricultural data.
- **Experience:** Enable continuous conversation loops, auto-send WhatsApp summaries, and visualize system performance on a live Admin Dashboard.

---

## 2. Architecture Overview

The system moves from a linear, slow pipeline to an optimized, modular REST architecture.

**Components:**
- **Telephony:** Twilio Voice (Webhooks)
- **Speech-to-Text (STT):** Deepgram Nova-2 (Pre-recorded API) – Replaces ElevenLabs for speed & accent support
- **Intelligence (LLM):** Groq (Llama 3 70B) – High-speed inference
- **Text-to-Speech (TTS):** Google Cloud TTS or Azure AI Speech – Replaces ElevenLabs for ultra-low latency
- **Knowledge Base (RAG):** Supabase (Postgres + pgvector) – New feature for domain expertise
- **Messaging:** Twilio WhatsApp Sandbox – New feature for post-call summaries
- **Monitoring:** Flask Admin Dashboard (AJAX Polling) – New feature for live demos

---

## 3. Priority 1: Fix Latency & Response Time (<8 seconds)

**Current Status:** Response takes ~25-35 seconds, primarily due to ElevenLabs TTS generation time.

**Solution:** Replace the slowest components and optimize the pipeline.

### Action A: Switch to Deepgram Nova-2 for STT

**Why:** Deepgram's pre-recorded API processes audio up to 40x faster than real-time. It has superior support for Indian accents and "Hinglish" compared to standard models.

**Implementation:**
1. Twilio `<Record>` finishes → Flask receives URL
2. Flask downloads audio to memory
3. Send audio to Deepgram API (model='nova-2', language='hi' or multi)
4. Receive transcript immediately

### Action B: Switch to Google Cloud TTS or Azure TTS

**Why:** ElevenLabs takes ~15s to generate long audio. Google/Azure generate high-quality "Wavenet" or "Neural" audio in **2-3 seconds**.

**Implementation:**
1. Send LLM text response to Google TTS API (en-IN-Wavenet or hi-IN-Wavenet voices)
2. Receive audio content, save to a static file (e.g., response_123.wav)
3. Return TwiML `<Play>` with the URL of the generated file

### Action C: Prompt Engineering for Speed

**Why:** Long text answers increase both LLM generation time and TTS processing time.

**Implementation:** Update the System Prompt to enforce brevity.

**Prompt:**
```
"You are an expert agricultural advisor. Answer in 1-2 short, conversational 
sentences maximum. Be direct. Do not use bullet points."
```

---

## 4. Priority 2: "Continuous" Conversation Flow

**Current Status:** The user asks one question, gets one answer, and the call hangs up.

**Solution:** Use Twilio's Gather loop to keep the line open.

### Implementation Logic:

1. **Greeting:** System plays welcome message
2. **Loop Start (The Input State):**
   - TwiML executes `<Record action="/voice/process" ... />` to capture user input
3. **Processing Endpoint (/voice/process):**
   - Server processes the audio (STT → RAG → LLM → TTS)
   - Server returns a TwiML response that chains the Answer with a New Record command
4. **The Loop TwiML:**

```xml
<Response>
    <Play>http://your-server.com/audio/response.wav</Play>
    <Say>Do you have another question?</Say>
    <Record action="/voice/process" timeout="5" />
</Response>
```

**Result:** The call never cuts. It answers and immediately listens for the next question.

---

## 5. Priority 3: Knowledge Base (RAG with Supabase)

**Current Status:** AI relies on general training data, which may be outdated or generic.

**Solution:** Retrieve relevant, verified agricultural data before answering.

### Setup:
- **Database:** Supabase project with pgvector extension enabled
- **Table Structure:** `documents` table with columns:
  - `id`
  - `content` (text chunk)
  - `embedding` (vector)

### Step A: Ingestion (Pre-Hackathon)

1. Write a script to read PDF documents (Soil Health Cards, KVK manuals, Government Schemes)
2. Split text into chunks
3. Generate embeddings using a fast model (e.g., OpenAI text-embedding-3-small or HuggingFace)
4. Insert chunks and embeddings into Supabase

### Step B: Retrieval (During Call)

Inside the Flask app (after STT):

1. Generate an embedding for the user's transcribed question
2. Query Supabase for the top 3 most similar document chunks
3. Append this context to the LLM System Prompt:

```
"Context: {retrieved_chunk_1} ... Use this information to answer the user's question."
```

---

## 6. Priority 4: Post-Call Summary (WhatsApp)

**Current Status:** Farmers rely on memory for complex advice (medicine names, dosage).

**Solution:** Send a text summary immediately after the call.

### Implementation:

1. **Accumulate History:** Store the conversation Q&A pairs in a global variable or database session keyed by CallSid
2. **Trigger:** Use Twilio's statusCallback on the final `<Hangup>` or detect a timeout in the Record loop
3. **Summarize & Send:**
   - Send the conversation history to the LLM with the prompt:
     ```
     "Summarize this advisory conversation into 3 clear bullet points in Hindi/English."
     ```
   - Use the Twilio WhatsApp Sandbox API to send this text to the caller

**Code:**
```python
client.messages.create(
    body=summary,
    from_='whatsapp:+14155238886',
    to='whatsapp:+91...'
)
```

---

## 7. Priority 5: Web Interface (Admin Dashboard)

**Current Status:** No visibility into what the system is doing during the call.

**Solution:** A real-time dashboard using robust AJAX Polling.

### Backend (Flask):

1. Create a global dictionary `call_state = {}`
2. Update this state at every step of the pipeline:
   ```python
   call_state['status'] = "Transcribing Audio..."
   call_state['user_text'] = "Farmer: Is my soil acidic?"
   call_state['rag_doc'] = "Retrieved: Soil_Health_Report.pdf"
   ```
3. Create a standardized endpoint `/api/status` that returns this JSON

### Frontend (HTML/JS):

1. A clean, professional HTML page titled "AgroWise Live Monitor"
2. Use a simple JavaScript `setInterval` loop to fetch `/api/status` every 1 second
3. Dynamically update HTML elements (`<div>`) with the current status, user query, and AI response

---

## Summary

This improvement plan transforms AgroWise from a basic MVP to a production-ready, intelligent advisory system that provides:

- **Sub-8 second responses** through optimized service providers
- **Continuous multi-turn conversations** for natural farmer interactions
- **Verified, grounded answers** through RAG knowledge base
- **Post-call reference** via WhatsApp summaries
- **Live monitoring** for demos and debugging

All while maintaining REST-based architecture for stability and ease of implementation.
