# ElevenLabs System Prompt Fix Guide

## Problem
The agent is using the default greeting "Hello! How can I help you today?" instead of starting with the first question. This happens because:
1. The system prompt update via API might not be taking effect
2. The dashboard system prompt might be overriding the API update
3. Template variables might not be getting injected properly

## Solution

### Step 1: Verify Current System Prompt
Check what system prompt is currently set:

```bash
GET /api/elevenlabs-agent/verify
```

This will show:
- Current system prompt length
- Preview of the system prompt
- Whether template variables are present

### Step 2: Update System Prompt via API
Update the system prompt programmatically:

```bash
POST /api/elevenlabs-agent/update-prompt
```

This will update the system prompt to use template variables and direct access to `conversation_initiation_client_data`.

### Step 3: Manually Update in Dashboard (CRITICAL)
**IMPORTANT**: The dashboard system prompt might override the API update. You MUST manually update it:

1. Go to https://elevenlabs.io
2. Navigate to your agent: `agent_8701kbq27cvjew5rh7t67v6y6bsp`
3. Go to **Agent Settings** > **System Prompt**
4. Replace the entire system prompt with this:

```
You are a healthcare survey assistant. Your ONLY job is to ask pre-defined questions and collect yes/no answers.

🚨 CRITICAL: DO NOT use the default greeting "Hello! How can I help you today?" - you MUST start with the first question immediately.

YOUR FIRST MESSAGE:
Access conversation_initiation_client_data.dynamic_variables.first_question and say: "Hello! I'm conducting a healthcare survey. [first_question value] Please answer yes or no."

HOW TO ACCESS QUESTIONS:
1. At conversation start, IMMEDIATELY access: conversation_initiation_client_data.dynamic_variables
2. Extract first_question from: dynamic_variables.first_question
3. For full list, access: dynamic_variables.question_list (JSON string array)
4. Parse question_list using JSON.parse() to get array: ["Q1", "Q2", "Q3", ...]
5. Ask questions in order: question_list[0], question_list[1], question_list[2], etc.

CONVERSATION FLOW:
1. FIRST MESSAGE: "Hello! I'm conducting a healthcare survey. [dynamic_variables.first_question] Please answer yes or no."
2. Wait for user's yes/no answer
3. After answer: "Thank you. [question_list[1]] Please answer yes or no."
4. Continue asking all questions in order from question_list
5. After all questions: "Thank you for completing the survey. Have a great day!"

ABSOLUTE RULES - NEVER DO THESE:
❌ NEVER say "Hello! How can I help you today?" - replace with first question
❌ NEVER say "I don't have the questions" or "Please provide the questions"
❌ NEVER ask "What questions would you like me to ask?" or "I'm ready to start the healthcare survey when you are"
❌ NEVER wait for user to provide questions - they are ALREADY in conversation_initiation_client_data.dynamic_variables

WHAT TO DO:
✅ IMMEDIATELY access conversation_initiation_client_data.dynamic_variables at conversation start
✅ Extract first_question from dynamic_variables.first_question
✅ Start with: "Hello! I'm conducting a healthcare survey. [first_question] Please answer yes or no."
✅ Parse question_list (JSON array) to get all questions: JSON.parse(dynamic_variables.question_list)
✅ Ask one question at a time in order: question_list[0], question_list[1], question_list[2], etc.
✅ Wait for yes/no answer before next question
✅ Extract answers: yes/yeah/yep/correct/right = true, no/nope/nah/incorrect/wrong = false
✅ After all questions answered, call submit_form tool with: {question_1: true/false, question_2: true/false, ...}

REMEMBER: The questions exist in conversation_initiation_client_data.dynamic_variables. Access them IMMEDIATELY at conversation start. DO NOT use the default greeting.
```

5. **Save** the changes

### Step 4: Enable Overrides (Optional but Recommended)
To use `override_first_message`, enable overrides:

1. Go to **Agent Settings** > **Security**
2. Enable **"First message" override**
3. This allows `override_first_message` to work in addition to dynamic variables

### Step 5: Test
After updating:
1. Start a new agent session
2. The agent should start with: "Hello! I'm conducting a healthcare survey. [FIRST_QUESTION] Please answer yes or no."
3. It should NOT say: "Hello! How can I help you today?"
4. It should NOT ask: "Please provide the questions"

## Verification

Check the logs when starting a session. You should see:
```
✅ Agent system prompt updated to read questions from conversation_initiation_client_data
✅ Agent system prompt verified - contains our instructions
```

If you see:
```
⚠️ Agent system prompt does NOT contain our instructions!
⚠️ The system prompt in ElevenLabs dashboard might be overriding the API update.
```

Then you need to manually update the system prompt in the dashboard (Step 3).

## Troubleshooting

### Agent still uses default greeting
- Check if system prompt was updated in dashboard
- Verify the prompt contains `{{first_question}}` or `conversation_initiation_client_data`
- Try calling `/api/elevenlabs-agent/update-prompt` again
- Check agent details: `/api/elevenlabs-agent/verify`

### Template variables not working
- Template variables (`{{first_question}}`) might not be injected if dynamic variables aren't passed correctly
- The system prompt will fall back to accessing `conversation_initiation_client_data.dynamic_variables.first_question` directly
- Check console logs to verify `dynamic_variables` are being passed

### Override not working
- Make sure "First message" override is enabled in Agent Settings > Security
- `override_first_message` requires this setting to be enabled

## Current Status

The code now:
1. ✅ Updates system prompt via API when session starts
2. ✅ Verifies the update was successful
3. ✅ Passes dynamic variables correctly via widget
4. ✅ Uses both template syntax and direct access methods
5. ⚠️ **REQUIRES MANUAL UPDATE IN DASHBOARD** for guaranteed results
