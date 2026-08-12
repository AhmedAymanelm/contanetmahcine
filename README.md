# Content Machine

Content Machine is an automated AI-driven platform for aggregating, generating, and publishing news content across multiple social media platforms. It acts as an intelligent newsroom that fetches news from RSS feeds, rewrites it using AI (Anthropic Claude), and publishes it in various formats (Text Posts, Carousels, Video Scripts) to platforms like Facebook, Instagram, LinkedIn, X (Twitter), TikTok, and Threads.

## Architecture

The project is divided into two main components:

1.  **Backend (FastAPI, Python)**: Handles data ingestion, AI processing, database management, and social media API integrations.
2.  **Frontend (Vanilla HTML/CSS/JS)**: A modern, responsive dashboard for reviewing generated content, managing templates, and monitoring analytics.

## Features

### 1. Automated News Ingestion
*   Fetches news articles from predefined RSS feeds automatically via a scheduled background worker.
*   Extracts the full text, title, and cover image of the raw articles.
*   Categorizes and stores raw articles in the database.

### 2. AI Content Generation
*   Uses **Anthropic's Claude 3.5 Sonnet** (via the `anthropic` library) to process raw articles.
*   Can generate three distinct types of content:
    *   **POST**: A unified, engaging text post suitable for Facebook, LinkedIn, X, and Threads.
    *   **CAROUSEL**: A series of slides (text + title) designed for Instagram and LinkedIn document posts. Includes dynamic image rendering via Playwright to generate the actual slide images.
    *   **VIDEO_SCRIPT**: A structured script (Hook, Body, Call to Action) intended for TikTok, Instagram Reels, and YouTube Shorts.
*   Analyzes the article to determine the most suitable content types and the best platforms to publish them on.

### 3. Review and Approval Dashboard (Frontend)
*   A centralized web interface where users can view all pending AI-generated content.
*   Content is grouped by the original news article, showing all generated variations (Post, Carousel, Script) side-by-side.
*   Features a **Preview Modal** that accurately simulates how the post will look natively on each specific social platform (Facebook, Instagram, X, TikTok, Threads, LinkedIn) before publishing.
*   Includes a dark/light mode toggle for better accessibility.

### 4. Multi-Platform Publishing
*   Direct API integrations to publish approved content to:
    *   **Facebook** (Pages API)
    *   **Instagram** (Graph API - Images and Carousels)
    *   **LinkedIn** (UGC Posts - Text, Images, and Document/PDF Carousels)
    *   **X / Twitter** (v2 API for text, v1.1 for media uploads)
    *   **Threads** (Threads API)
    *   **TikTok** (Drafts/Direct Post API)
*   Supports attaching the raw article's image automatically for platforms that require or benefit from visual media (like Instagram and Facebook).

### 5. Automation and Scheduling
*   Users can "Approve and Publish Now" or schedule posts for a specific time in the future.
*   A background task runner checks the schedule every minute to publish queued content exactly when required.

## Tech Stack

*   **Backend**: Python, FastAPI, SQLAlchemy, PostgreSQL (Neon), Playwright (for Carousel rendering), Tweepy, HTTPX.
*   **Frontend**: HTML5, CSS3, Vanilla JavaScript, Swiper.js (for carousel previews), Flatpickr (for scheduling).
*   **AI Integration**: Anthropic Claude API.
*   **Deployment**: Railway (Platform as a Service).

## Setup and Installation

### Prerequisites
*   Python 3.10+
*   PostgreSQL database (local or cloud like Neon)
*   Various API Keys (Anthropic, Facebook/Instagram, Twitter, LinkedIn, etc.)

### Environment Variables
Create a `.env` file in the root directory and configure the necessary keys based on `.env.example`.

### Running Locally
1.  Navigate to the `backend` directory.
2.  Install dependencies: `pip install -r requirements.txt`
3.  Run database migrations: `alembic upgrade head`
4.  Start the FastAPI server: `uvicorn app.main:app --reload`
5.  Access the frontend by opening `frontend/index.html` in a local web server (or via the backend's static file serving if configured).

## Project Structure

*   `backend/app/`: Core FastAPI application.
    *   `ai/`: Logic for interacting with Claude and generating content.
    *   `api/`: REST API routers (endpoints).
    *   `models/`: SQLAlchemy database models.
    *   `services/`: Business logic (Social media integration, ingestion, scheduling).
    *   `workers/`: Background tasks for fetching news and publishing scheduled content.
*   `frontend/`: Static assets for the dashboard.
    *   `css/`: Stylesheets including theme variables.
    *   `js/`: Vanilla JS logic for the dashboard features.
    *   `index.html`: Main dashboard entry point.
