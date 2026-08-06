"""API routes for source discovery, search, and suggestions."""

import time

import aiohttp
from fastapi import APIRouter, Query

from backend.config import RSSHUB_URL, REQUEST_TIMEOUT, logger

router = APIRouter(prefix="/api/discover", tags=["discover"])

# Cached answer to "is RSSHub reachable", so the picker does not probe it on
# every request. (checked_at_monotonic, healthy)
_RSSHUB_STATE: tuple[float | None, bool] = (None, False)
RSSHUB_CACHE_SECONDS = 120

# Curated source catalog — organized by category
# Each entry maps to an RSSHub route or direct RSS/API URL
SOURCE_CATALOG = [
    # ===== News =====
    {"name": "Hacker News", "category": "News", "type": "rss",
     "url": "https://hnrss.org/frontpage", "icon": "HN",
     "description": "Top stories from Hacker News"},
    {"name": "TechCrunch", "category": "News", "type": "rss",
     "url": "https://techcrunch.com/feed/", "icon": "TC",
     "description": "Technology news and analysis"},
    {"name": "Ars Technica", "category": "News", "type": "rss",
     "url": "https://feeds.arstechnica.com/arstechnica/index", "icon": "AT",
     "description": "Tech policy, science, and culture"},
    {"name": "The Verge", "category": "News", "type": "rss",
     "url": "https://www.theverge.com/rss/index.xml", "icon": "TV",
     "description": "Technology, science, art, and culture"},
    {"name": "Wired", "category": "News", "type": "rss",
     "url": "https://www.wired.com/feed/rss", "icon": "WR",
     "description": "In-depth tech and culture reporting"},
    {"name": "Reuters Top News", "category": "News", "type": "rss",
     "url": f"{RSSHUB_URL}/reuters/world", "icon": "R",
     "description": "World news from Reuters"},
    {"name": "BBC News", "category": "News", "type": "rss",
     "url": "https://feeds.bbci.co.uk/news/rss.xml", "icon": "BBC",
     "description": "Breaking news from BBC"},
    {"name": "NPR News", "category": "News", "type": "rss",
     "url": "https://feeds.npr.org/1001/rss.xml", "icon": "NPR",
     "description": "National and world news"},
    {"name": "Al Jazeera", "category": "News", "type": "rss",
     "url": "https://www.aljazeera.com/xml/rss/all.xml", "icon": "AJ",
     "description": "International news coverage"},
    {"name": "CNN Top Stories", "category": "News", "type": "rss",
     "url": "http://rss.cnn.com/rss/cnn_topstories.rss", "icon": "CNN",
     "description": "Top stories from CNN"},
    {"name": "The Guardian - World", "category": "News", "type": "rss",
     "url": "https://www.theguardian.com/world/rss", "icon": "TG",
     "description": "World news from The Guardian"},
    {"name": "NBC News", "category": "News", "type": "rss",
     "url": "https://feeds.nbcnews.com/nbcnews/public/news", "icon": "NBC",
     "description": "Top stories from NBC News"},
    {"name": "Fox News", "category": "News", "type": "rss",
     "url": "https://moxie.foxnews.com/google-publisher/latest.xml", "icon": "FOX",
     "description": "Latest news from Fox News"},
    {"name": "The Hill", "category": "News", "type": "rss",
     "url": "https://thehill.com/feed/", "icon": "TH",
     "description": "Political news and policy"},

    # ===== Tech =====
    {"name": "Engadget", "category": "Tech", "type": "rss",
     "url": "https://www.engadget.com/rss.xml", "icon": "ENG",
     "description": "Consumer electronics and gadget news"},
    {"name": "Tom's Hardware", "category": "Tech", "type": "rss",
     "url": "https://www.tomshardware.com/feeds/all", "icon": "TH",
     "description": "PC hardware reviews and news"},
    {"name": "9to5Google", "category": "Tech", "type": "rss",
     "url": "https://9to5google.com/feed/", "icon": "9G",
     "description": "Google and Android news"},
    {"name": "9to5Mac", "category": "Tech", "type": "rss",
     "url": "https://9to5mac.com/feed/", "icon": "9M",
     "description": "Apple and Mac news"},
    {"name": "MacRumors", "category": "Tech", "type": "rss",
     "url": "https://feeds.macrumors.com/MacRumors-All", "icon": "MR",
     "description": "Apple rumors and news"},
    {"name": "Android Authority", "category": "Tech", "type": "rss",
     "url": "https://www.androidauthority.com/feed/", "icon": "AA",
     "description": "Android news and reviews"},
    {"name": "ZDNet", "category": "Tech", "type": "rss",
     "url": "https://www.zdnet.com/news/rss.xml", "icon": "ZD",
     "description": "Enterprise tech news"},
    {"name": "The Register", "category": "Tech", "type": "rss",
     "url": "https://www.theregister.com/headlines.atom", "icon": "REG",
     "description": "Biting tech journalism"},
    {"name": "Slashdot", "category": "Tech", "type": "rss",
     "url": "https://rss.slashdot.org/Slashdot/slashdotMain", "icon": "/.",
     "description": "News for nerds, stuff that matters"},

    # ===== Reddit =====
    {"name": "r/technology", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/technology", "icon": "R",
     "description": "Technology discussions and news"},
    {"name": "r/programming", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/programming", "icon": "R",
     "description": "Programming news and discussion"},
    {"name": "r/science", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/science", "icon": "R",
     "description": "Science news and research"},
    {"name": "r/worldnews", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/worldnews", "icon": "R",
     "description": "Major international news"},
    {"name": "r/dataisbeautiful", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/dataisbeautiful", "icon": "R",
     "description": "Data visualizations"},
    {"name": "r/wallstreetbets", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/wallstreetbets", "icon": "R",
     "description": "Stock market discussion"},
    {"name": "r/gaming", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/gaming", "icon": "R",
     "description": "Gaming news and memes"},
    {"name": "r/movies", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/movies", "icon": "R",
     "description": "Movie news and discussion"},
    {"name": "r/books", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/books", "icon": "R",
     "description": "Book discussions and recommendations"},
    {"name": "r/pics", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/pics", "icon": "R",
     "description": "Interesting photos and images"},
    {"name": "r/news", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/news", "icon": "R",
     "description": "US and world news"},
    {"name": "r/AskReddit", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/AskReddit", "icon": "R",
     "description": "Ask and answer questions"},
    {"name": "r/todayilearned", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/todayilearned", "icon": "R",
     "description": "Fascinating facts and discoveries"},
    {"name": "r/sports", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/sports", "icon": "R",
     "description": "Sports highlights and news"},
    {"name": "r/nfl", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/nfl", "icon": "R",
     "description": "NFL football discussion"},
    {"name": "r/nba", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/nba", "icon": "R",
     "description": "NBA basketball discussion"},
    {"name": "r/soccer", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/soccer", "icon": "R",
     "description": "World football/soccer"},
    {"name": "r/learnprogramming", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/learnprogramming", "icon": "R",
     "description": "Programming learning resources"},
    {"name": "r/Python", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/Python", "icon": "R",
     "description": "Python programming community"},
    {"name": "r/javascript", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/javascript", "icon": "R",
     "description": "JavaScript news and discussion"},
    {"name": "r/MachineLearning", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/MachineLearning", "icon": "R",
     "description": "ML research and applications"},
    {"name": "r/startups", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/startups", "icon": "R",
     "description": "Startup discussion and advice"},
    {"name": "r/personalfinance", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/personalfinance", "icon": "R",
     "description": "Personal finance advice"},
    {"name": "r/investing", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/investing", "icon": "R",
     "description": "Investment discussion"},
    {"name": "r/CryptoCurrency", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/CryptoCurrency", "icon": "R",
     "description": "Crypto news and discussion"},
    {"name": "r/space", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/space", "icon": "R",
     "description": "Space exploration and astronomy"},
    {"name": "r/funny", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/funny", "icon": "R",
     "description": "Humor and comedy"},
    {"name": "r/food", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/food", "icon": "R",
     "description": "Food photos and recipes"},
    {"name": "r/DIY", "category": "Reddit", "type": "reddit",
     "url": "https://www.reddit.com/r/DIY", "icon": "R",
     "description": "Do-it-yourself projects"},

    # ===== YouTube =====
    {"name": "Fireship", "category": "YouTube", "type": "youtube",
     "url": "https://www.youtube.com/c/Fireship", "icon": "YT",
     "description": "Fast-paced tech tutorials and news"},
    {"name": "Linus Tech Tips", "category": "YouTube", "type": "youtube",
     "url": "https://www.youtube.com/c/LinusTechTips", "icon": "YT",
     "description": "Tech reviews and builds"},
    {"name": "MKBHD", "category": "YouTube", "type": "youtube",
     "url": "https://www.youtube.com/c/mkbhd", "icon": "YT",
     "description": "Quality tech videos by Marques Brownlee"},
    {"name": "3Blue1Brown", "category": "YouTube", "type": "youtube",
     "url": "https://www.youtube.com/c/3blue1brown", "icon": "YT",
     "description": "Animated math explainers"},
    {"name": "Veritasium", "category": "YouTube", "type": "youtube",
     "url": "https://www.youtube.com/c/veritasium", "icon": "YT",
     "description": "Science and engineering videos"},
    {"name": "Kurzgesagt", "category": "YouTube", "type": "youtube",
     "url": "https://www.youtube.com/c/inanutshell", "icon": "YT",
     "description": "Animated science and philosophy"},
    {"name": "Computerphile", "category": "YouTube", "type": "youtube",
     "url": "https://www.youtube.com/@Computerphile", "icon": "YT",
     "description": "Computer science topics explained"},
    {"name": "Two Minute Papers", "category": "YouTube", "type": "youtube",
     "url": "https://www.youtube.com/c/KárolyZsolnai", "icon": "YT",
     "description": "AI/ML research paper summaries"},
    {"name": "SmarterEveryDay", "category": "YouTube", "type": "youtube",
     "url": "https://www.youtube.com/c/smartereveryday", "icon": "YT",
     "description": "Science and engineering exploration"},
    {"name": "JCS - Criminal Psychology", "category": "YouTube", "type": "youtube",
     "url": "https://www.youtube.com/@JCS", "icon": "YT",
     "description": "Criminal psychology analysis"},
    {"name": "Mark Rober", "category": "YouTube", "type": "youtube",
     "url": "https://www.youtube.com/c/MarkRober", "icon": "YT",
     "description": "Engineering and science projects"},
    {"name": "Wendover Productions", "category": "YouTube", "type": "youtube",
     "url": "https://www.youtube.com/c/Wendoverproductions", "icon": "YT",
     "description": "Logistics, economics, and geography"},
    {"name": "Tom Scott", "category": "YouTube", "type": "youtube",
     "url": "https://www.youtube.com/c/TomScottGo", "icon": "YT",
     "description": "Interesting places and things"},
    {"name": "Corridor Crew", "category": "YouTube", "type": "youtube",
     "url": "https://www.youtube.com/c/CorridorCrew", "icon": "YT",
     "description": "VFX artists react and filmmaking"},

    # ===== Dev =====
    {"name": "GitHub Trending", "category": "Dev", "type": "rss",
     "url": f"{RSSHUB_URL}/github/trending/daily/all/en", "icon": "GH",
     "description": "Trending repositories today"},
    {"name": "GitHub - Python Trending", "category": "Dev", "type": "rss",
     "url": f"{RSSHUB_URL}/github/trending/daily/python/en", "icon": "GH",
     "description": "Trending Python repos"},
    {"name": "GitHub - JS Trending", "category": "Dev", "type": "rss",
     "url": f"{RSSHUB_URL}/github/trending/daily/javascript/en", "icon": "GH",
     "description": "Trending JavaScript repos"},
    {"name": "GitHub - Rust Trending", "category": "Dev", "type": "rss",
     "url": f"{RSSHUB_URL}/github/trending/daily/rust/en", "icon": "GH",
     "description": "Trending Rust repos"},
    {"name": "Dev.to - Top", "category": "Dev", "type": "rss",
     "url": "https://dev.to/feed", "icon": "DEV",
     "description": "Top posts on Dev.to community"},
    {"name": "CSS-Tricks", "category": "Dev", "type": "rss",
     "url": "https://css-tricks.com/feed/", "icon": "CSS",
     "description": "Web design tips and tricks"},
    {"name": "Smashing Magazine", "category": "Dev", "type": "rss",
     "url": "https://www.smashingmagazine.com/feed/", "icon": "SM",
     "description": "Web development and design"},
    {"name": "Stack Overflow Blog", "category": "Dev", "type": "rss",
     "url": "https://stackoverflow.blog/feed/", "icon": "SO",
     "description": "Stack Overflow official blog"},
    {"name": "Real Python", "category": "Dev", "type": "rss",
     "url": "https://realpython.com/atom.xml", "icon": "PY",
     "description": "Python tutorials and articles"},
    {"name": "JavaScript Weekly", "category": "Dev", "type": "rss",
     "url": "https://javascriptweekly.com/rss/", "icon": "JS",
     "description": "Weekly JavaScript newsletter"},
    {"name": "Changelog", "category": "Dev", "type": "rss",
     "url": "https://changelog.com/feed", "icon": "CL",
     "description": "Open source and software dev news"},

    # ===== Finance =====
    {"name": "Yahoo Finance - Markets", "category": "Finance", "type": "rss",
     "url": "https://finance.yahoo.com/news/rssindex", "icon": "$",
     "description": "Market news from Yahoo Finance"},
    {"name": "Bloomberg Markets", "category": "Finance", "type": "rss",
     "url": f"{RSSHUB_URL}/bloomberg", "icon": "BB",
     "description": "Bloomberg markets coverage"},
    {"name": "CNBC Top News", "category": "Finance", "type": "rss",
     "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "icon": "CNBC",
     "description": "Business and financial news"},
    {"name": "MarketWatch", "category": "Finance", "type": "rss",
     "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories", "icon": "MW",
     "description": "Market data and analysis"},
    {"name": "Seeking Alpha", "category": "Finance", "type": "rss",
     "url": "https://seekingalpha.com/market_currents.xml", "icon": "SA",
     "description": "Stock analysis and market news"},
    {"name": "Financial Times", "category": "Finance", "type": "rss",
     "url": f"{RSSHUB_URL}/ft/myft/popular", "icon": "FT",
     "description": "Global financial news"},
    {"name": "The Motley Fool", "category": "Finance", "type": "rss",
     "url": "https://www.fool.com/feeds/index.aspx", "icon": "MF",
     "description": "Investment analysis and advice"},
    {"name": "CoinDesk", "category": "Finance", "type": "rss",
     "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "icon": "CD",
     "description": "Cryptocurrency news and analysis"},

    # ===== Science =====
    {"name": "NASA - Breaking News", "category": "Science", "type": "rss",
     "url": "https://www.nasa.gov/news-release/feed/", "icon": "NASA",
     "description": "Latest from NASA"},
    {"name": "Nature - Latest Research", "category": "Science", "type": "rss",
     "url": "https://www.nature.com/nature.rss", "icon": "NAT",
     "description": "Latest research from Nature"},
    {"name": "MIT Technology Review", "category": "Science", "type": "rss",
     "url": "https://www.technologyreview.com/feed/", "icon": "MIT",
     "description": "Emerging tech and innovation"},
    {"name": "Science Daily", "category": "Science", "type": "rss",
     "url": "https://www.sciencedaily.com/rss/all.xml", "icon": "SD",
     "description": "Latest science research news"},
    {"name": "New Scientist", "category": "Science", "type": "rss",
     "url": "https://www.newscientist.com/feed/home/", "icon": "NS",
     "description": "Science and technology reporting"},
    {"name": "Phys.org", "category": "Science", "type": "rss",
     "url": "https://phys.org/rss-feed/", "icon": "PHY",
     "description": "Science, research, and technology news"},
    {"name": "Space.com", "category": "Science", "type": "rss",
     "url": "https://www.space.com/feeds/all", "icon": "SPC",
     "description": "Space and astronomy news"},
    {"name": "Scientific American", "category": "Science", "type": "rss",
     "url": "http://rss.sciam.com/ScientificAmerican-Global", "icon": "SCI",
     "description": "Science for the curious mind"},

    # ===== Entertainment =====
    {"name": "IGN - All", "category": "Entertainment", "type": "rss",
     "url": "https://feeds.feedburner.com/ign/all", "icon": "IGN",
     "description": "Gaming, movies, and entertainment"},
    {"name": "Polygon", "category": "Entertainment", "type": "rss",
     "url": "https://www.polygon.com/rss/index.xml", "icon": "PLY",
     "description": "Gaming and entertainment culture"},
    {"name": "Kotaku", "category": "Entertainment", "type": "rss",
     "url": "https://kotaku.com/rss", "icon": "KTK",
     "description": "Gaming news and culture"},
    {"name": "PC Gamer", "category": "Entertainment", "type": "rss",
     "url": "https://www.pcgamer.com/rss/", "icon": "PCG",
     "description": "PC gaming news and reviews"},
    {"name": "Variety", "category": "Entertainment", "type": "rss",
     "url": "https://variety.com/feed/", "icon": "VAR",
     "description": "Entertainment industry news"},
    {"name": "Hollywood Reporter", "category": "Entertainment", "type": "rss",
     "url": "https://www.hollywoodreporter.com/feed/", "icon": "HR",
     "description": "Film, TV, and entertainment"},
    {"name": "Pitchfork", "category": "Entertainment", "type": "rss",
     "url": "https://pitchfork.com/feed/feed-news/rss", "icon": "PF",
     "description": "Music reviews and news"},
    {"name": "Rolling Stone", "category": "Entertainment", "type": "rss",
     "url": "https://www.rollingstone.com/feed/", "icon": "RS",
     "description": "Music, culture, and politics"},

    # ===== Sports =====
    # The three ESPN feeds and Bleacher Report were all dead. ESPN answers this
    # client with an empty 202, which used to be recorded as a healthy fetch,
    # so picking the Sports topic gave a new user three panels that said
    # "Loading..." forever and one 404. These four are checked by
    # tests/test_catalog.py.
    {"name": "BBC Sport", "category": "Sports", "type": "rss",
     "url": "https://feeds.bbci.co.uk/sport/rss.xml", "icon": "BBC",
     "description": "Sport headlines from the BBC"},
    {"name": "CBS Sports", "category": "Sports", "type": "rss",
     "url": "https://www.cbssports.com/rss/headlines/", "icon": "CBS",
     "description": "US sports headlines and analysis"},
    {"name": "Yahoo Sports", "category": "Sports", "type": "rss",
     "url": "https://sports.yahoo.com/rss/", "icon": "YS",
     "description": "Scores, news and rumours across US sport"},
    {"name": "The Guardian - Sport", "category": "Sports", "type": "rss",
     "url": "https://www.theguardian.com/sport/rss", "icon": "GRD",
     "description": "Sport from the Guardian, strong on football"},
    {"name": "The Athletic", "category": "Sports", "type": "rss",
     "url": f"{RSSHUB_URL}/theathletic", "icon": "ATH",
     "description": "In-depth sports journalism"},

    # ===== Pinterest (via RSSHub) =====
    {"name": "Pinterest - DIY & Crafts", "category": "Pinterest", "type": "rss",
     "url": f"{RSSHUB_URL}/pinterest/user/pinterest/_created", "icon": "PIN",
     "description": "Pinterest official pins"},
    {"name": "Pinterest - Home Decor", "category": "Pinterest", "type": "rss",
     "url": f"{RSSHUB_URL}/pinterest/user/homedecor", "icon": "PIN",
     "description": "Home decoration ideas and inspiration"},
    {"name": "Pinterest - Food & Recipes", "category": "Pinterest", "type": "rss",
     "url": f"{RSSHUB_URL}/pinterest/user/foodrecipes", "icon": "PIN",
     "description": "Recipes and food photography"},
    {"name": "Pinterest - Fashion", "category": "Pinterest", "type": "rss",
     "url": f"{RSSHUB_URL}/pinterest/user/fashion", "icon": "PIN",
     "description": "Fashion trends and outfit ideas"},

    # ===== Social (via RSSHub) =====
    {"name": "Twitter/X - Elon Musk", "category": "Social", "type": "rss",
     "url": f"{RSSHUB_URL}/twitter/user/elonmusk", "icon": "X",
     "description": "Elon Musk's tweets (requires auth token)",
     "requires_auth": True},
    {"name": "Instagram - NASA", "category": "Social", "type": "rss",
     "url": f"{RSSHUB_URL}/picnob/user/nasa/profile", "icon": "IG",
     "description": "NASA's Instagram (via Picnob proxy)"},
    {"name": "Instagram - NatGeo", "category": "Social", "type": "rss",
     "url": f"{RSSHUB_URL}/picnob/user/natgeo/profile", "icon": "IG",
     "description": "National Geographic photos"},
    {"name": "Mastodon - Trending", "category": "Social", "type": "rss",
     "url": f"{RSSHUB_URL}/mastodon/timeline/mastodon.social/public", "icon": "MAS",
     "description": "Trending on mastodon.social"},

    # ===== Lifestyle =====
    {"name": "Lifehacker", "category": "Lifestyle", "type": "rss",
     "url": "https://lifehacker.com/feed/rss", "icon": "LH",
     "description": "Tips, tricks, and life hacks"},
    {"name": "Wirecutter", "category": "Lifestyle", "type": "rss",
     "url": "https://www.nytimes.com/wirecutter/feed/", "icon": "WC",
     "description": "Product reviews and recommendations"},
    {"name": "CNET", "category": "Lifestyle", "type": "rss",
     "url": "https://www.cnet.com/rss/news/", "icon": "CNET",
     "description": "Tech product reviews and deals"},
    {"name": "Apartment Therapy", "category": "Lifestyle", "type": "rss",
     "url": "https://www.apartmenttherapy.com/main.rss", "icon": "APT",
     "description": "Home design and decor ideas"},
    {"name": "Smitten Kitchen", "category": "Lifestyle", "type": "rss",
     "url": "https://smittenkitchen.com/feed/", "icon": "SK",
     "description": "Recipes and food science"},
]

# RSSHub route templates for custom user input
RSSHUB_TEMPLATES = {
    "pinterest_user": {
        "label": "Pinterest User",
        "route": "/pinterest/user/{username}/_created",
        "placeholder": "Enter Pinterest username",
        "example": "howieserious",
        "category": "Pinterest",
    },
    "reddit_subreddit": {
        "label": "Reddit Subreddit",
        "route": None,  # Use native reddit adapter
        "placeholder": "Enter subreddit name (without r/)",
        "example": "technology",
        "category": "Reddit",
    },
    "youtube_channel": {
        "label": "YouTube Channel",
        "route": None,  # Use native youtube adapter
        "placeholder": "Enter channel URL or name",
        "example": "mkbhd",
        "category": "YouTube",
    },
    "github_repos": {
        "label": "GitHub User Repos",
        "route": "/github/repos/{username}",
        "placeholder": "Enter GitHub username",
        "example": "torvalds",
        "category": "Dev",
    },
    "github_trending": {
        "label": "GitHub Trending",
        "route": "/github/trending/daily/{language}/en",
        "placeholder": "Enter language (or 'all')",
        "example": "python",
        "category": "Dev",
    },
    "twitter_user": {
        "label": "Twitter/X User",
        "route": "/twitter/user/{username}",
        "placeholder": "Enter Twitter username",
        "example": "elonmusk",
        "category": "Social",
        "requires_auth": True,
    },
    "instagram_user": {
        "label": "Instagram User",
        "route": "/picnob/user/{username}/profile",
        "placeholder": "Enter Instagram username",
        "example": "natgeo",
        "category": "Social",
    },
}


# ===== Starter Bundles =====
STARTER_BUNDLES = [
    {
        "id": "morning-news",
        "name": "Morning News",
        "emoji": "📰",
        "description": "Stay informed with trusted global news sources",
        "source_names": ["BBC News", "CNN Top Stories", "The Guardian - World", "NPR News", "NBC News"],
    },
    {
        "id": "tech-deep-dive",
        "name": "Tech Deep Dive",
        "emoji": "💻",
        "description": "Hardware reviews, software analysis, and tech culture",
        "source_names": ["Ars Technica", "The Verge", "Wired", "TechCrunch", "Hacker News"],
    },
    {
        "id": "finance-dashboard",
        "name": "Finance Dashboard",
        "emoji": "📈",
        "description": "Markets, analysis, and financial news",
        "source_names": ["CNBC Top News", "MarketWatch", "Bloomberg Markets", "Seeking Alpha", "Yahoo Finance - Markets"],
    },
    {
        "id": "sports-center",
        "name": "Sports Center",
        "emoji": "🏈",
        "description": "Scores, highlights, and sports analysis",
        "source_names": ["BBC Sport", "CBS Sports", "Yahoo Sports", "The Guardian - Sport", "r/sports"],
    },
    {
        "id": "dev-feed",
        "name": "Dev Feed",
        "emoji": "🛠️",
        "description": "Trending repos, dev blogs, and programming news",
        "source_names": ["Dev.to - Top", "Real Python", "Hacker News", "Stack Overflow Blog", "r/programming"],
    },
    {
        "id": "science-explorer",
        "name": "Science Explorer",
        "emoji": "🔬",
        "description": "Latest discoveries in space, nature, and technology",
        "source_names": ["NASA - Breaking News", "Nature - Latest Research", "Science Daily", "Space.com", "r/science"],
    },
    {
        "id": "entertainment-mix",
        "name": "Entertainment Mix",
        "emoji": "🎮",
        "description": "Gaming, movies, music, and pop culture",
        "source_names": ["IGN - All", "Polygon", "Variety", "Rolling Stone", "r/gaming"],
    },
    {
        "id": "youtube-essentials",
        "name": "YouTube Essentials",
        "emoji": "▶️",
        "description": "Top tech and science YouTube creators",
        "source_names": ["Fireship", "MKBHD", "Veritasium", "3Blue1Brown", "Kurzgesagt"],
    },
]

# ===== Onboarding Topics =====
ONBOARDING_TOPICS = [
    {"id": "news", "name": "News", "emoji": "📰", "categories": ["News"]},
    {"id": "tech", "name": "Tech", "emoji": "💻", "categories": ["Tech"]},
    {"id": "sports", "name": "Sports", "emoji": "🏈", "categories": ["Sports"]},
    {"id": "finance", "name": "Finance", "emoji": "📈", "categories": ["Finance"]},
    {"id": "science", "name": "Science", "emoji": "🔬", "categories": ["Science"]},
    {"id": "entertainment", "name": "Entertainment", "emoji": "🎮", "categories": ["Entertainment"]},
    {"id": "reddit", "name": "Reddit", "emoji": "🤖", "categories": ["Reddit"]},
    {"id": "youtube", "name": "YouTube", "emoji": "▶️", "categories": ["YouTube"]},
    {"id": "dev", "name": "Dev", "emoji": "🛠️", "categories": ["Dev"]},
    {"id": "lifestyle", "name": "Lifestyle", "emoji": "🏠", "categories": ["Lifestyle"]},
]

# Build a lookup dict for catalog sources by name
_CATALOG_BY_NAME = {s["name"]: s for s in SOURCE_CATALOG}


def _resolve_bundle_sources(bundle: dict) -> list[dict]:
    """Resolve a bundle's source_names to full catalog entries."""
    sources = []
    seen_urls = set()
    for name in bundle["source_names"]:
        entry = _CATALOG_BY_NAME.get(name)
        if entry and entry["url"] not in seen_urls:
            sources.append(entry)
            seen_urls.add(entry["url"])
    return sources


@router.get("/bundles")
async def get_bundles():
    """Get starter bundles with resolved source details."""
    usable = {s["name"] for s in await offerable_sources()}
    result = []
    for bundle in STARTER_BUNDLES:
        sources = [
            s for s in _resolve_bundle_sources(bundle) if s["name"] in usable
        ]
        result.append({
            "id": bundle["id"],
            "name": bundle["name"],
            "emoji": bundle["emoji"],
            "description": bundle["description"],
            "source_count": len(sources),
            "sources": sources,
        })
    return result


@router.get("/onboarding/topics")
async def get_onboarding_topics():
    """Get onboarding topic cards with source counts."""
    catalog = await offerable_sources()
    result = []
    for topic in ONBOARDING_TOPICS:
        count = sum(
            1 for s in catalog
            if s["category"] in topic["categories"]
        )
        result.append({
            "id": topic["id"],
            "name": topic["name"],
            "emoji": topic["emoji"],
            "source_count": count,
        })
    return result


@router.get("/onboarding/sources")
async def get_onboarding_sources(topics: str = Query(..., min_length=1)):
    """Get catalog sources for selected onboarding topics.
    topics is a comma-separated list of topic IDs."""
    topic_ids = [t.strip().lower() for t in topics.split(",")]
    topic_map = {t["id"]: t for t in ONBOARDING_TOPICS}

    categories = set()
    for tid in topic_ids:
        topic = topic_map.get(tid)
        if topic:
            categories.update(topic["categories"])

    catalog = await offerable_sources()
    sources = [s for s in catalog if s["category"] in categories]
    return sources


@router.get("/suggestions")
async def get_suggestions(category: str = None):
    """Get suggested sources, optionally filtered by category."""
    catalog = await offerable_sources()
    if category:
        return [s for s in catalog if s["category"].lower() == category.lower()]
    return catalog


@router.get("/categories")
async def get_categories():
    """Get all available source categories."""
    cats = {}
    for s in await offerable_sources():
        cat = s["category"]
        if cat not in cats:
            cats[cat] = 0
        cats[cat] += 1
    return [{"name": k, "count": v} for k, v in cats.items()]


@router.get("/templates")
async def get_templates():
    """Get RSSHub templates for adding custom sources by platform."""
    return RSSHUB_TEMPLATES


@router.get("/search")
async def search_sources(q: str = Query(..., min_length=2)):
    """Search the source catalog and RSSHub for matching sources."""
    q_lower = q.lower()
    results = []

    # Search catalog
    for s in SOURCE_CATALOG:
        if (q_lower in s["name"].lower()
                or q_lower in s.get("description", "").lower()
                or q_lower in s.get("category", "").lower()):
            results.append({**s, "source": "catalog"})

    # Auto-generate platform suggestions for any search term
    if not q.startswith("http") and len(q_lower) > 1:
        term = q_lower.replace("r/", "").replace("/", "")

        # Reddit subreddit
        results.append({
            "name": f"r/{term}",
            "category": "Reddit",
            "type": "reddit",
            "url": f"https://www.reddit.com/r/{term}",
            "icon": "R",
            "description": f"Reddit r/{term} subreddit",
            "source": "generated",
        })

        # YouTube channel search
        results.append({
            "name": f"YouTube: {q}",
            "category": "YouTube",
            "type": "youtube",
            "url": f"https://www.youtube.com/@{term}",
            "icon": "YT",
            "description": f"YouTube channel @{term}",
            "source": "generated",
        })

        # Pinterest user
        results.append({
            "name": f"Pinterest: {q}",
            "category": "Pinterest",
            "type": "rss",
            "url": f"{RSSHUB_URL}/pinterest/user/{term}/_created",
            "icon": "PIN",
            "description": f"Pinterest pins by {term}",
            "source": "generated",
        })

        # GitHub trending for language
        results.append({
            "name": f"GitHub Trending: {q}",
            "category": "Dev",
            "type": "rss",
            "url": f"{RSSHUB_URL}/github/trending/daily/{term}/en",
            "icon": "GH",
            "description": f"Trending {q} repos on GitHub",
            "source": "generated",
        })

    # If it looks like a URL
    if q.startswith("http"):
        results.append({
            "name": q.split("/")[-1] or "Custom Source",
            "category": "Custom",
            "type": "rss",
            "url": q,
            "icon": "RSS",
            "description": f"RSS feed at {q}",
            "source": "url",
        })

    # Try RSSHub search if available
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{RSSHUB_URL}/rsshub/routes/{q}",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    routes = data.get("data", {})
                    for route_key, route_info in routes.items():
                        if isinstance(route_info, dict):
                            results.append({
                                "name": route_info.get("name", route_key),
                                "category": "RSSHub",
                                "type": "rss",
                                "url": f"{RSSHUB_URL}{route_key}",
                                "icon": "RSH",
                                "description": route_info.get("description", "RSSHub route"),
                                "rsshub_route": route_key,
                                "source": "rsshub",
                            })
    except Exception:
        pass  # RSSHub search is best-effort

    return results


def is_rsshub_source(entry: dict) -> bool:
    """Does this catalog entry only work if RSSHub is running?"""
    return entry["url"].startswith(RSSHUB_URL)


async def rsshub_available() -> bool:
    """Is RSSHub actually reachable, cached briefly.

    Sixteen catalog entries are RSSHub routes. RSSHub is a separate service
    this project does not ship, and the README calls it optional, so for anyone
    who has not run one those sixteen were sixteen sources in the picker that
    could only ever produce a connection error. Offering a source that cannot
    work is worse than not offering it.
    """
    global _RSSHUB_STATE
    now = time.monotonic()
    cached_at, healthy = _RSSHUB_STATE
    if cached_at is not None and (now - cached_at) < RSSHUB_CACHE_SECONDS:
        return healthy

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{RSSHUB_URL}/healthz",
                timeout=aiohttp.ClientTimeout(total=3),
            ) as resp:
                healthy = resp.status == 200
    except Exception:  # noqa: BLE001 - any failure means "cannot use it"
        healthy = False

    _RSSHUB_STATE = (now, healthy)
    return healthy


async def offerable_sources() -> list[dict]:
    """The catalog, minus anything that cannot work in this installation."""
    if await rsshub_available():
        return SOURCE_CATALOG
    return [s for s in SOURCE_CATALOG if not is_rsshub_source(s)]


@router.get("/rsshub/test")
async def test_rsshub():
    """Check if RSSHub is running and accessible."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{RSSHUB_URL}/healthz",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                healthy = resp.status == 200
                return {"status": "ok" if healthy else "error", "url": RSSHUB_URL}
    except Exception as e:
        return {"status": "error", "url": RSSHUB_URL, "error": str(e)}
