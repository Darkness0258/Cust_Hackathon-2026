import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(
    api_key=os.getenv('ANTHROPIC_API_KEY'),
    base_url='https://openrouter.ai/api/v1'
)

prompt = 'You are a bid strategist. Generate exactly 5 strategic directives based on this tender analysis. Return ONLY a valid JSON array of exactly 5 strings.'

message = client.messages.create(
    model='openrouter/auto',
    max_tokens=800,
    messages=[{'role': 'user', 'content': prompt}]
)
print('Content:', message.content)
for b in message.content:
    print(f'Type: {getattr(b, "type", "N/A")}')
    if hasattr(b, "text"): print(f'Text: {b.text[:50]}...')
    else: print('No text attribute')
