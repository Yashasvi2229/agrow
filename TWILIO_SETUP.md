# Agrow Twilio Setup Guide

This guide will help you set up Twilio for phone call integration with the Agrow AI agricultural helpline.

## Prerequisites
- Python 3.8+ installed
- All AI pipeline dependencies working (ElevenLabs, Sarvam, Groq)

## Step 1: Create Twilio Trial Account

1. Go to [https://www.twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. Sign up with your email (no credit card required)
3. Verify your email and phone number
4. You'll receive **$15.50 in free trial credits**

## Step 2: Get Your Twilio Credentials

1. After logging in, go to the [Twilio Console](https://console.twilio.com/)
2. On the dashboard, you'll see:
   - **Account SID** (starts with `AC...`)
   - **Auth Token** (click to reveal)
3. Copy these values - you'll need them for the `.env` file

## Step 3: Get a Phone Number

1. In the Twilio Console, go to **Phone Numbers** → **Manage** → **Buy a number**
2. Select **India** as the country
3. Look for a number with **Voice** capability
4. Click **Buy** (this uses your trial credits, still free!)
5. Note: Trial accounts can only get certain numbers for free

## Step 4: Verify Your Demo Phone Numbers

**IMPORTANT**: Twilio trial accounts can only receive calls from verified numbers!

1. Go to **Phone Numbers** → **Verified Caller IDs**
2. Click **Add a new Caller ID**
3. Enter the phone number you'll use for testing/demo (your phone)
4. Twilio will call you with a verification code
5. Enter the code to verify
6. Repeat for 2-3 demo numbers (judges, team members, etc.)

## Step 5: Install Dependencies

```bash
cd /Users/dakshjaitly/Desktop/Projects/Agrow/agrow
pip install -r ai-helpline-pipeline/requirements.txt
```

## Step 6: Configure Environment Variables

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```
   TWILIO_ACCOUNT_SID=AC... (your Account SID)
   TWILIO_AUTH_TOKEN=... (your Auth Token)
   TWILIO_PHONE_NUMBER=+91... (your Twilio number)
   
   ELEVENLABS_API_KEY=... (from ai-helpline-pipeline/.env)
   SARVAM_API_KEY=...
   GROQ_API_KEY=...
   ```

3. Or keep using the existing `.env` in `ai-helpline-pipeline/` - the server will load from there too

## Step 7: Set Up Ngrok (for local development)

Since Twilio needs to reach your local server, you need a public URL:

1. Install ngrok:
   ```bash
   brew install ngrok
   # or download from https://ngrok.com/download
   ```

2. Start ngrok tunnel:
   ```bash
   ngrok http 5000
   ```

3. Copy the **Forwarding URL** (looks like `https://xxxx-xx-xx-xx.ngrok-free.app`)

## Step 8: Configure Twilio Webhooks

1. Go to **Phone Numbers** → **Manage** → **Active numbers**
2. Click on your Twilio phone number
3. Scroll to **Voice Configuration**
4. Under **A CALL COMES IN**, set:
   - **Webhook**: `https://your-ngrok-url.ngrok-free.app/voice/incoming`
   - **HTTP Method**: `POST`
5. Click **Save**

## Step 9: Start the Server

```bash
cd /Users/dakshjaitly/Desktop/Projects/Agrow/agrow
python server.py
```

You should see:
```
Starting Agrow Twilio Server...
Pipeline initialized successfully
Twilio Phone Number: +91...
Running on http://0.0.0.0:5000
```

## Step 10: Test the Integration

1. From a **verified phone number**, call your Twilio number
2. You should hear: "Welcome to Agrow..."
3. After the beep, ask a farming question in any Indian language
4. Wait for processing (~10-20 seconds)
5. You'll hear the AI response in your language!

## Troubleshooting

### "This number is not verified"
- Make sure you're calling from a verified Caller ID
- Go to Twilio Console → Verified Caller IDs and verify your number

### "Webhook Error"
- Check that ngrok is running and the URL is correct in Twilio
- Check server logs for errors
- Verify your `.env` file has all required API keys

### "Pipeline not initialized"
- Check that all AI API keys are set correctly
- Look at server logs for specific errors
- Test the pipeline independently with: `python ai-helpline-pipeline/main.py Sample1.wav`

### "Recording not received"
- Check server logs for the recording URL
- Verify Twilio webhook is pointing to `/voice/recording`
- Make sure ngrok tunnel is still active

## Demo Presentation Tips

1. **Test beforehand**: Do 2-3 test calls the day before
2. **Have backup**: Keep Sample audio files ready in case live demo fails
3. **Explain latency**: Tell judges "The AI is processing..." during the ~15s wait
4. **Verified numbers**: Make sure the demo caller's number is verified!
5. **Ngrok stability**: Start ngrok fresh before the presentation

## Cost Tracking

- Trial credit: $15.50
- Each call costs ~$0.01-0.02 per minute
- You can do ~20-30 demo calls with trial credits

## Next Steps

Once the demo is successful and you get funding:
- Upgrade to paid Twilio account (removes "trial" message and verification requirements)
- Get toll-free number or multiple regional numbers
- Implement real-time streaming for lower latency
- Add call analytics and monitoring
