"""Test script to verify OpenAI AI agent connection"""
from ai import client, ask_ai
import os

print("="*60)
print("TESTING AI AGENT CONNECTION")
print("="*60)

# Check API key
api_key = os.environ.get("OPEN_API_KEY")
if api_key and api_key != "OPEN_API_KEY":
    print(f"✓ API Key found: {api_key[:8]}...{api_key[-4:]}")
else:
    print("✗ No valid API key found")
    print("  Set OPEN_API_KEY environment variable or in .env file")

# Check client
if client:
    print("✓ OpenAI client initialized")
else:
    print("✗ OpenAI client not initialized")

print("\n" + "="*60)
print("TESTING AI AGENT INTERPRETATION")
print("="*60)

# Test commands
test_commands = [
    "show me mars",
    "track the red planet",
    "point to jupiter",
    "where is venus",
    "find saturn"
]

if client:
    for cmd in test_commands:
        print(f"\nCommand: '{cmd}'")
        result = ask_ai(cmd)
        print(f"Result: {result}")
else:
    print("\nSkipping tests - AI agent not available")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
