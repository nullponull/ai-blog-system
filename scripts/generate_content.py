#!/usr/bin/env python3
"""
Generate content using Gemini API with model rotation for quota management
"""

import sys
import os
import requests
import json
import time

def call_gemini_api(prompt, output_file=None):
    """
    Call Gemini API with model rotation
    """
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY not set", file=sys.stderr)
        return False

    # Model rotation list
    models = [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.0-flash"
    ]

    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': api_key
    }

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.9,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 8192,
        }
    }

    # Try each model until one succeeds
    for model_index, model in enumerate(models):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        try:
            print(f"🤖 Trying model: {model}", file=sys.stderr)
            response = requests.post(url, headers=headers, json=data, timeout=120)

            # Check for quota error
            if response.status_code == 429:
                print(f"⚠️ Quota limit reached for {model}", file=sys.stderr)
                continue  # Try next model

            response.raise_for_status()

            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                content = result['candidates'][0]['content']['parts'][0]['text']
                print(f"✅ Successfully generated with {model}", file=sys.stderr)

                # Write to file or stdout
                if output_file:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                else:
                    print(content)

                return True
            else:
                print(f"⚠️ No content generated with {model}", file=sys.stderr)
                continue

        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed for {model}: {e}", file=sys.stderr)
            if "quota" in str(e).lower() or "429" in str(e):
                continue  # Try next model
            continue
        except Exception as e:
            print(f"💀 Error processing response for {model}: {e}", file=sys.stderr)
            continue

    print("❌ All models failed or quota exceeded", file=sys.stderr)
    return False

def main():
    if len(sys.argv) < 2:
        print("Usage: generate_content.py <prompt> [output_file]", file=sys.stderr)
        sys.exit(1)

    prompt = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    success = call_gemini_api(prompt, output_file)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()