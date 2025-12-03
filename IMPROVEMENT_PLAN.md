# Agrow AI Helpline - Improvement Plan

## Current Issues & Proposed Solutions

---

## 🎯 **Priority 1: Multi-Language Voice Interface**

### **Problem:**
Farmers hear English greetings/status messages ("Welcome to Agrow...", "We are processing...") but may not understand English at all.

### **Goals:**
- Greet farmers in their native language
- Provide status updates in their language
- Make the entire experience feel local and accessible

### **Approach Options:**

#### **Option A: Phone Number-Based Language Detection** (RECOMMENDED)
**How it works:**
- Extract region from phone number (area code/STD code)
- Map region → primary language
- Use that language for TwiML messages

**Pros:**
- Automatic, no user input needed
- Works before farmer speaks
- Accurate for landlines and regional mobile numbers

**Cons:**
- Mobile numbers aren't always region-specific (people move)
- Requires maintaining area code → language mapping
- Won't work for WhatsApp/VoIP calls

**Implementation:**
```python
# India STD code → Language mapping
STD_TO_LANGUAGE = {
    "22": "mr",    # Mumbai → Marathi
    "11": "hi",    # Delhi → Hindi  
    "44": "ta",    # Chennai → Tamil
    "80": "kn",    # Bangalore → Kannada
    "40": "te",    # Hyderabad → Telugu
    "33": "ta",    # Coimbatore → Tamil
    # ... etc
}

def detect_language_from_number(phone_number):
    # Extract STD code from +91XXXXXXXXXX
    std_code = phone_number[3:5]  # or [3:6] for 3-digit codes
    return STD_TO_LANGUAGE.get(std_code, "hi")  # Default to Hindi
```

#### **Option B: First-Call Language Selection** (Interactive)
**How it works:**
1. Play: "Press 1 for Hindi, 2 for Tamil, 3 for Telugu..."
2. Farmer selects language
3. Store preference with CallSid or phone number

**Pros:**
- Very accurate (farmer chooses)
- Works regardless of phone number origin
- Can handle multilingual farmers

**Cons:**
- Adds friction (extra step)
- Requires farmers to understand number system
- Still needs initial prompt in some language

#### **Option C: Hybrid Approach** (BEST)
1. **Detect from phone number** → greet in detected language
2. **Then ask:** "Press 1 to continue in Hindi, press 2 for Tamil..." (in detected language)
3. **Default to Hindi** if detection fails

**Pros:**
- Best of both worlds
- Gives farmers control
- Graceful fallback

### **Recommended Solution:**

**Start with Option A** (phone-based detection with Hindi fallback) because:
- Simplest to implement
- Zero friction for farmers
- Can always add Option C later as enhancement

**Language Priority:**
1. Hindi (most widely understood)
2. Tamil, Telugu, Kannada, Marathi, Punjabi, Bengali (major farming states)
3. Others as needed

**Implementation Steps:**
1. Create STD code → language mapping database
2. Add language detection function in `server.py`
3. Create multi-language prompts:
   - Welcome message
   - "Please ask your question after the beep"
   - "Processing your question..."
   - "Still processing, please hold..."
   - "Thank you for using Agrow"
4. Use Twilio's `<Say>` with `language` parameter OR pre-recorded audio

**TwiML Language Support:**
```xml
<!-- Hindi -->
<Say voice="Polly.Aditi" language="hi-IN">
    आग्रो में आपका स्वागत है। कृपया बीप के बाद अपना सवाल पूछें।
</Say>

<!-- Tamil -->
<Say voice="Polly.Aditi" language="ta-IN">
    அக்ரோவுக்கு வரவேற்கிறோம். பீப் ஒலிக்குப் பிறகு உங்கள் கேள்வியைக் கேளுங்கள்.
</Say>
```

---

## 🔧 **Priority 2: Fix Language Detection & Translation Pipeline**

### **Problem:**
- Tamil audio detected as Russian
- Auto-detection skipping translation steps
- Not using Sarvam translation properly

### **Root Causes:**

#### **Issue 1: ElevenLabs STT Language Detection**
ElevenLabs' auto-detect might not be trained well on Indian languages, especially less common ones like Tamil.

**Solutions:**
1. **Force language parameter** instead of "auto"
2. **Use Sarvam STT** instead (built for Indian languages)
3. **Two-stage detection:**
   - Use ElevenLabs for quick detection
   - If confidence < 80%, retry with forced language hint

#### **Issue 2: Translation Being Skipped**
Looking at your pipeline code, when `source_lang="auto"`, it skips translation:
```python
if effective_source not in ("en", "auto"):
    # Translate to English
```

**The Fix:**
Pipeline should:
1. Always detect actual language (don't pass "auto" to LLM step)
2. Translate if source != English
3. Use Sarvam for ALL Indic language pairs

### **Recommended Pipeline Flow:**

```
CURRENT (BROKEN):
Audio → STT (lang=auto) → "auto" → Skip Translation → LLM → Skip Back-translate → TTS

IMPROVED:
Audio → STT (lang=auto) → Detect actual lang → 
  If Hindi/Tamil/etc: Translate to English → LLM → Back-translate → TTS
  If English: Direct to LLM → TTS
```

### **Specific Fixes Needed:**

#### **Fix 1: Better Language Detection**
```python
# In pipeline.py
def detect_language(self, audio_path: str) -> str:
    """
    Detect language from audio with confidence checking
    """
    stt_result = self.speech.speech_to_text(audio_path, source_lang="auto")
    
    # Check if detected language is Indian language
    indian_languages = ["hi", "ta", "te", "kn", "mr", "pa", "bn", "gu", "ml", "or"]
    
    if stt_result.language in indian_languages:
        return stt_result.language
    elif stt_result.language == "en":
        return "en"
    else:
        # Suspicious detection (like Russian for Tamil)
        # Default to Hindi or let user specify
        logger.warning(f"Unexpected language detected: {stt_result.language}")
        return "hi"  # Safe fallback
```

#### **Fix 2: Always Use Translation**
```python
# Remove the "auto" exception
effective_source = detected_language  # Never "auto"

if effective_source != "en":
    # Always translate non-English to English for LLM
    translated_query = self.sarvam.translate(
        stt.text, 
        source_lang=f"{effective_source}-IN",
        target_lang="en-IN"
    )
    query_for_llm = translated_query.translated_text
```

#### **Fix 3: Improve Sarvam API Usage**
Check Sarvam's language codes - they might need specific format:
- "ta-IN" vs "ta"
- "hi-IN" vs "hin"

Verify with Sarvam API docs.

### **Testing Plan:**
1. Record test audio in Hindi, Tamil, Telugu, Kannada
2. Test STT detection accuracy
3. Verify translation quality
4. Compare before/after results

---

## ⚡ **Priority 3: Reduce Response Time**

### **Current Timing Breakdown:**
Based on logs:
- **STT (ElevenLabs):** ~1-2 seconds ✅
- **Translation (Sarvam):** ~1 second ✅  
- **LLM (Groq):** ~1 second ✅
- **Back-translation (Sarvam):** ~1 second ✅
- **TTS (ElevenLabs):** ~15-18 seconds ⚠️ **BOTTLENECK!**

**Total: ~20-24 seconds**

### **The Real Issue: Text-to-Speech**

TTS takes 75% of total processing time! This is because:
- Generating natural-sounding speech is compute-intensive
- ElevenLabs might be processing sequentially
- Audio file size affects generation time

### **Optimization Approaches:**

#### **Option 1: Streaming TTS** (BEST for latency)
Instead of generating entire audio file, stream it as it's created.

**How:**
- Use ElevenLabs streaming API
- Play audio to caller while it's still being generated
- Reduces perceived latency from 18s → 3-5s

**Pros:**
- Massive UX improvement
- Farmer hears response almost immediately
- Professional feel

**Cons:**
- Complex implementation (WebSocket/streaming)
- Harder to debug
- Requires Twilio WebSocket support

#### **Option 2: Faster TTS Service** 
Switch from ElevenLabs to:
- **Google Cloud TTS:** ~2-3 seconds, supports Indian languages
- **Azure TTS:** ~2-3 seconds, good quality
- **Play.ht:** ~3-5 seconds, cheaper

**Pros:**
- Easy drop-in replacement
- 5-6x faster
- Often cheaper

**Cons:**
- Quality might be lower than ElevenLabs
- Need to test voice quality

#### **Option 3: Pre-generate Common Responses**
For FAQ-type questions:
- Cache responses for common queries
- "How to prepare soil?" → pre-generated audio
- Check question similarity, serve cached audio

**Pros:**
- Instant responses for common questions
- Reduced API costs

**Cons:**
- Only works for repetitive queries
- Cache management complexity
- Less personalized

#### **Option 4: Parallel Processing**
Currently sequential: STT → Translate → LLM → Back-translate → TTS

**Optimize:**
```python
# Start TTS immediately with partial response
# As LLM generates tokens, feed to TTS
# Stream final audio
```

**Pros:**
- Reduces total time
- Better resource utilization

**Cons:**
- Very complex
- Harder error handling

### **Recommended Approach:**

**Phase 1 (Quick Win):**
- Test **Google Cloud TTS** or **Azure TTS** as ElevenLabs replacement
- Should reduce time from 24s → 8-10s
- Easy to implement, minimal risk

**Phase 2 (Medium-term):**  
- Implement **streaming TTS** for real-time feel
- Requires significant refactoring but worth it

**Phase 3 (Optimization):**
- Add **response caching** for FAQs
- Use **CDN** for audio file delivery
- Optimize LLM prompts for shorter responses

---

## 📋 **Implementation Roadmap**

### **Week 1: Multi-Language Voice Interface**
- [ ] Create STD code → language mapping
- [ ] Implement language detection from phone number  
- [ ] Create Hindi prompts for all TwiML messages
- [ ] Test with Hindi-speaking regions
- [ ] Add Tamil, Telugu, Kannada prompts
- **Estimated effort:** 2-3 days
- **Impact:** High (better UX for farmers)

### **Week 2: Fix Language Detection & Pipeline**
- [ ] Review ElevenLabs STT language detection accuracy
- [ ] Fix pipeline to always use proper language (not "auto")
- [ ] Ensure Sarvam translation works for all Indian languages
- [ ] Create test suite with multi-language audio samples
- [ ] Fix Tamil → Russian misdetection issue
- **Estimated effort:** 3-4 days  
- **Impact:** High (accuracy improvement)

### **Week 3: Performance Optimization**
- [ ] Benchmark current TTS performance
- [ ] Test Google Cloud TTS / Azure TTS alternatives
- [ ] Compare voice quality vs speed tradeoff
- [ ] Implement faster TTS service
- [ ] (Optional) Start streaming TTS prototype
- **Estimated effort:** 4-5 days
- **Impact:** Medium-High (better UX, lower costs)

---

## 🔍 **Technical Deep Dives**

### **Challenge 1: Twilio TTS Language Support**

Twilio's `<Say>` supports these Indian languages:
- Hindi (`hi-IN`) - Polly.Aditi (female)
- Tamil (`ta-IN`) - Polly.Aditi
- Bengali (`bn-IN`) - Polly.Aditi
- Marathi - Limited
- Telugu, Kannada - Check support

**Alternative:** Pre-record messages using ElevenLabs/Google TTS, serve as audio files.

### **Challenge 2: Sarvam Translation Quality**

Sarvam is great for:
- Hindi ↔ English
- Major Indic languages ↔ English

Test quality for:
- Tamil, Telugu (should be good)
- Kannada, Marathi, Bengali (verify)
- Punjabi, Gujarati (check support)

### **Challenge 3: STD Code Mapping**

India has **100s of STD codes**. Priority approach:
1. Map major agricultural regions first:
   - Punjab, Haryana (Wheat belt)
   - Tamil Nadu, Karnataka (South)
   - Maharashtra, Gujarat (West)
   - UP, Bihar (North/East)
2. Default to Hindi for unmapped codes
3. Expand mapping based on call data

---

## 💰 **Cost Impact Analysis**

### **Current Cost: ~$0.17/call**

| Change | Cost Impact |
|--------|-------------|
| Switch to Google TTS | **-30%** (~$0.12/call) |
| Add Hindi prompts (TTS) | +$0.01/call |
| Use Sarvam STT instead of ElevenLabs | **-50%** on STT (~$0.16/call) |
| Cache common responses | **-20%** on cached queries |

**Potential optimized cost:** ~$0.10-0.12/call (40% reduction!)

---

## 🎯 **Success Metrics**

### **Before:**
- Response time: 24 seconds
- Language accuracy: ~70% (fails on Tamil, etc.)
- Farmer understands prompts: 50% (English only)

### **After (Target):**
- Response time: <12 seconds
- Language accuracy: >95%
- Farmer understands prompts: >95% (native language)

---

## 🚀 **Quick Wins to Start Today**

1. **Hindi Prompts** - Replace English prompts with Hindi (30 min work, huge impact)
2. **Fix "auto" Language** - Remove auto-detection in pipeline, always detect actual language (1 hour)
3. **Test Google TTS** - Quick benchmark to see speed improvement (2 hours)

These three changes alone would dramatically improve the farmer experience!

---

## 📝 **Questions to Research**

1. What are ElevenLabs' actual Indian language STT accuracy rates?
2. Does Sarvam have its own STT API we should use instead?
3. Which Indian language TTS service has best quality/speed tradeoff?
4. Can we use Twilio's built-in multilingual TTS or need custom audio?
5. What's the farmer distribution by language in our target regions?

---

## 🎬 **Next Steps**

1. **Review this plan** - Add/modify based on your priorities
2. **Choose starting point** - Which improvement to tackle first?
3. **Set up test data** - Record multi-language audio samples
4. **Start with Priority 1** - Multi-language prompts (biggest UX win)
5. **Iterate based on feedback** - Test with actual farmers if possible!

Let me know which area you want to start with, and I'll help you implement it! 🚀
