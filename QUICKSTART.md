# Agrow Quick Start - Twilio Integration

## 🚀 Quick Commands

### First Time Setup
```bash
# 1. Install dependencies
pip install -r ai-helpline-pipeline/requirements.txt

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env with your API keys (Twilio + AI services)
nano .env
```

### Running the Server

**Terminal 1** - Start ngrok:
```bash
ngrok http 5000
```
Copy the ngrok URL (e.g., `https://abc123.ngrok-free.app`)

**Terminal 2** - Start Flask server:
```bash
python server.py
```

### Configure Twilio Webhook
1. Go to [Twilio Console](https://console.twilio.com/) → Phone Numbers
2. Click your number → Voice Configuration
3. Set webhook to: `https://your-ngrok-url.ngrok-free.app/voice/incoming`
4. Save!

### Test the Call
Call your Twilio number from a verified phone number!

---

## 📋 What You Need

1. **Twilio Account** (free trial: https://www.twilio.com/try-twilio)
   - Account SID
   - Auth Token  
   - Phone number

2. **AI Service API Keys** (you already have these):
   - ElevenLabs API key
   - Sarvam API key
   - Groq API key

3. **Verified Phone Number** (in Twilio Console, for testing)

---

## 🎯 How It Works

```
Farmer calls → Twilio → Your Flask Server → AI Pipeline → Response → Farmer hears answer
```

**Flow:**
1. Call comes in → Greeting plays → Records question
2. Server downloads recording → Processes through AI pipeline
3. Response generated → Plays back to caller

**Processing time**: ~10-20 seconds per call

---

## 💡 Pro Tips

- **Keep ngrok running** - If it stops, update Twilio webhook URL
- **Check logs** - Server prints detailed logs for debugging
- **Test with Sample files** - Before live calls, test pipeline: `python ai-helpline-pipeline/main.py Sample1.wav`
- **Verify numbers first** - Trial accounts only work with verified Caller IDs

---

## 🐛 Troubleshooting

**Server won't start?**
- Check `.env` has all required keys
- Install dependencies: `pip install flask twilio`

**Call doesn't connect?**
- Verify ngrok is running
- Check Twilio webhook URL is correct
- Ensure calling from verified number

**No audio response?**
- Check server logs for errors
- Test pipeline separately first
- Verify AI API keys are correct

---

For detailed setup instructions, see [TWILIO_SETUP.md](./TWILIO_SETUP.md)
