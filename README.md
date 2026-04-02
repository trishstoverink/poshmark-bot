# Poshmark Auto-Share & Offer Bot

A local web app that automatically shares your Poshmark listings and sends offers to likers. Runs on your own computer with a browser-based dashboard.

## Features

- **Auto-Share** - Shares all your active listings on a schedule with configurable speed
- **Auto-Offer** - Detects new likes and sends offers automatically
- **Dashboard** - Browser-based UI to configure settings and monitor activity
- **Configurable** - Set share speed, offer discount %, minimum price, and more
- **User Accounts** - Login system with admin user management
- **Anti-Detection** - Uses undetected-chromedriver to avoid Poshmark bot detection

## Requirements

- **Python 3.8+** - [Download here](https://www.python.org/downloads/)
- **Google Chrome** - Must be installed on your computer

## Setup

```bash
cd poshmark-bot
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5000** in your browser.

## First Time Setup

1. Open http://localhost:5000
2. Create your admin account (first account is automatically admin)
3. Connect your Poshmark account (email + password)
4. If Poshmark requires email verification, enter the code when prompted
5. Configure share speed, offer %, and other settings
6. Click Start!

## Settings

### Auto-Share
| Setting | Description | Default |
|---------|-------------|---------|
| Min delay | Minimum seconds between shares | 5s |
| Max delay | Maximum seconds between shares | 10s |
| Cycle interval | How often to run a full share cycle | 2 hours |
| Share order | Random, Newest First, or Oldest First | Random |

### Auto-Offer
| Setting | Description | Default |
|---------|-------------|---------|
| Discount % | Percentage off listing price | 20% |
| Min price | Won't send offers below this | $5 |
| Check interval | How often to check for new likes | 15 min |
| Shipping discount | Offer discounted shipping | Yes |

## Notes

- Runs locally on your computer only — not hosted in the cloud
- Uses your real Chrome browser in headless mode (invisible)
- Your Poshmark credentials are only sent to Poshmark, never stored in plain text
- Keep the terminal window open while the bot is running
- Use reasonable share delays (5-10s+) to avoid Poshmark rate limiting
