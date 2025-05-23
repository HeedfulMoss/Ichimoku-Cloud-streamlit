#!/bin/bash

# setup-k8s.sh - Automated Kubernetes deployment with AWS secrets from .env

set -e  # Exit on any error

echo "🚀 Setting up Kubernetes deployment with AWS integration..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ Error: kubectl is not installed or not in PATH!"
    echo "Please install kubectl and ensure it's configured to connect to your cluster."
    exit 1
fi

# Check if kubectl can connect to cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Error: Cannot connect to Kubernetes cluster!"
    echo "Please ensure kubectl is configured and your cluster is running."
    echo "For local development, you might need to start minikube or Docker Desktop."
    exit 1
fi

# Check if .env file exists
if [[ ! -f .env ]]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env file with AWS credentials. Example:"
    echo ""
    echo "AWS_BUCKET_NAME=ichimoku-data-bt2025"
    echo "AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX"
    echo "AWS_SECRET_ACCESS_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    echo "AWS_DEFAULT_REGION=us-east-1"
    echo "USE_AWS_S3=true"
    echo "USE_AWS_LAMBDA=false"
    echo "USE_AWS_CLOUDWATCH=false"
    exit 1
fi

# Load environment variables from .env (handle both Unix and Windows line endings)
echo "📄 Loading configuration from .env..."
if command -v dos2unix &> /dev/null; then
    dos2unix .env 2>/dev/null || true
fi

# Export variables from .env, ignoring comments and empty lines
set -a  # automatically export all variables
source <(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//')
set +a

# Validate required variables
if [[ -z "$AWS_ACCESS_KEY_ID" || -z "$AWS_SECRET_ACCESS_KEY" || -z "$AWS_BUCKET_NAME" ]]; then
    echo "❌ Error: Missing required AWS credentials in .env file!"
    echo "Required variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME"
    exit 1
fi

# Set defaults for optional variables
AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
USE_AWS_S3=${USE_AWS_S3:-true}
USE_AWS_LAMBDA=${USE_AWS_LAMBDA:-false}
USE_AWS_CLOUDWATCH=${USE_AWS_CLOUDWATCH:-false}

echo "✅ Configuration loaded:"
echo "   - Bucket: $AWS_BUCKET_NAME"
echo "   - Region: $AWS_DEFAULT_REGION"
echo "   - S3 Enabled: $USE_AWS_S3"

# Check if Docker images exist locally
echo "🔍 Checking Docker images..."
images_missing=false

if ! docker image inspect ichimoku-cloud-streamlit-backend:latest &> /dev/null; then
    echo "⚠️  Backend image not found: ichimoku-cloud-streamlit-backend:latest"
    images_missing=true
fi

if ! docker image inspect ichimoku-cloud-streamlit-streamlit-frontend:latest &> /dev/null; then
    echo "⚠️  Streamlit frontend image not found: ichimoku-cloud-streamlit-streamlit-frontend:latest"
    images_missing=true
fi

if ! docker image inspect ichimoku-cloud-streamlit-react-frontend:latest &> /dev/null; then
    echo "⚠️  React frontend image not found: ichimoku-cloud-streamlit-react-frontend:latest"
    images_missing=true
fi

if [ "$images_missing" = true ]; then
    echo "🔨 Building missing Docker images..."
    docker-compose build
    echo "✅ Docker images built successfully"
fi

# Delete existing secret if it exists (ignore errors)
echo "🗑️ Cleaning up existing resources..."
kubectl delete secret aws-credentials 2>/dev/null || true
kubectl delete configmap aws-config 2>/dev/null || true

# Delete existing deployments
kubectl delete -f backend/k8s/ 2>/dev/null || true
kubectl delete -f streamlit-frontend/k8s/ 2>/dev/null || true
kubectl delete -f react-frontend/k8s/ 2>/dev/null || true

# Wait a moment for cleanup
sleep 5

# Create AWS credentials secret from .env
echo "🔐 Creating AWS credentials secret..."
kubectl create secret generic aws-credentials \
    --from-literal=aws-access-key-id="$AWS_ACCESS_KEY_ID" \
    --from-literal=aws-secret-access-key="$AWS_SECRET_ACCESS_KEY" \
    --from-literal=aws-default-region="$AWS_DEFAULT_REGION"

# Create ConfigMap for non-secret environment variables
echo "📋 Creating configuration..."
kubectl create configmap aws-config \
    --from-literal=AWS_BUCKET_NAME="$AWS_BUCKET_NAME" \
    --from-literal=USE_AWS_S3="$USE_AWS_S3" \
    --from-literal=USE_AWS_LAMBDA="$USE_AWS_LAMBDA" \
    --from-literal=USE_AWS_CLOUDWATCH="$USE_AWS_CLOUDWATCH"

# Deploy applications
echo "🚀 Deploying applications..."
kubectl apply -f backend/k8s/
kubectl apply -f streamlit-frontend/k8s/
kubectl apply -f react-frontend/k8s/

# Wait for deployments to be ready
echo "⏳ Waiting for pods to be ready..."
echo "   Waiting for backend..."
kubectl wait --for=condition=available --timeout=300s deployment/ichimoku-backend || {
    echo "❌ Backend deployment failed"
    kubectl get pods -l app=ichimoku-backend
    kubectl logs -l app=ichimoku-backend --tail=20
    exit 1
}

echo "   Waiting for Streamlit frontend..."
kubectl wait --for=condition=available --timeout=300s deployment/ichimoku-streamlit-frontend || {
    echo "❌ Streamlit frontend deployment failed"
    kubectl get pods -l app=ichimoku-streamlit-frontend
    exit 1
}

echo "   Waiting for React frontend..."
kubectl wait --for=condition=available --timeout=300s deployment/ichimoku-react-frontend || {
    echo "❌ React frontend deployment failed"
    kubectl get pods -l app=ichimoku-react-frontend
    exit 1
}

# Test the deployment
echo "🧪 Testing deployment..."
sleep 10  # Give services time to start

# Test backend health with retries
echo "   Testing backend health..."
for i in {1..6}; do
    if curl -f -s http://localhost:30000/ > /dev/null; then
        echo "   ✅ Backend is responding"
        break
    else
        if [ $i -eq 6 ]; then
            echo "   ⚠️ Backend is not responding after 60 seconds"
            echo "   Check logs: kubectl logs -l app=ichimoku-backend"
        else
            echo "   Attempt $i/6: Backend not ready, waiting 10 seconds..."
            sleep 10
        fi
    fi
done

# Test AWS status
echo "   Testing AWS integration..."
AWS_STATUS=$(curl -s http://localhost:30000/aws/status 2>/dev/null || echo '{"s3_connected": false}')
S3_CONNECTED=$(echo "$AWS_STATUS" | grep -o '"s3_connected":[^,}]*' | cut -d: -f2 | tr -d ' ')

if [[ "$S3_CONNECTED" == "true" ]]; then
    echo "   ✅ AWS S3 integration working"
else
    echo "   ❌ AWS S3 integration failed"
    echo "   Response: $AWS_STATUS"
    echo "   This might be expected if you haven't configured AWS credentials properly"
fi

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📱 Access your applications:"
echo "   - React Frontend:    http://localhost:30002"
echo "   - Streamlit Frontend: http://localhost:30001"  
echo "   - Backend API:       http://localhost:30000"
echo "   - API Docs:          http://localhost:30000/docs"
echo ""
echo "🔍 Useful commands:"
echo "   - Check pods:        kubectl get pods"
echo "   - Check logs:        kubectl logs -l app=ichimoku-backend"
echo "   - Test AWS:          curl http://localhost:30000/aws/status"
echo "   - Cleanup:           ./k8s_cleanup_script.sh"
echo ""

# Show pod status
echo "📊 Current pod status:"
kubectl get pods -o wide

echo ""
echo "🎯 Quick test commands:"
echo "   curl http://localhost:30000/"
echo "   curl http://localhost:30000/data/AAPL"