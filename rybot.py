import os
import time
import json
import random
import requests
import tweepy
import schedule
from datetime import datetime, timedelta

# Set up environment variables (you'll use GitHub Secrets for deployment)
# For local testing, use a .env file or set these directly in your environment
TWITTER_CONSUMER_KEY = os.environ.get("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = os.environ.get("TWITTER_CONSUMER_SECRET") 
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

# Initialize Twitter API client
auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)
client = tweepy.Client(
    consumer_key=TWITTER_CONSUMER_KEY,
    consumer_secret=TWITTER_CONSUMER_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
)

# Memory file to store agent state between runs
MEMORY_FILE = "agent_memory.json"

def load_memory():
    """Load agent memory from file"""
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Initialize with default values if file doesn't exist
        return {
            "tweets": [],
            "last_prices": {},
            "topics_used": [],
            "last_run": datetime.now().isoformat(),
            "total_tweets": 0,
            "mentions_replied": []
        }

def save_memory(memory):
    """Save agent memory to file"""
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def get_crypto_data():
    """Get cryptocurrency market data from free APIs"""
    try:
        # CoinGecko API (free tier, no API key needed)
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 15,
            "page": 1,
            "sparkline": False,
            "price_change_percentage": "24h"
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        # Format the data
        crypto_data = {}
        for coin in data:
            crypto_data[coin["id"]] = {
                "name": coin["name"],
                "symbol": coin["symbol"].upper(),
                "price": coin["current_price"],
                "price_change_24h": coin["price_change_percentage_24h"],
                "market_cap": coin["market_cap"],
                "volume": coin["total_volume"]
            }
        
        return crypto_data
    except Exception as e:
        print(f"Error fetching crypto data: {e}")
        return {}

def get_crypto_news():
    """Get cryptocurrency news from free APIs"""
    try:
        # CryptoCompare API (free tier, no API key needed)
        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        response = requests.get(url)
        data = response.json()
        
        news_items = []
        if data.get("Data"):
            for item in data["Data"][:5]:  # Get top 5 news items
                news_items.append({
                    "title": item["title"],
                    "url": item["url"],
                    "source": item["source"],
                    "published_at": item["published_on"]
                })
        
        return news_items
    except Exception as e:
        print(f"Error fetching crypto news: {e}")
        return []

def get_recent_mentions(memory):
    """Get recent mentions that haven't been replied to yet"""
    try:
        mentions = api.mentions_timeline(count=10)
        replied_ids = memory.get("mentions_replied", [])
        
        new_mentions = []
        for mention in mentions:
            if str(mention.id) not in replied_ids:
                new_mentions.append({
                    "id": mention.id,
                    "text": mention.text,
                    "user": mention.user.screen_name,
                    "created_at": mention.created_at.isoformat()
                })
        
        return new_mentions
    except Exception as e:
        print(f"Error fetching mentions: {e}")
        return []

def generate_market_update(crypto_data):
    """Generate a market update tweet"""
    # Select top 5 cryptocurrencies
    top_coins = list(crypto_data.values())[:5]
    
    tweet = "🚀 #Crypto Market Update 📊\n\n"
    
    for coin in top_coins:
        emoji = "🟢" if coin["price_change_24h"] > 0 else "🔴"
        tweet += f"{emoji} #{coin['symbol']}: ${coin['price']:,.2f} ({coin['price_change_24h']:.2f}%)\n"
    
    # Add a random insight
    insights = [
        "Market sentiment appears cautiously optimistic today.",
        "Trading volumes remain steady across major exchanges.",
        "DeFi tokens showing relative strength compared to the broader market.",
        "Watch for potential breakout patterns forming on several altcoins.",
        "Funding rates suggest a balanced derivatives market currently.",
        "On-chain metrics indicate accumulation at these price levels."
    ]
    
    tweet += f"\n💡 {random.choice(insights)}\n"
    tweet += f"\n#cryptocurrency #bitcoin #ethereum"
    
    # Ensure within Twitter's character limit
    if len(tweet) > 280:
        tweet = tweet[:277] + "..."
    
    return tweet

def generate_news_update(news_items):
    """Generate a news update tweet"""
    if not news_items:
        return None
    
    # Select a random news item
    news = random.choice(news_items)
    
    tweet = f"📰 #Crypto News Alert\n\n"
    tweet += f"{news['title']}\n\n"
    
    # Add a brief commentary
    commentaries = [
        "This could impact market sentiment in the short term.",
        "Worth watching how this develops.",
        "Potentially significant for the ecosystem.",
        "What are your thoughts on this development?",
        "This aligns with recent market movements.",
        "An interesting development for the industry."
    ]
    
    tweet += f"{random.choice(commentaries)}\n\n"
    tweet += f"Source: {news['source']}"
    
    # Ensure within Twitter's character limit
    if len(tweet) > 280:
        title_length = 100
        tweet = f"📰 #Crypto News Alert\n\n{news['title'][:title_length]}...\n\n{random.choice(commentaries)}\n\nSource: {news['source']}"
        
        # Truncate further if still too long
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
    
    return tweet

def generate_educational_content(memory):
    """Generate educational content about crypto"""
    # List of educational topics
    topics = [
        {
            "topic": "What is #DeFi?",
            "content": "Decentralized Finance (#DeFi) refers to financial applications built on blockchain technology that aim to replace traditional financial intermediaries with protocol-based relationships. It enables permissionless financial transactions. #CryptoEducation"
        },
        {
            "topic": "Understanding #NFTs",
            "content": "Non-Fungible Tokens (#NFTs) are unique digital assets verified using blockchain technology. Unlike cryptocurrencies, each NFT has unique properties and isn't interchangeable. They represent ownership of digital or physical items. #CryptoBasics"
        },
        {
            "topic": "What is #HODL?",
            "content": "HODL is crypto slang for holding onto your assets regardless of price volatility. Originally a typo of 'hold' in a 2013 Bitcoin forum, it's now backronymed to mean 'Hold On for Dear Life'. A long-term investment strategy. #CryptoTerms"
        },
        {
            "topic": "#PoW vs #PoS",
            "content": "Proof of Work (#PoW) and Proof of Stake (#PoS) are consensus mechanisms. PoW requires solving complex puzzles (mining), while PoS validators are selected based on the number of coins they stake. PoS is more energy-efficient. #BlockchainBasics"
        },
        {
            "topic": "What are #SmartContracts?",
            "content": "Smart Contracts are self-executing contracts where the terms are directly written into code. They automatically execute when conditions are met, enabling trustless transactions without intermediaries. The foundation of many crypto applications. #Blockchain"
        },
        {
            "topic": "#Layer2 Solutions",
            "content": "Layer 2 solutions are protocols built on top of existing blockchains (Layer 1) to improve scalability and efficiency. They process transactions off the main chain while inheriting its security, reducing fees and increasing speed. #CryptoInfrastructure"
        },
        {
            "topic": "What is #Staking?",
            "content": "Staking is the process of locking up cryptocurrency to support network operations in exchange for rewards. It's common in Proof of Stake blockchains, where stakers validate transactions and help secure the network. #PassiveIncome #Crypto"
        },
        {
            "topic": "Understanding #TokenEconomics",
            "content": "Tokenomics refers to the economic model of a cryptocurrency. It includes supply mechanisms (inflation/deflation), utility, distribution, and incentive structures. Strong tokenomics is crucial for a project's long-term sustainability. #CryptoInvesting"
        }
    ]
    
    # Filter out recently used topics
    used_topics = memory.get("topics_used", [])
    available_topics = [t for t in topics if t["topic"] not in used_topics]
    
    # If all topics have been used, reset
    if not available_topics:
        available_topics = topics
        memory["topics_used"] = []
    
    # Select a random topic
    selected_topic = random.choice(available_topics)
    
    # Update memory
    memory["topics_used"].append(selected_topic["topic"])
    
    return selected_topic["content"]

def generate_trend_analysis(crypto_data, memory):
    """Generate a trend analysis based on price changes"""
    # Compare current prices with previous prices
    last_prices = memory.get("last_prices", {})
    insights = []
    
    for coin_id, data in crypto_data.items():
        if coin_id in last_prices:
            # Calculate price change since last check
            prev_price = last_prices[coin_id]
            current_price = data["price"]
            percent_change = ((current_price - prev_price) / prev_price) * 100
            
            # Only include significant changes
            if abs(percent_change) > 3:
                direction = "up" if percent_change > 0 else "down"
                insights.append({
                    "coin": data["symbol"],
                    "change": percent_change,
                    "direction": direction
                })
    
    # Update last prices
    for coin_id, data in crypto_data.items():
        last_prices[coin_id] = data["price"]
    memory["last_prices"] = last_prices
    
    # Generate tweet if we have insights
    if insights:
        # Sort by absolute change
        insights.sort(key=lambda x: abs(x["change"]), reverse=True)
        
        # Take top 3
        top_insights = insights[:3]
        
        tweet = "📊 #Crypto Trend Alert 👀\n\n"
        
        for insight in top_insights:
            emoji = "🚀" if insight["direction"] == "up" else "📉"
            tweet += f"{emoji} #{insight['coin']} has moved {insight['change']:.2f}% {insight['direction']} since my last check\n"
        
        # Add a commentary
        commentaries = [
            "Keep an eye on these movements as the day progresses.",
            "Volume suggests this trend might continue in the short term.",
            "These moves align with broader market sentiment currently.",
            "Technical indicators suggest watching for potential reversals.",
            "This volatility presents both risks and opportunities.",
            "What's your take on these price movements?"
        ]
        
        tweet += f"\n💭 {random.choice(commentaries)}\n"
        tweet += f"\n#crypto #trading #marketanalysis"
        
        # Ensure within Twitter's character limit
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
        
        return tweet
    
    return None

def respond_to_mention(mention):
    """Generate a response to a user mention"""
    # Extract any potential questions or keywords
    text = mention["text"].lower()
    
    # Check for common crypto questions
    responses = []
    
    if any(word in text for word in ["price", "prediction", "forecast", "going", "moon"]):
        responses = [
            f"Hey @{mention['user']}! While I don't make price predictions, the current market conditions suggest watching key support/resistance levels. What's your current strategy? #DYOR",
            f"Thanks for reaching out @{mention['user']}! Price action is always complex - I focus on fundamentals rather than short-term movements. What specific aspect interests you? #CryptoAnalysis",
            f"Hi @{mention['user']}! I avoid making price predictions as they're often unreliable. Instead, consider project fundamentals, market cycles, and your risk tolerance. What's your investment horizon? #CryptoAdvice"
        ]
    elif any(word in text for word in ["beginner", "start", "new", "learn", "advice"]):
        responses = [
            f"Welcome to crypto @{mention['user']}! Start with researching established projects like Bitcoin & Ethereum, use reputable exchanges, and never invest more than you can afford to lose. Any specific questions? #CryptoBasics",
            f"Hi @{mention['user']}! For beginners, I recommend: 1) Learn blockchain basics 2) Start small 3) Use hardware wallets for security 4) DCA strategy. What area interests you most? #CryptoTips",
            f"Great to see new people in the space @{mention['user']}! Remember: research thoroughly, secure your assets properly, and think long-term. Would you like resources on any specific topic? #CryptoEducation"
        ]
    elif any(word in text for word in ["defi", "yield", "farming", "staking"]):
        responses = [
            f"Hey @{mention['user']}! DeFi offers interesting opportunities but comes with risks. Always verify protocols, understand smart contract risks, and start with small amounts. Which platforms are you considering? #DeFi",
            f"Hi @{mention['user']}! When exploring yield opportunities, security should be your first priority. Established protocols with audits are generally safer, though no guarantee. What's your risk tolerance? #DeFiSafety",
            f"Thanks for the mention @{mention['user']}! DeFi is evolving rapidly - the key is balancing potential yields against platform risks. Diversification across protocols can help. Any specific yield strategies you're curious about? #DeFiStrategies"
        ]
    else:
        # General responses
        responses = [
            f"Thanks for reaching out @{mention['user']}! I'm always happy to discuss crypto markets and technology. Anything specific on your mind? #CryptoCommunity",
            f"Hey @{mention['user']}! Appreciate the mention. The crypto space is always evolving - what aspects are you currently focused on? #CryptoDiscussion",
            f"Hi @{mention['user']}! Thanks for connecting. I'm here to share insights on crypto markets and technology. What brought you to the crypto space? #BlockchainTech"
        ]
    
    return random.choice(responses)

def post_tweet(content):
    """Post a tweet and return the tweet ID"""
    try:
        response = client.create_tweet(text=content)
        tweet_id = response.data["id"]
        print(f"Posted tweet: {content[:50]}...")
        return tweet_id
    except Exception as e:
        print(f"Error posting tweet: {e}")
        return None

def post_reply(content, reply_to_id):
    """Post a reply to a specific tweet"""
    try:
        response = client.create_tweet(
            text=content,
            in_reply_to_tweet_id=reply_to_id
        )
        reply_id = response.data["id"]
        print(f"Posted reply: {content[:50]}...")
        return reply_id
    except Exception as e:
        print(f"Error posting reply: {e}")
        return None

def run_bot():
    """Main function to run the crypto Twitter bot"""
    print(f"Running crypto bot at {datetime.now().isoformat()}")
    
    # Load memory
    memory = load_memory()
    
    # Get crypto data
    crypto_data = get_crypto_data()
    if not crypto_data:
        print("Failed to get crypto data, aborting run")
        return
    
    # Get news
    news_items = get_crypto_news()
    
    # Get mentions
    mentions = get_recent_mentions(memory)
    
    # Decide what kind of content to post
    action = random.choice(["market", "news", "education", "trend", "engage"])
    tweet_id = None
    
    # Override with engagement if there are new mentions
    if mentions and random.random() < 0.8:  # 80% chance to respond if there are mentions
        action = "engage"
    
    # Execute selected action
    if action == "market":
        content = generate_market_update(crypto_data)
        tweet_id = post_tweet(content)
        if tweet_id:
            memory["tweets"].append({
                "id": tweet_id,
                "type": "market_update",
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
    
    elif action == "news" and news_items:
        content = generate_news_update(news_items)
        if content:
            tweet_id = post_tweet(content)
            if tweet_id:
                memory["tweets"].append({
                    "id": tweet_id,
                    "type": "news",
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                })
    
    elif action == "education":
        content = generate_educational_content(memory)
        tweet_id = post_tweet(content)
        if tweet_id:
            memory["tweets"].append({
                "id": tweet_id,
                "type": "education",
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
    
    elif action == "trend":
        content = generate_trend_analysis(crypto_data, memory)
        if content:
            tweet_id = post_tweet(content)
            if tweet_id:
                memory["tweets"].append({
                    "id": tweet_id,
                    "type": "trend_analysis",
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                })
        else:
            # Fallback to market update if no trends detected
            content = generate_market_update(crypto_data)
            tweet_id = post_tweet(content)
            if tweet_id:
                memory["tweets"].append({
                    "id": tweet_id,
                    "type": "market_update",
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                })
    
    elif action == "engage" and mentions:
        # Respond to the first unaddressed mention
        mention = mentions[0]
        content = respond_to_mention(mention)
        reply_id = post_reply(content, mention["id"])
        
        if reply_id:
            # Record the reply
            memory["mentions_replied"].append(str(mention["id"]))
            # Keep the list manageable
            if len(memory["mentions_replied"]) > 100:
                memory["mentions_replied"] = memory["mentions_replied"][-100:]
            
            memory["tweets"].append({
                "id": reply_id,
                "type": "reply",
                "content": content,
                "reply_to": mention["id"],
                "reply_to_user": mention["user"],
                "timestamp": datetime.now().isoformat()
            })
    
    # Update total tweets count if we posted something
    if tweet_id:
        memory["total_tweets"] = memory.get("total_tweets", 0) + 1
    
    # Update last run time
    memory["last_run"] = datetime.now().isoformat()
    
    # Trim tweets history to prevent file size issues
    if len(memory["tweets"]) > 100:
        memory["tweets"] = memory["tweets"][-100:]
    
    # Save updated memory
    save_memory(memory)
    
    print(f"Bot run completed at {datetime.now().isoformat()}")
    print("-" * 40)

if __name__ == "__main__":
    # For local testing, run once
    run_bot()
    
    # For scheduled running (if running locally or in a container)
    # schedule.every(3).hours.do(run_bot)
    # 
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)
