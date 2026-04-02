# Poshmark Auto-Share & Offer Bot

A free, local web app that automatically shares your Poshmark listings and sends offers to likers.

## Features

- **Auto-Share** - Shares all your active listings on a schedule with configurable speed
- **Auto-Offer** - Detects new likes and sends offers automatically
- **Dashboard** - Browser-based UI to configure settings and monitor activity
- **Configurable** - Set share speed, offer discount %, minimum price, and more

## Setup

### 1. Install Python 3.8+

Download from [python.org](https://www.python.org/downloads/) if not already installed.

### 2. Install dependencies

```bash
cd poshmark-bot
pip install -r requirements.txt
```

### 3. Run the app

```bash
python app.py
```

### 4. Open the dashboard

Go to **http://localhost:5000** in your browser.

### 5. Log in

Enter your Poshmark username/email and password in the dashboard.

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

- Your credentials are only sent to Poshmark and stored locally as session cookies
- The SQLite database (`poshmark_bot.db`) is created in the app directory and excluded from git
- Poshmark may rate-limit or restrict accounts using automation - use reasonable delays
