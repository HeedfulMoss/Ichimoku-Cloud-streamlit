# Ichimoku Cloud Application

A microservice-based application for visualizing Ichimoku Cloud technical indicators for stock tickers with multiple frontend options.

## Project Architecture

```
Ichimoku-Cloud-Application/
├── README.md                   # Project documentation
├── docker-compose.yml          # Docker Compose configuration
├── .dockerignore               # Files to ignore in Docker builds
├── .gitignore                  # Files to ignore in Git
├── Makefile                    # Automation commands (optional)
├── streamlit-frontend/         # Streamlit frontend service
│   ├── Dockerfile              # Streamlit Docker configuration
│   ├── requirements.txt        # Streamlit dependencies
│   ├── app/                    # Streamlit application code
│   │   ├── __init__.py         # Package initialization
│   │   ├── Homepage.py         # Main Streamlit page
│   │   ├── charts.py           # Chart rendering logic
│   └── k8s/                    # Kubernetes manifests for Streamlit
│       ├── streamlit-deployment.yaml
│       └── streamlit-service.yaml
├── react-frontend/             # React/HTML frontend service
│   ├── Dockerfile              # React frontend Docker configuration
│   ├── index.html              # React/HTML application
│   └── k8s/                    # Kubernetes manifests for React
│       ├── react-deployment.yaml
│       └── react-service.yaml
└── backend/                    # FastAPI backend service
    ├── Dockerfile              # Backend Docker configuration
    ├── requirements.txt        # Backend dependencies
    ├── app/                    # Backend application code
    │   ├── main.py             # FastAPI entrypoint
    │   ├── data_fetch.py       # Data fetching service
    │   ├── ichimoku.py         # Ichimoku calculation logic
    └── k8s/                    # Kubernetes manifests for backend
        ├── backend-deployment.yaml
        └── backend-service.yaml
```

## Project Description

This application provides an interactive visualization of Ichimoku Cloud technical indicators for stock tickers. The Ichimoku Cloud is a popular technical analysis tool that helps traders identify trend direction, momentum, and potential support/resistance levels.

The project is structured as a microservice application with:

1. **Streamlit Frontend**: Provides a user interface where users can:
   - Input stock ticker symbols
   - Adjust Ichimoku Cloud parameters
   - View the resulting chart with candlesticks, volume, and Ichimoku Cloud indicators

2. **Backend (FastAPI)**: Handles data processing:
   - Fetches historical stock data from Yahoo Finance
   - Performs Ichimoku Cloud calculations
   - Provides data to the frontend via REST API
   - Endpoints: `/data/{ticker}` (GET) and `/ichimoku` (POST)  

3. **React Frontend**: JavaScript/HTML-based interface:
   - Native HTML/CSS interface with interactive controls
   - Uses lightweight-charts library directly
   - Synchronized dual-pane layout (main chart + volume)
   - Complete Ichimoku Cloud visualization with proper chart interactions

## Project Explanation:

- **Frontend**:
  - `Homepage.py`: Main Streamlit interface that handles user input and displays the chart
  - `charts.py`: Contains the logic for rendering charts using streamlit_lightweight_charts

- **Backend**:
  - `main.py`: FastAPI application entry point
  - `data_fetch.py`: Service to fetch ticker data from Yahoo Finance
  - `ichimoku.py`: Service that calculates Ichimoku Cloud indicators

### Access the Applications
- **React Frontend**: http://localhost:3000
- **Streamlit Frontend**: http://localhost:8501  
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## How to Run:

### Running with Kubernetes (current)

Follow these steps from the project root to build your images and deploy both services into your local Kubernetes cluster:

#### 1. Build Docker Images
Use your existing Docker Compose file to build both services

```bash
docker-compose build
```

This will produce two local images tagged:

```
ichimoku-cloud-streamlit-backend:latest
ichimoku-cloud-streamlit-streamlit-frontend:latest
ichimoku-cloud-streamlit-react-frontend:latest
```

#### 2. Deploy to Kubernetes

```bash
kubectl apply -f backend/k8s/ -f streamlit-frontend/k8s/ -f react-frontend/k8s/
```

#### 4. Stop the Kubernetes Deployment
 Tear down both frontend and backend resources

```bash
kubectl delete -f backend/k8s/ -f streamlit-frontend/k8s/ -f react-frontend/k8s/
```

### Using just Docker

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

### Docker Commands Reference

#### Build and Start Services
```bash
docker-compose up
```

#### Build and Start Services in Detached Mode
```bash
docker-compose up -d
```

#### Stop Services
```bash
docker-compose down
```

#### Rebuild Services
```bash
docker-compose up --build
```

#### View Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs react-frontend
docker-compose logs streamlit-frontend
docker-compose logs backend
```

### Debug Commands

```bash
# Check Docker containers
docker ps
docker logs <container-name>

# Check Kubernetes resources
kubectl get all
kubectl describe pod <pod-name>
kubectl logs <pod-name>

# Test API connectivity
curl http://localhost:8000/data/AAPL
```


## Technical Background

The Ichimoku Cloud (or Ichimoku Kinko Hyo) consists of five components:

1. **Tenkan-sen (Conversion Line)**: (9-period high + 9-period low)/2
2. **Kijun-sen (Base Line)**: (26-period high + 26-period low)/2
3. **Senkou Span A (Leading Span A)**: (Tenkan-sen + Kijun-sen)/2, plotted 26 periods ahead
4. **Senkou Span B (Leading Span B)**: (52-period high + 52-period low)/2, plotted 26 periods ahead
5. **Chikou Span (Lagging Span)**: Close price, plotted 26 periods behind

The area between Senkou Span A and B is called the "cloud" or "kumo". When Span A is above Span B, the cloud is bullish (green). When Span B is above Span A, the cloud is bearish (red).

The "cloud" (kumo) is the area between Senkou Spans A and B:
- **Bullish Cloud**: When Span A > Span B → green cloud → uptrend
- **Bearish Cloud**: When Span B > Span A → red cloud → downtrend

## Continuous Integration with GitHub Actions

We use GitHub Actions to automatically build both Docker images on every push or pull request to `main`, ensuring the Dockerfiles remain valid.

### Steps

**Workflow**: `.github/workflows/docker-image-build.yml`
- **Triggers**: `push` and `pull_request` events on the `main` branch
- **Checkout your code** (`actions/checkout@v3`)
- **Set up Buildx** (`docker/setup-buildx-action@v2`)
- **Build backend image**
    - Context: `./backend`
    - Dockerfile: `backend/Dockerfile`
    - Tag: `ichimoku-cloud-streamlit-backend:latest`
    - `push: false` (build-only)
- **Build streamlit-frontend image**
    - Context: `./streamlit-frontend`
    - Dockerfile: `streamlit-frontend/Dockerfile`
    - Tag: `ichimoku-cloud-streamlit-streamlit-frontend:latest`
    - `push: false`
- **Build react-frontend image**
    - Context: `./react-frontend`
    - Dockerfile: `react-frontend/Dockerfile`
    - Tag: `ichimoku-cloud-react-frontend:latest`
    - `push: false`
- **Validation**: Ensures Dockerfiles build successfully

### How to enable
- Commit and push the workflow file:
  ```bash
  git add .github/workflows/docker-image-build.yml
  git commit -m "ci: Add Docker image build workflow"
  git push origin main
- View results on your repo's Actions tab.

### What it tests
- Verifies that both backend/Dockerfile and frontend/Dockerfile build successfully—catching syntax errors, missing files, or broken build steps before you merge code.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test locally
4. Ensure Docker builds succeed
5. Test Kubernetes deployment
6. Submit a pull request

## License

[Add your license information here]