# Project Libertad: Telegram Scraper & Distributor

![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)
![Deployment](https://img.shields.io/badge/deploy-Docker-blue)

**Project Libertad** is a dual-purpose Python application designed for community support and information dissemination during periods of internet restriction. It consists of two main, independent components:

1.  **Proxy Scraper & Notifier**: A continuously running, Dockerized service that monitors public Telegram channels for new proxy links, categorizes them, and distributes them via email and a designated Telegram group.
2.  **SSH Credential Distributor**: A one-time, manually-run script that securely distributes unique SSH credentials from an Excel file to each member of a specific Telegram group via private message.

---

## 1. Component: Proxy Scraper & Notifier (`main.py`)

This is the primary, production-ready component of the project. It runs 24/7 as a service to provide a constant stream of fresh proxy links.

### Core Features

- **Automated Scraping**: Monitors a list of public Telegram channels every 8 hours.
- **Intelligent Fetching**: Always re-scans the last 8 hours of messages on every run to ensure no links from failed cycles are missed.
- **Multi-Protocol Support**: Extracts and categorizes MTProto, VLESS, VMess, and Shadowsocks links.
- **Dual Notification System**:
  - **Email**: Sends a formatted email with a supportive message, categorized proxy lists as `.txt` attachments, and a PDF guide.
  - **Telegram Group**: Posts a clean, formatted summary of new links to a designated group, embedding MTProto links for brevity.
- **Stateless & Deployable**: Designed to be deployed as a Docker container on any cloud platform (e.g., RunonFlux) using persistent volumes for state.

### Tech Stack

- **Language**: Python 3.9+
- **Libraries**: Telethon, python-dotenv
- **Containerization**: Docker

### Deployment Instructions

This service is designed to be deployed as a Docker container.

#### Step 1: Prepare Configuration Files

1.  **`.env` File**: Create a `.env` file from the `env.example` template and fill it with your credentials. **Do not commit this file to Git.**
2.  **`emails.txt`**: Add your list of recipient emails, one per line.
3.  **`emergency_guide.pdf`**: Place the PDF guide file (e.g., `در صورت وقوع بحران یا جنگ.pdf`) in the root directory and update its name in the `.env` file if needed.

#### Step 2: Build the Docker Image

Build and tag the image for Docker Hub. Replace `yourdockerhubusername` with your actual username.
```bash
docker build -t yourdockerhubusername/project-libertad-scraper:latest .