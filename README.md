# Ichimoku Cloud Application

A **security-hardened** microservice application for visualizing Ichimoku Cloud technical indicators with AWS Lambda data collection, S3 storage, and enterprise-grade security features.

## 🏗️ Project Architecture

```
Ichimoku-Cloud-Application/
├── README.md                   # Project documentation
├── docker-compose.yml          # Docker Compose configuration
├── .dockerignore               # Files to ignore in Docker builds
├── .gitignore                  # Files to ignore in Git
├── k8s_setup_script.sh         # Automated Kubernetes deployment
├── k8s_cleanup_script.sh       # Automated cleanup script
├── .env                        # Environment variables (AWS credentials)
├── streamlit-frontend/         # Streamlit frontend service
│   ├── Dockerfile              # Streamlit Docker configuration
│   ├── requirements.txt        # Streamlit dependencies
│   ├── app/                    # Streamlit application code
│   │   ├── __init__.py         # Package initialization
│   │   ├── Homepage.py         # Main Streamlit page (with Lambda UI)
│   │   ├── charts.py           # Chart rendering logic
│   └── k8s/                    # Kubernetes manifests for Streamlit
│       ├── streamlit-deployment.yaml
│       └── streamlit-service.yaml
├── react-frontend/             # React/HTML frontend service
│   ├── Dockerfile              # React frontend Docker configuration
│   ├── index.html              # React/HTML application (with Lambda UI)
│   └── k8s/                    # Kubernetes manifests for React
│       ├── react-deployment.yaml
│       └── react-service.yaml
└── backend/                    # FastAPI backend service
    ├── Dockerfile              # Backend Docker configuration
    ├── requirements.txt        # Backend dependencies (with AWS)
    ├── app/                    # Backend application code
    │   ├── main.py             # FastAPI entrypoint (with Lambda + security)
    │   ├── data_fetch.py       # Data fetching service
    │   ├── lambda_data_collector.py # 🔒 Secured Lambda function reference
    │   ├── aws_data_service.py # 🔒 AWS service integration (secured)
    │   ├── ichimoku.py         # Ichimoku calculation logic
    └── k8s/                    # Kubernetes manifests for backend
        ├── backend-deployment.yaml (with AWS secrets)
        └── backend-service.yaml
```

## 🔒 Security Features

This application includes **enterprise-grade security** improvements:

### **Lambda Security:**
- Hardcoded bucket names (injection-proof)
- Rate limiting (5 requests/minute per IP)
- Input validation (strict ticker format)
- Source validation (require "ichimoku-app")
- Size limits (prevent abuse)
- Enhanced monitoring (security logging)

### **Backend Security:**
- Rate limiting on all endpoints
- Input sanitization and validation
- Client IP tracking and logging
- Error message sanitization
- Enhanced exception handling

### **AWS Security:**
- Restricted IAM policies (not S3FullAccess)
- S3 server-side encryption
- Source validation for Lambda calls
- Automated secret management

## 📖 Project Description

This application provides an interactive visualization of Ichimoku Cloud technical indicators for stock tickers with **secured AWS Lambda data collection** for building custom backtesting datasets. The Ichimoku Cloud is a popular technical analysis tool that helps traders identify trend direction, momentum, and potential support/resistance levels.

### **Frontend Components:**
1. **Streamlit Frontend**: Python-based user interface with:
   - Interactive ticker input and parameter controls
   - **Secured AWS Lambda data collection**
   - Real-time chart updates with Ichimoku Cloud indicators
   - Multi-source data options (S3, Local CSV, Yahoo Finance)

2. **React Frontend**: JavaScript/HTML-based interface with:
   - Native HTML/CSS interface with lightweight-charts library
   - Synchronized dual-pane layout (main chart + volume)
   - **Secured AWS Lambda data collection UI**
   - Complete Ichimoku Cloud visualization

3. **Backend (FastAPI)**: **Security-hardened** data processing with:
   - Multi-source data fetching with intelligent fallback
   - **Rate-limited and validated** API endpoints
   - **Secured AWS S3 and Lambda integration**
   - Automatic S3 cache management with cleanup
   - Security logging and monitoring

4. **AWS Lambda Function**: **Serverless data collection** with security:
   - **Input validation and rate limiting**
   - **Source authentication** (only authorized requests)
   - **Hardcoded security parameters** (no injection attacks)
   - **Automatic data storage** in S3 with encryption
   - **Ultra-low cost** operation (free tier coverage)

## 🌩️ Data Sources

The application supports **intelligent multi-source data** with secure fallback:

1. **🌩️ S3 Cache** - Fastest (cached Yahoo Finance data with auto-cleanup)
2. **📁 AWS S3 CSV (Lambda)** - Your secured dataset via Lambda
3. **💾 Local CSV** - AAPL backup file (default option)
4. **🌐 Yahoo Finance** - Live data with automatic S3 caching

## 🎯 AWS Integration Features

### **Manual Data Collection:**
- **Secured data collection** - Click button to download any ticker  
- **Automatic overwriting** - Updates existing data seamlessly  
- **Ticker tracking** - Maintains list of available data  
- **Rate limiting** - Prevents abuse and spam  
- **Input validation** - Blocks malicious requests  

### **Cost & Performance:**
- **Cost-efficient** - Stays within free tier limits  
- **S3 auto-caching** - Speeds up repeated requests  
- **Automatic cleanup** - Prevents storage bloat  
- **Smart fallback** - Always finds data somewhere  

## 🚀 Quick Start

### **Step 1: Setup AWS Credentials**
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your AWS credentials:
# AWS_BUCKET_NAME=your-bucket-name
# AWS_ACCESS_KEY_ID=your-access-key
# AWS_SECRET_ACCESS_KEY=your-secret-key
```

### **Step 2: Deploy with Kubernetes (Recommended)**
```bash
# Make scripts executable
chmod +x k8s_setup_script.sh k8s_cleanup_script.sh

# One-command deployment
./k8s_setup_script.sh
```

**This automatically:**
- 🔧 Creates Kubernetes secrets from your `.env`
- 🚀 Deploys all services
- ✅ Tests the deployment
- 📋 Shows you the access URLs

### **Step 3: Access Applications**
- **React Frontend**: http://localhost:30002
- **Streamlit Frontend**: http://localhost:30001  
- **Backend API**: http://localhost:30000
- **API Documentation**: http://localhost:30000/docs

### **Step 4: Clean Up**
```bash
# One-command cleanup
./k8s_cleanup_script.sh
```

## 🐳 Alternative: Docker Compose

```bash
# Set up environment
echo "AWS_BUCKET_NAME=your-bucket" >> .env
echo "USE_AWS_S3=true" >> .env

# Start services
docker-compose up --build

# Access applications
# React: http://localhost:3000
# Streamlit: http://localhost:8501
# Backend: http://localhost:8000
```

## 🔧 Development Commands

### **Kubernetes Management:**
```bash
# Deploy everything
./k8s_setup_script.sh

# Check status
kubectl get all

# View logs
kubectl logs -l app=ichimoku-backend --tail=20

# Clean up
./k8s_cleanup_script.sh
```

### **Docker Management:**
```bash
# Build and start
docker-compose up --build

# Stop services
docker-compose down

# View logs
docker-compose logs backend
```

### **API Testing:**
```bash
# Test backend connectivity
curl http://localhost:30000/data/AAPL

# Check AWS status
curl http://localhost:30000/aws/status

# Test secured Lambda collection
curl -X POST http://localhost:30000/aws/collect/MSFT

# List available S3 data
curl http://localhost:30000/aws/tickers
```

## 🧪 Security Testing

### **Rate Limiting Test:**
```bash
# Test rate limiting (should block after 5 requests)
for i in {1..7}; do
  echo "Request $i:"
  curl -w "Status: %{http_code}\n" -X POST http://localhost:30000/aws/collect/TEST
done
```

### **Input Validation Test:**
```bash
# Valid tickers (should work)
curl -X POST http://localhost:30000/aws/collect/AAPL
curl -X POST http://localhost:30000/aws/collect/MSFT

# Invalid tickers (should fail)
curl -X POST http://localhost:30000/aws/collect/INVALID_TICKER  # Too long
curl -X POST http://localhost:30000/aws/collect/TEST            # Blacklisted
curl -X POST http://localhost:30000/aws/collect/A@PL            # Special chars
```

## 📊 Technical Background

The Ichimoku Cloud (Ichimoku Kinko Hyo) consists of five components:

1. **Tenkan-sen (Conversion Line)**: (9-period high + 9-period low)/2
2. **Kijun-sen (Base Line)**: (26-period high + 26-period low)/2
3. **Senkou Span A (Leading Span A)**: (Tenkan-sen + Kijun-sen)/2, plotted 26 periods ahead
4. **Senkou Span B (Leading Span B)**: (52-period high + 52-period low)/2, plotted 26 periods ahead
5. **Chikou Span (Lagging Span)**: Close price, plotted 26 periods behind

The "cloud" (kumo) is the area between Senkou Spans A and B:
- **Bullish Cloud**: When Span A > Span B → green cloud → uptrend
- **Bearish Cloud**: When Span B > Span A → red cloud → downtrend

## 🔐 Security Verification

Your setup is secure when you see:

### **Success Indicators:**
- Rate limiting works: 6th request gets 429 error
- Input validation works: Invalid tickers get 400 error
- Lambda validation works: Unauthorized requests get 403 error
- Normal usage works: Valid requests process successfully
- Monitoring active: Security events appear in logs

### **Security Red Flags:**
- Backend accepts unlimited requests
- Lambda accepts any source parameter
- Invalid ticker formats are processed
- Error messages expose internal details

## 💰 Cost Analysis

**Expected Monthly Cost: $0.00**

### **AWS Free Tier Coverage:**
- **Lambda**: 1M requests/month (you'll use 10-50)
- **S3 Storage**: 5GB free (CSV files are tiny)
- **S3 Requests**: 20,000 GET, 2,000 PUT free
- **Data Transfer**: 100GB free

### **Cost Controls:**
- Lambda disabled by default
- S3 auto-cleanup prevents bloat
- Rate limiting prevents abuse
- Input validation blocks spam

## 🛠️ Troubleshooting

### **Common Issues:**

**"AWS not available":**
```bash
# Check credentials in .env
cat .env | grep AWS

# Test AWS CLI
aws sts get-caller-identity

# Check pod environment
kubectl exec -it $(kubectl get pod -l app=ichimoku-backend -o jsonpath='{.items[0].metadata.name}') -- env | grep AWS
```

**"Rate limit exceeded":**
```bash
# Wait 1 minute between requests
# Or check rate limiting logs
kubectl logs -l app=ichimoku-backend | grep "Rate limit"
```

**"Invalid ticker":**
```bash
# Use valid format: 1-5 characters, A-Z and 0-9 only
# Avoid: TEST, SPAM, HACK, special characters
```

## 📚 Documentation

- **[Complete Setup Guide](COMPLETE_SETUP_GUIDE.md)** - Full AWS setup with security
- **[Security Summary](security_summary.md)** - Security improvements overview
- **[Lambda Guide](secured_lambda_guide.md)** - Secured Lambda implementation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Test security features
4. Ensure all scripts work
5. Verify AWS integration
6. Submit a pull request

## 📄 License

This project is open source. Please see the LICENSE file for details.

---

## 🎉 **You're Ready!**

Your **security-hardened** Ichimoku Cloud application is ready for production use with:

- 🔒 **Enterprise security** - Rate limiting, input validation, secure AWS integration
- ⚡ **High performance** - Multi-source data with intelligent caching
- 💰 **Cost optimized** - Free tier compatible with automatic controls
- 🚀 **Easy deployment** - One-command Kubernetes setup
- 🛡️ **Production ready** - Monitoring, logging, and error handling

Start exploring technical analysis with confidence! 📈