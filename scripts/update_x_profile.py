#!/usr/bin/env python3
"""XプロフィールにサイトURLを設定"""

import os
import tweepy


def update_profile():
    api_key = os.getenv('X_API_KEY')
    api_secret = os.getenv('X_API_SECRET')
    access_token = os.getenv('X_ACCESS_TOKEN')
    access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')

    if not all([api_key, api_secret, access_token, access_token_secret]):
        raise ValueError("X API credentials not set")

    # API v1.1 for profile update
    auth = tweepy.OAuth1UserHandler(api_key, api_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)

    # Update profile URL
    api.update_profile(url="https://ai-media.co.jp")
    print("X profile URL updated to https://ai-media.co.jp")

    # Verify
    me = api.verify_credentials()
    print(f"Account: @{me.screen_name}")
    print(f"URL: {me.url}")
    print(f"Description: {me.description}")


if __name__ == "__main__":
    update_profile()
