# Ichimoku Cloud Streamlit

A microservice-based application for visualizing Ichimoku Cloud technical indicators for stock tickers.

## Project Architecture

```
Ichimoku-Cloud-streamlit/
├── README.md                   # Project documentation
├── docker-compose.yml          # Docker compose configuration
├── .dockerignore               # Files to ignore in Docker
├── .gitignore                  # Files to ignore in Git
├── frontend/                   # Streamlit frontend
│   ├── Dockerfile              # Frontend Docker configuration
│   ├── requirements.txt        # Frontend dependencies
│   ├── app/                    # Frontend application code
│   │   ├── __init__.py         # Package initialization
│   │   ├── Homepage.py         # Main Streamlit page
│   │   ├── charts.py           # Chart rendering logic
│   
├── backend/                    # FastAPI backend
│   ├── Dockerfile              # Backend Docker configuration
│   ├── requirements.txt        # Backend dependencies
│   ├── app/                    # Backend application code
│   │   ├── main.py             # FastAPI main file
│   │   ├── data_fetch.py   # Data fetching service
│   │   ├── ichimoku.py     # Ichimoku calculations
```

## Project Description

This application provides an interactive visualization of Ichimoku Cloud technical indicators for stock tickers. The Ichimoku Cloud is a popular technical analysis tool that helps traders identify trend direction, momentum, and potential support/resistance levels.

The project is structured as a microservice application with:

1. **Frontend (Streamlit)**: Provides a user interface where users can:
   - Input stock ticker symbols
   - Adjust Ichimoku Cloud parameters
   - View the resulting chart with candlesticks, volume, and Ichimoku Cloud indicators

2. **Backend (FastAPI)**: Handles data processing:
   - Fetches historical stock data from Yahoo Finance
   - Performs Ichimoku Cloud calculations
   - Provides data to the frontend via REST API

### Key Files Explanation:

- **Frontend**:
  - `Homepage.py`: Main Streamlit interface that handles user input and displays the chart
  - `charts.py`: Contains the logic for rendering charts using streamlit_lightweight_charts
  - `api_client.py`: Client for communicating with the backend API

- **Backend**:
  - `main.py`: FastAPI application entry point
  - `routers/tickers.py`: Defines API endpoints for ticker data
  - `services/data_fetch.py`: Service to fetch ticker data from Yahoo Finance
  - `services/ichimoku.py`: Service that calculates Ichimoku Cloud indicators

## How to Run

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/HeedfulMoss/Ichimoku-Cloud-streamlit.git
cd Ichimoku-Cloud-streamlit
```

2. Start the application using Docker Compose:
```bash
docker-compose up
```

3. Open your browser and navigate to:
```
http://localhost:8501
```

This will start both the frontend and backend services with proper network configuration.

### Manual Setup (For Development)

#### Backend

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the FastAPI application:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Frontend

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the Streamlit application:
```bash
streamlit run app/Homepage.py
```

4. Open your browser and navigate to:
```
http://localhost:8501
```

## Docker Commands Reference

### Build and Start Services
```bash
docker-compose up
```

### Build and Start Services in Detached Mode
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### Rebuild Services
```bash
docker-compose up --build
```

### View Logs
```bash
docker-compose logs
```

### View Logs for a Specific Service
```bash
docker-compose logs frontend
docker-compose logs backend
```

## Technical Background

The Ichimoku Cloud (or Ichimoku Kinko Hyo) consists of five components:

1. **Tenkan-sen (Conversion Line)**: (9-period high + 9-period low)/2
2. **Kijun-sen (Base Line)**: (26-period high + 26-period low)/2
3. **Senkou Span A (Leading Span A)**: (Tenkan-sen + Kijun-sen)/2, plotted 26 periods ahead
4. **Senkou Span B (Leading Span B)**: (52-period high + 52-period low)/2, plotted 26 periods ahead
5. **Chikou Span (Lagging Span)**: Close price, plotted 26 periods behind

The area between Senkou Span A and B is called the "cloud" or "kumo". When Span A is above Span B, the cloud is bullish (green). When Span B is above Span A, the cloud is bearish (red).
