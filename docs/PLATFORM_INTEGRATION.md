# Platform Integration Guide - Free & Unlimited Methods

> Research document covering free, no-paid-tier methods for pulling content from major platforms.
> All methods documented here are either fully free, open-source, or use platform-native feeds with no API key required.

---

## Table of Contents

1. [YouTube](#1-youtube)
2. [Reddit](#2-reddit)
3. [Twitter / X](#3-twitter--x)
4. [Instagram](#4-instagram)
5. [Facebook](#5-facebook)
6. [LinkedIn](#6-linkedin)
7. [Email (Gmail / Outlook)](#7-email-gmail--outlook)
8. [Hacker News](#8-hacker-news)
9. [GitHub](#9-github)
10. [Twitch](#10-twitch)
11. [Discord](#11-discord)
12. [News Sites](#12-news-sites)
13. [Summary Matrix](#13-summary-matrix)

---

## 1. YouTube

### Method A: Native RSS Feeds (RECOMMENDED)

YouTube provides free, built-in RSS/Atom feeds for every channel and playlist. No API key, no authentication, no rate limit concerns for normal usage.

**Channel feed:**
```
https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
```

**Playlist feed:**
```
https://www.youtube.com/feeds/videos.xml?playlist_id=PLAYLIST_ID
```

**Finding channel IDs:**
- View page source on the channel page, search for browse_id or externalId
- Or extract from the channel URL if it uses the /channel/UCxxxxxx format

**Data returned:** Title, video URL, thumbnail, description, published date, author name.

**Limitations:**
- Returns only the **15 most recent** videos per channel
- No view counts, like counts, or comment data
- No search functionality

| Attribute | Value |
|-----------|-------|
| Cost | Free |
| Auth | None |
| Rate Limit | None documented (standard HTTP politeness applies) |
| Reliability | Excellent - maintained by YouTube directly |
| Data Freshness | Near real-time (updates within minutes of publish) |

### Method B: Invidious API (Self-Hosted)

Invidious is an open-source alternative YouTube frontend with a full JSON API. Self-hostable via Docker.

**Key endpoints:**
```
GET /api/v1/channels/{channel_id}
GET /api/v1/channels/{channel_id}/videos
GET /api/v1/videos/{video_id}
GET /api/v1/search?q=query
GET /api/v1/trending
GET /api/v1/popular
GET /api/v1/transcripts/{video_id}
```

**Data returned:** Everything YouTube RSS provides PLUS view counts, like counts, subscriber counts, video duration, adaptive/legacy format URLs, captions, related videos.

**Limitations:**
- Must self-host for reliability (public instances are overloaded and frequently blocked)
- YouTube actively blocks Invidious; requires regular token rotation
- Written in Crystal (not Python) - heavier to maintain

| Attribute | Value |
|-----------|-------|
| Cost | Free (self-hosted) |
| Auth | None for public data |
| Rate Limit | YouTube internal limits apply (IP-based) |
| Reliability | Moderate - requires maintenance against YouTube blocks |
| Repo | https://github.com/iv-org/invidious |
### Method C: yt-dlp Metadata Extraction

yt-dlp can extract rich metadata from YouTube (and 1000+ other sites) without downloading any video.

**Python API usage:**
```python
import yt_dlp

opts = {"quiet": True, "no_warnings": True, "skip_download": True}
with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info(
        "https://www.youtube.com/watch?v=VIDEO_ID",
        download=False
    )
    # info contains: title, description, view_count, like_count,
    # upload_date, duration, thumbnail, channel, tags, categories...
```

**Limitations:**
- Slower than RSS (makes full page requests per video/channel)
- YouTube may rate-limit aggressive usage
- Best used as a fallback for enriching RSS data with view counts, etc.

| Attribute | Value |
|-----------|-------|
| Cost | Free, open-source |
| Auth | None |
| Rate Limit | YouTube IP-based throttling; use delays between requests |
| Reliability | Excellent - very actively maintained, adapts to YouTube changes fast |
| Repo | https://github.com/yt-dlp/yt-dlp |

### Recommendation for Awesome Aggregator

**Primary:** YouTube RSS feeds (Method A) - fast, free, zero auth, covers 95% of use cases.
**Enrichment:** yt-dlp (Method C) - on-demand metadata fetch when user clicks details on a video.

---

## 2. Reddit

### Method A: Native RSS Feeds (RECOMMENDED)

Reddit provides built-in RSS feeds by appending .rss to any URL. No API key, no auth.

**Subreddit feed:**
```
https://www.reddit.com/r/SUBREDDIT/.rss
https://www.reddit.com/r/SUBREDDIT/top/.rss?sort=top&t=day&limit=25
```

**Multi-subreddit feed:**
```
https://www.reddit.com/r/python+javascript+rust/.rss
```

**User feed:**
```
https://www.reddit.com/user/USERNAME/.rss
```

**Data returned:** Post title, author, subreddit, permalink, selftext/link, published date, score (at time of feed generation).

| Attribute | Value |
|-----------|-------|
| Cost | Free |
| Auth | None |
| Rate Limit | None documented for RSS |
| Reliability | Excellent |

### Method B: .json Endpoints

Append .json to any Reddit URL to get structured JSON data. Richer than RSS.

**Examples:**
```
https://www.reddit.com/r/SUBREDDIT.json
https://www.reddit.com/r/SUBREDDIT/hot.json?limit=25
https://old.reddit.com/r/SUBREDDIT/comments/POST_ID.json
https://www.reddit.com/user/USERNAME/about.json
```

**Data returned:** Full post data including score, num_comments, upvote_ratio, all_awardings, flair, media embeds, crosspost info.

**Important:** Set a descriptive User-Agent header to avoid blocks:
```python
headers = {"User-Agent": "AwesomeAggregator/1.0 (by /u/yourusername)"}
```

| Attribute | Value |
|-----------|-------|
| Cost | Free |
| Auth | None |
| Rate Limit | ~10 requests/minute (unauthenticated) |
| Reliability | Good - still working as of 2026 |

### Method C: Redlib / Libreddit (Self-Hosted Frontend)

Redlib (formerly Libreddit) is an actively maintained private Reddit frontend written in Rust. Can be self-hosted to proxy Reddit data.

- **Redlib:** https://github.com/redlib-org/redlib (active, recommended)
- **Libreddit:** https://github.com/libreddit/libreddit (legacy, less active)
- **Teddit:** https://codeberg.org/teddit/teddit (Node.js, no longer actively maintained)

| Attribute | Value |
|-----------|-------|
| Cost | Free (self-hosted) |
| Auth | None |
| Rate Limit | Reddit IP-based limits |
| Reliability | Moderate - depends on Reddit not blocking the instance IP |

### Recommendation for Awesome Aggregator

**Primary:** Reddit RSS feeds (Method A) for basic feeds; .json endpoints (Method B) for richer data.
**The .json approach is already implemented** in the existing backend/sources/reddit.py adapter.

---
## 3. Twitter / X

Twitter/X is the hardest platform to access for free since the API became paid-only. All methods here are workarounds with varying reliability.

### Method A: RSS-Bridge Twitter Bridge (Self-Hosted)

RSS-Bridge is a self-hosted PHP app that generates RSS feeds for sites that do not natively offer them. It includes a TwitterV2 bridge.

**Caveat:** The TwitterV2 bridge requires a **Twitter Developer Bearer token**, which means you need a Twitter Developer account. The free API tier gives you read access to the v2 API endpoints.

**Setup:**
```bash
docker run -p 3000:80 rssbridge/rss-bridge
```

Then access: http://localhost:3000/?action=display&bridge=TwitterBridge&context=By+username&u=USERNAME&format=Atom

| Attribute | Value |
|-----------|-------|
| Cost | Free (self-hosted), but Twitter API key may be needed |
| Auth | Twitter Bearer token for TwitterV2 bridge |
| Rate Limit | Twitter API free tier: 1,500 tweets read/month |
| Reliability | Low-Moderate - Twitter frequently breaks third-party access |
| Repo | https://github.com/RSS-Bridge/rss-bridge |

### Method B: Nitter Instances

Nitter is an alternative Twitter frontend that provided RSS feeds. The main instance (nitter.net) is dead, but some instances survive.

**Known working instances (as of early 2026, subject to breakage):**
- xcancel.com
- nitter.privacydev.net (intermittent)

**RSS format:**
```
https://xcancel.com/USERNAME/rss
```

**Critical issue:** Nitter instances now require real X account session tokens to function, and X actively blocks them. Reliability is poor.

| Attribute | Value |
|-----------|-------|
| Cost | Free |
| Auth | None (for user), but instance operators need X session tokens |
| Rate Limit | Instance-dependent |
| Reliability | LOW - instances break frequently, X actively blocks them |

### Method C: bird.makeup (Fediverse Bridge)

bird.makeup bridges Twitter/X accounts into the Fediverse (Mastodon/ActivityPub). You can follow X accounts from any Mastodon instance.

**How it works:** Search for @username@bird.makeup from any Mastodon client. Posts from that X account appear in your Mastodon timeline.

**For RSS:** Mastodon exposes RSS feeds for every account:
```
https://YOUR_MASTODON_INSTANCE/@username@bird.makeup.rss
```

| Attribute | Value |
|-----------|-------|
| Cost | Free |
| Auth | Need a Mastodon account (free on any instance) |
| Rate Limit | Mastodon instance limits |
| Reliability | Moderate - depends on bird.makeup staying operational |

### Recommendation for Awesome Aggregator

**Twitter/X has no truly reliable free method.** The realistic options:
1. **RSS-Bridge + Twitter free API tier** - Most reliable but requires a developer account and has a 1,500 tweet/month cap.
2. **Nitter instances** - Free but unreliable. Can be used as a fallback with instance rotation.
3. **bird.makeup via Mastodon RSS** - Creative workaround but adds Mastodon as a dependency.

**Implementation:** Build the adapter with a pluggable backend that can try Nitter first, fall back to RSS-Bridge, and gracefully degrade if both fail.

---
## 4. Instagram

Instagram is extremely hostile to scraping. Meta actively blocks open-source frontends.

### Method A: RSS-Bridge Instagram Bridge (Self-Hosted)

RSS-Bridge includes an Instagram bridge, plus alternative bridges like PicukiBridge and PicnobBridge that scrape third-party Instagram viewers.

**Self-hosted RSS-Bridge:**
```
http://localhost:3000/?action=display&bridge=InstagramBridge&context=Username&u=USERNAME&format=Atom
```

**Important:** The main InstagramBridge requires a working Instagram account cookie for your self-hosted instance. The PicukiBridge and PicnobBridge bridges scrape third-party viewer sites (picuki.com, picnob.com) and may work without auth.

| Attribute | Value |
|-----------|-------|
| Cost | Free (self-hosted) |
| Auth | Instagram session cookie recommended |
| Rate Limit | Instagram blocks aggressively |
| Reliability | LOW - Instagram frequently changes its anti-scraping measures |

### Method B: Proxigram (Self-Hosted Frontend)

Proxigram is an open-source, privacy-focused Instagram frontend. It scrapes data from third-party Instagram viewer sites rather than Instagram directly.

**Features:**
- Browse without JavaScript
- RSS feed support with configurable post limits
- Multiple scraping providers (fallback chain)

**Repo:** https://codeberg.org/proxigram/proxigram

| Attribute | Value |
|-----------|-------|
| Cost | Free (self-hosted) |
| Auth | None |
| Rate Limit | Depends on upstream viewer sites |
| Reliability | LOW-MODERATE - upstream viewers can break at any time |

### Method C: Bibliogram (DEPRECATED)

Bibliogram development has stopped. Instagram blocked its servers and the maintainer gave up. Not recommended.

### Recommendation for Awesome Aggregator

**Instagram integration is high-effort, low-reliability.** If users need it:
1. **RSS-Bridge with PicukiBridge** as the least-maintenance option
2. **Proxigram self-hosted** for richer data but more infrastructure
3. Mark Instagram as experimental / best-effort in the UI

---

## 5. Facebook

Facebook (Meta) removed native RSS feeds years ago and actively blocks scraping.

### Method A: RSS-Bridge Facebook Bridge

RSS-Bridge includes a Facebook bridge for public pages. It scrapes the mobile version of Facebook pages.

**Usage:**
```
http://localhost:3000/?action=display&bridge=FacebookBridge&context=User&u=PAGE_NAME&format=Atom
```

**Major caveat:** Public Facebook pages often redirect to login prompts. This works intermittently. Self-hosting RSS-Bridge on a residential IP (not a datacenter) improves success rate.

| Attribute | Value |
|-----------|-------|
| Cost | Free (self-hosted) |
| Auth | None, but login walls are common |
| Rate Limit | Facebook blocks aggressively |
| Reliability | LOW |

### Recommendation for Awesome Aggregator

**Facebook is the hardest platform to integrate for free.** Realistic approach:
1. RSS-Bridge FacebookBridge as best-effort
2. Clearly mark as experimental with frequent breakage expected
3. Consider deprioritizing Facebook in favor of more reliable sources

---

## 6. LinkedIn

LinkedIn is extremely aggressive against scraping and has taken legal action against scraping services.

### Assessment

**Critical issues:**
- LinkedIn removed work history from public (logged-out) profiles
- LinkedIn uses advanced fingerprinting, behavioral detection, and fraud scoring
- Account bans are common and permanent
- Legal risk: Proxycurl (a major LinkedIn scraping service) was shut down under legal pressure
- LinkedIn does NOT offer RSS feeds for profiles, companies, or posts

| Attribute | Value |
|-----------|-------|
| Reliability | VERY LOW |
| Legal Risk | HIGH - LinkedIn actively litigates |

### Recommendation for Awesome Aggregator

**Do NOT integrate LinkedIn scraping.** The legal risk is real, the data access is poor, and accounts get banned. If users want LinkedIn content, suggest they use LinkedIn native notification emails and route those through the Email/IMAP integration instead.

---
## 7. Email (Gmail / Outlook)

### Method A: IMAP Access (RECOMMENDED)

IMAP is a free, standard protocol for reading email. Both Gmail and Outlook support it with OAuth2 authentication.

**Gmail IMAP:**
- Server: imap.gmail.com, Port: 993 (SSL)
- Auth: OAuth2 (XOAUTH2 SASL mechanism)
- Scope: https://mail.google.com/
- Requires: Google Cloud project with Gmail API enabled (free)

**Outlook/Microsoft 365 IMAP:**
- Server: outlook.office365.com, Port: 993 (SSL)
- Auth: OAuth2 (XOAUTH2 SASL mechanism)
- Requires: Azure AD app registration (free)

**Python implementation:**
```python
import imaplib

# Gmail with OAuth2
imap = imaplib.IMAP4_SSL("imap.gmail.com")
auth_string = f"user={email}auth=Bearer {access_token}"
imap.authenticate("XOAUTH2", lambda x: auth_string.encode())
imap.select("INBOX")
status, messages = imap.search(None, "UNSEEN")
```

**Note:** Google and Microsoft have dropped basic auth (username+password). OAuth2 is now mandatory. The setup requires a one-time OAuth consent flow, but after that, token refresh is automatic.

| Attribute | Value |
|-----------|-------|
| Cost | Free |
| Auth | OAuth2 (one-time setup per user) |
| Rate Limit | Gmail: ~250 IMAP commands/min; Outlook: similar |
| Reliability | Excellent - standards-based protocol |
| Data Access | Full inbox access (read, search, folders) |

### Method B: Email-to-RSS Bridges

Tools like kill-the-newsletter convert email newsletters to RSS feeds by providing a unique email address that forwards to an RSS endpoint.

- **kill-the-newsletter:** https://github.com/leafac/kill-the-newsletter (self-hosted)

| Attribute | Value |
|-----------|-------|
| Cost | Free (self-hosted) |
| Auth | None |
| Reliability | Good |

### Recommendation for Awesome Aggregator

**IMAP with OAuth2 is the gold standard.** It is free, unlimited, standards-based, and gives full inbox access. The OAuth2 setup is a one-time configuration per email provider. Implement a generic IMAP adapter that supports both Gmail and Outlook.

---
## 8. Hacker News

Hacker News is the most developer-friendly platform - everything is free and open.

### Method A: Official Firebase API (Free, No Auth)

The official HN API is hosted on Firebase and requires no authentication.

**Endpoints:**
```
https://hacker-news.firebaseio.com/v0/topstories.json
https://hacker-news.firebaseio.com/v0/newstories.json
https://hacker-news.firebaseio.com/v0/beststories.json
https://hacker-news.firebaseio.com/v0/askstories.json
https://hacker-news.firebaseio.com/v0/showstories.json
https://hacker-news.firebaseio.com/v0/jobstories.json
https://hacker-news.firebaseio.com/v0/item/{id}.json
https://hacker-news.firebaseio.com/v0/user/{username}.json
```

| Attribute | Value |
|-----------|-------|
| Cost | Free |
| Auth | None |
| Rate Limit | None documented |
| Reliability | Excellent - official, maintained by Y Combinator |

### Method B: Algolia HN Search API (Free, No Auth)

Algolia powers the official HN search. Full-text search with filtering and sorting.

**Endpoints:**
```
https://hn.algolia.com/api/v1/search?query=TERM
https://hn.algolia.com/api/v1/search_by_date?query=TERM
https://hn.algolia.com/api/v1/items/{id}
https://hn.algolia.com/api/v1/users/{username}
```

**Filters:** tags=story, tags=comment, tags=ask_hn, numericFilters=points>100

| Attribute | Value |
|-----------|-------|
| Cost | Free |
| Auth | None |
| Rate Limit | ~10,000 requests/hour (generous) |
| Reliability | Excellent |

### Method C: hnrss.org (RSS Feeds)

hnrss.org generates RSS feeds from HN with filtering support. Powered by Algolia.

**Feed URLs:**
```
https://hnrss.org/frontpage
https://hnrss.org/newest
https://hnrss.org/best
https://hnrss.org/ask
https://hnrss.org/show
https://hnrss.org/jobs
https://hnrss.org/newest?q=python
https://hnrss.org/newest?points=100
```

**Format options:** Append .atom for Atom format, .jsonfeed for JSON Feed.
**Default:** 20 items per feed, configurable with count=N (max 100).

| Attribute | Value |
|-----------|-------|
| Cost | Free |
| Auth | None |
| Rate Limit | Standard HTTP politeness |
| Reliability | Excellent |

### Recommendation for Awesome Aggregator

**Use the Firebase API (Method A) as primary** for real-time story lists, and **hnrss.org (Method C)** as an RSS-based alternative for the generic RSS adapter. The Algolia API (Method B) is ideal for search functionality.

---
## 9. GitHub

### Method A: Atom Feeds (Free, No Auth)

GitHub provides native Atom feeds for most resources. No API key needed.

**Feed URLs:**
```
https://github.com/{owner}/{repo}/releases.atom
https://github.com/{owner}/{repo}/commits.atom
https://github.com/{owner}/{repo}/tags.atom
https://github.com/{user}.atom
```

| Attribute | Value |
|-----------|-------|
| Cost | Free |
| Auth | None |
| Rate Limit | None documented for Atom feeds |
| Reliability | Excellent |

### Method B: GitHub REST API (Free with Rate Limits)

The GitHub REST API is free for public data with generous rate limits.

**Unauthenticated:** 60 requests/hour
**Authenticated (personal access token):** 5,000 requests/hour

**Useful endpoints:**
```
GET /users/{username}/events/public
GET /repos/{owner}/{repo}/events
GET /repos/{owner}/{repo}/releases/latest
GET /repos/{owner}/{repo}/commits
```

A free personal access token (PAT) with no special scopes gets you from 60 to 5,000 requests/hour.

| Attribute | Value |
|-----------|-------|
| Cost | Free |
| Auth | None (60/hr) or PAT (5,000/hr) |
| Rate Limit | 60 or 5,000 requests/hour |
| Reliability | Excellent |

### Recommendation for Awesome Aggregator

**Primary:** GitHub Atom feeds for release/commit tracking (zero auth, zero limits).
**Enhanced:** REST API with a free PAT for richer data (5,000 req/hr is plenty).

---

## 10. Twitch

### Method A: Third-Party RSS Services

Twitch does not provide native RSS feeds. Third-party services fill the gap.

**TwitchRSS:**
```
https://twitchrss.appspot.com/vod/{channel_name}
```

**Self-hostable:** https://github.com/lzeke0/TwitchRSS

| Attribute | Value |
|-----------|-------|
| Cost | Free |
| Auth | None |
| Rate Limit | Service-dependent |
| Reliability | Moderate - depends on Twitch not blocking the service |

### Method B: Twitch Helix API (Free Tier)

The Twitch API (Helix) is free to use with OAuth2 app credentials.

**Setup:** Register an application at dev.twitch.tv (free). Get a Client ID + Client Secret.

**Auth:** Client Credentials OAuth flow (app-to-app, no user login needed for public data).

**Useful endpoints:**
```
GET /helix/streams?user_login={channel}
GET /helix/videos?user_id={id}&type=archive
GET /helix/channels?broadcaster_id={id}
GET /helix/schedule?broadcaster_id={id}
```

**Rate limits:**
- Without Bearer token: 30 requests/minute
- With Bearer token: 120 requests/minute (800 points bucket)

| Attribute | Value |
|-----------|-------|
| Cost | Free |
| Auth | OAuth2 Client Credentials (free registration) |
| Rate Limit | 120 req/min with auth token |
| Reliability | Excellent - official API |

### Recommendation for Awesome Aggregator

**Use the Twitch Helix API (Method B).** Registration is free, the API is well-documented, and 120 requests/minute is generous. Use TwitchRSS as a no-auth fallback for simple VOD tracking.

---
## 11. Discord

### Important Limitation

Discord is designed as a real-time chat platform, NOT a content feed. Integrating it requires a fundamentally different approach than RSS-based sources.

### Method A: Discord Bot (Free, Read Messages)

A Discord bot can read messages in any server it has been invited to, with appropriate permissions.

**Setup:**
1. Create a bot at discord.com/developers (free)
2. Enable MESSAGE_CONTENT intent (required for reading message text)
3. Invite the bot to target servers with Read Messages permission
4. Connect via WebSocket (Gateway) to receive real-time messages

**Python library:** discord.py or nextcord

**Rate limits:** 50 requests/second globally for the bot. Gateway WebSocket is persistent (no polling needed).

**Key limitation:** The bot must be explicitly invited to each server. Users cannot read arbitrary servers.

| Attribute | Value |
|-----------|-------|
| Cost | Free |
| Auth | Bot token (free registration) |
| Rate Limit | 50 req/sec |
| Reliability | Excellent - official API |
| Limitation | Bot must be invited to each server |

### Method B: Webhooks (Send Only - NOT Useful for Reading)

Discord webhooks are **outbound only** - they can send messages TO Discord but cannot read FROM Discord. Not useful for content aggregation.

### Recommendation for Awesome Aggregator

**Discord bot (Method A)** is the only free way to read Discord content. The adapter needs to maintain a persistent WebSocket connection (different from the poll-based model of other sources). Consider making this an advanced integration given the complexity.

---

## 12. News Sites

### Method A: Native RSS Feeds (RECOMMENDED)

Most major news sites still provide RSS feeds. This is the most reliable, free, and unlimited method.

**Common RSS feed locations:**
```
https://www.nytimes.com/sectionName/rss.xml
https://feeds.bbci.co.uk/news/rss.xml
https://rss.cnn.com/rss/cnn_topstories.rss
https://feeds.reuters.com/reuters/topNews
https://www.theguardian.com/world/rss
https://techcrunch.com/feed/
https://www.wired.com/feed/rss
https://arstechnica.com/feed/
```

| Attribute | Value |
|-----------|-------|
| Cost | Free |
| Auth | None |
| Rate Limit | None (standard HTTP caching via ETags/Last-Modified) |
| Reliability | Excellent |

### Method B: Google News RSS

Google News provides aggregated news RSS feeds with topic and keyword filtering.

**Feed URLs:**
```
https://news.google.com/rss
https://news.google.com/rss/search?q=KEYWORD
```

**Limitation:** Article URLs point to Google redirects rather than the original source. You need to follow the redirect to get the actual article URL.

| Attribute | Value |
|-----------|-------|
| Cost | Free |
| Auth | None |
| Rate Limit | None documented |
| Reliability | Good |

### Method C: NewsAPI.org Free Tier (CAPPED - Not Recommended)

newsapi.org offers a free tier but with significant limitations:
- **100 requests/day** only
- Articles delayed by 24 hours
- No SLA
- **NOT unlimited** - violates our requirements

**Better free alternatives (still capped but higher limits):**
- **NewsData.io:** 200 credits/day, 89+ languages
- **World News API:** 500 requests/day
- **Finlight.me:** 10,000 requests/month (financial news focus)

These are all capped and therefore **not recommended as primary** methods, but can supplement RSS feeds for search/discovery.

### Recommendation for Awesome Aggregator

**Primary:** Native RSS feeds from news sites. The existing backend/sources/rss.py adapter handles this perfectly.
**Supplementary:** Google News RSS for topic-based aggregation and discovery.
**Avoid:** Paid/capped news APIs as primary sources. Use them only for search if needed.

---
## 13. Summary Matrix

| Platform | Best Method | Cost | Auth Required | Rate Limit | Reliability | Priority |
|----------|------------|------|---------------|------------|-------------|----------|
| **YouTube** | RSS feeds | Free | None | None | Excellent | P0 |
| **Reddit** | .rss / .json | Free | None | 10 req/min (.json) | Excellent | P0 |
| **Hacker News** | Firebase API | Free | None | None | Excellent | P0 |
| **GitHub** | Atom feeds | Free | None | None | Excellent | P0 |
| **News Sites** | RSS feeds | Free | None | None | Excellent | P0 |
| **Email** | IMAP/OAuth2 | Free | OAuth2 setup | ~250 cmd/min | Excellent | P1 |
| **Twitch** | Helix API | Free | OAuth2 app | 120 req/min | Excellent | P1 |
| **Discord** | Bot API | Free | Bot token | 50 req/sec | Excellent | P2 |
| **Twitter/X** | Nitter/RSS-Bridge | Free | Varies | Varies | LOW | P2 |
| **Instagram** | RSS-Bridge/Proxigram | Free | Session cookie | Aggressive blocking | LOW | P3 |
| **Facebook** | RSS-Bridge | Free | None | Aggressive blocking | LOW | P3 |
| **LinkedIn** | N/A | N/A | N/A | N/A | DO NOT INTEGRATE | P4 |

### Priority Legend
- **P0:** Implement first. Free, unlimited, reliable, zero auth.
- **P1:** Implement second. Free but requires one-time OAuth/API setup.
- **P2:** Implement third. Free but reliability concerns.
- **P3:** Experimental. High breakage rate, mark as beta in UI.
- **P4:** Skip. Legal risk or no viable free method.

---

## 14. Meta-Platform: RSSHub (Game Changer)

**RSSHub is the single most important discovery for this project.** It is an open-source RSS feed generator with 41.8K GitHub stars, 5,000+ global instances, and routes covering 1,000+ content sources. It turns virtually any website into an RSS feed.

**Repo:** https://github.com/DIYgod/RSSHub
**Docs:** https://docs.rsshub.app
**License:** MIT

### What RSSHub Changes

RSSHub provides a **unified RSS interface** for nearly every platform we need. Instead of building custom adapters for Twitter, Instagram, Discord, etc., we can route requests through a self-hosted RSSHub instance and consume standard RSS feeds from all of them.

### Supported Platform Routes

| Platform | RSSHub Route | Auth Required |
|----------|-------------|---------------|
| **Twitter/X** | /twitter/user/:id | TWITTER_AUTH_TOKEN or username/password |
| **Twitter/X media** | /twitter/media/:id | Same as above |
| **Twitter/X search** | /twitter/keyword/:keyword | Same as above |
| **Instagram** | /instagram/:category/:key | Instagram cookie |
| **YouTube channel** | /youtube/channel/:id | None |
| **YouTube user** | /youtube/user/:username | None |
| **YouTube playlist** | /youtube/playlist/:id | None |
| **Discord channel** | /discord/channel/:channelId | DISCORD_AUTHORIZATION token |
| **Facebook page** | /facebook/page/:id | None (may be unreliable) |
| **Mastodon user** | /mastodon/acct/:acct/statuses | None |
| **Mastodon timeline** | /mastodon/timeline/:site | None |
| **Telegram channel** | /telegram/channel/:username | None |
| **GitHub repos** | /github/repos/:user | None |
| **GitHub issues** | /github/issue/:user/:repo | None |
| **GitHub stars** | /github/starred_repos/:user | None |
| **Hacker News** | /hackernews/:section | None |
| **Reddit** | /reddit/subreddit/:subreddit | None |
| **Spotify** | /spotify/artist/:id | SPOTIFY credentials |
| **Twitch** | /twitch/live/:login | None |
| **TikTok** | /tiktok/user/:user | None |
| **Pinterest** | /pinterest/user/:user | None |
| **Bilibili** | /bilibili/user/video/:uid | None |
| **SoundCloud** | /soundcloud/tracks/:user | None |

### Deployment

Single Docker container:
```bash
docker run -d --name rsshub -p 1200:1200 diygod/rsshub
```

Or with Docker Compose:
```yaml
services:
  rsshub:
    image: diygod/rsshub
    restart: always
    ports:
      - "1200:1200"
    environment:
      # Twitter (optional)
      TWITTER_AUTH_TOKEN: "your_token"
      # Instagram (optional)
      IG_COOKIE: "your_cookie"
      # Discord (optional)
      DISCORD_AUTHORIZATION: "your_token"
      # Cache settings
      CACHE_TYPE: memory
      CACHE_EXPIRE: 300
```

### Rate Limits

- Self-hosted: **No rate limits** (you control the instance)
- Built-in caching reduces upstream requests
- Public instances (rsshub.app): Rate limited, not recommended for production

### How This Changes Our Architecture

With RSSHub self-hosted, the Awesome Aggregator adapter strategy simplifies dramatically:

1. **Generic RSS adapter** handles ALL RSSHub-backed platforms (YouTube, Reddit, HN, GitHub, Twitch, TikTok, Pinterest, etc.)
2. **RSSHub-Twitter adapter** = generic RSS pointed at /twitter/user/:id route
3. **RSSHub-Instagram adapter** = generic RSS pointed at /instagram/:category/:key route
4. **RSSHub-Discord adapter** = generic RSS pointed at /discord/channel/:channelId route

Instead of building 12+ custom adapters, we build **one RSSHub-aware RSS adapter** that constructs the correct route URL and passes platform-specific auth tokens from config.

| Attribute | Value |
|-----------|-------|
| Cost | Free (self-hosted, MIT license) |
| Auth | Per-platform (some routes need tokens, many need none) |
| Rate Limit | None (self-hosted) |
| Reliability | Excellent for zero-auth routes; platform-dependent for auth routes |
| Stars | 41.8K on GitHub |
| Status | Actively maintained as of Feb 2026 |

---

## 15. Meta-Platform: RSS-Bridge (Complementary)

RSS-Bridge is a PHP-based self-hosted tool that generates RSS/Atom feeds for 200+ platforms. It complements RSSHub by covering some sites RSSHub does not.

**Repo:** https://github.com/RSS-Bridge/rss-bridge
**License:** Unlicense (public domain)

### Deployment

```bash
docker run -d --name rss-bridge -p 3000:80 rssbridge/rss-bridge
```

### Key Differences from RSSHub

| Aspect | RSSHub | RSS-Bridge |
|--------|--------|------------|
| Language | JavaScript (Node.js) | PHP |
| Routes/Bridges | 5,000+ routes | 200+ bridges |
| GitHub Stars | 41.8K | 7.4K |
| Resource Usage | Moderate (Node.js) | Lightweight (PHP) |
| Auth Handling | Per-route env vars | Per-bridge config |
| API Style | URL path routes | Query parameter bridges |

### Recommendation

**Deploy both.** RSSHub as primary (more routes, more actively maintained), RSS-Bridge as fallback (lighter, covers some niche sites RSSHub misses). Both run as single Docker containers with minimal resources.

---
## Revised Architecture Notes

### The RSSHub-First Strategy

The discovery of RSSHub fundamentally changes our integration approach. Instead of building custom adapters per platform, we deploy RSSHub as middleware and consume its standardized RSS output.

**Before (custom adapters per platform):**
```
YouTube  --> YouTube RSS Adapter
Reddit   --> Reddit .json Adapter
Twitter  --> Nitter/RSS-Bridge Adapter
HN       --> Firebase API Adapter
Instagram --> RSS-Bridge Adapter
Discord  --> Discord Bot Adapter (WebSocket)
...12+ custom adapters
```

**After (RSSHub-first):**
```
All platforms ----> RSSHub Instance ----> Generic RSS Adapter ----> Awesome Aggregator
(YouTube, Reddit, Twitter,                                               |
 HN, Instagram, Discord,                                                 |
 Twitch, TikTok, etc.)               Direct RSS (native feeds) --------->+
                                     IMAP/Email (Gmail, Outlook) ------->|
```

### Revised Adapter Implementation Order

1. **Generic RSS/Atom adapter** (already built) - handles native feeds AND RSSHub output
2. **RSSHub deployment** - Docker container, configure platform auth tokens
3. **Reddit .json adapter** (already built) - keep for richer data than RSS provides
4. **Hacker News adapter** - Firebase API for real-time, RSSHub as RSS fallback
5. **Email/IMAP adapter** - OAuth2 setup (cannot be RSS-ified)
6. **Discord bot adapter** - for real-time chat (RSSHub covers message history only)

### Revised Summary Matrix

| Platform | Primary Method | Fallback | Auth | Reliability | Priority |
|----------|---------------|----------|------|-------------|----------|
| **YouTube** | Native RSS | RSSHub | None | Excellent | P0 |
| **Reddit** | .rss / .json | RSSHub | None | Excellent | P0 |
| **Hacker News** | Firebase API | RSSHub/hnrss | None | Excellent | P0 |
| **GitHub** | Atom feeds | RSSHub | None | Excellent | P0 |
| **News Sites** | Native RSS | Google News RSS | None | Excellent | P0 |
| **Twitch** | RSSHub | Helix API | None via RSSHub | Good | P1 |
| **Mastodon** | RSSHub | Native RSS | None | Good | P1 |
| **Email** | IMAP/OAuth2 | N/A | OAuth2 | Excellent | P1 |
| **Twitter/X** | RSSHub | Nitter/RSS-Bridge | Auth token | Moderate | P2 |
| **Discord** | RSSHub (history) | Bot (real-time) | Auth token | Moderate | P2 |
| **Instagram** | RSSHub | RSS-Bridge | Cookie | Low | P3 |
| **Facebook** | RSSHub | RSS-Bridge | None | Low | P3 |
| **Spotify** | RSSHub | N/A | Credentials | Moderate | P3 |
| **TikTok** | RSSHub | N/A | None | Moderate | P3 |
| **LinkedIn** | N/A | N/A | N/A | DO NOT INTEGRATE | P4 |

### Docker Compose for Full Stack

```yaml
# docker-compose.yml - Awesome Aggregator infrastructure
services:
  aggregator-backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - rsshub
      - rss-bridge

  rsshub:
    image: diygod/rsshub
    restart: always
    ports:
      - "1200:1200"
    environment:
      CACHE_TYPE: memory
      CACHE_EXPIRE: 300
      # Add platform tokens as needed:
      # TWITTER_AUTH_TOKEN: "..."
      # IG_COOKIE: "..."
      # DISCORD_AUTHORIZATION: "..."

  rss-bridge:
    image: rssbridge/rss-bridge
    restart: always
    ports:
      - "3000:80"
```

This gives us a **three-container stack** that covers 1,000+ content sources through standardized RSS feeds.

---

*Last updated: 2026-02-12*
*Research conducted by: The Scout (platform-researcher agent)*
*Updated with RSSHub (41.8K stars) and RSS-Bridge findings from OSS research team*
