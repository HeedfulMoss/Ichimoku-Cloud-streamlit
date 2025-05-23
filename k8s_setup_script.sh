#!/bin/bash

# setup-k8s.sh - Automated Kubernetes deployment with AWS secrets from .env

set -e  # Exit on any error

echo "🚀 Setting up Kubernetes deployment with AWS integration..."

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

# Load environment variables from .env
echo "📄 Loading configuration from .env..."
export $(grep -v '^#' .env | xargs)

# Validate required variables
if [[ -z "$AWS_ACCESS_KEY_ID" || -z "$AWS_SECRET_ACCESS_KEY" || -z "$AWS_BUCKET_NAME" ]]; then
    echo "❌ Error: Missing required AWS credentials in .env file!"
    echo "Required variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME"
    exit 1
fi

echo "✅ Configuration loaded:"
echo "   - Bucket: $AWS_BUCKET_NAME"
echo "   - Region: ${AWS_DEFAULT_REGION:-us-east-1}"
echo "   - S3 Enabled: ${USE_AWS_S3:-true}"

# Delete existing secret if it exists (ignore errors)
echo "🗑️ Cleaning up existing resources..."
kubectl delete secret aws-credentials 2>/dev/null || true

# Delete existing deployments
kubectl delete -f backend/k8s/ -f streamlit-frontend/k8s/ -f react-frontend/k8s/ 2>/dev/null || true

# Wait a moment for cleanup
sleep 5

# Create AWS credentials secret from .env
echo "🔐 Creating AWS credentials secret..."
kubectl create secret generic aws-credentials \
    --from-literal=aws-access-key-id="$AWS_ACCESS_KEY_ID" \
    --from-literal=aws-secret-access-key="$AWS_SECRET_ACCESS_KEY" \
    --from-literal=aws-default-region="${AWS_DEFAULT_REGION:-us-east-1}"

# Create ConfigMap for non-secret environment variables
echo "📋 Creating configuration..."
kubectl create configmap aws-config \
    --from-literal=AWS_BUCKET_NAME="$AWS_BUCKET_NAME" \
    --from-literal=USE_AWS_S3="${USE_AWS_S3:-true}" \
    --from-literal=USE_AWS_LAMBDA="${USE_AWS_LAMBDA:-false}" \
    --from-literal=USE_AWS_CLOUDWATCH="${USE_AWS_CLOUDWATCH:-false}"

# Deploy applications
echo "🚀 Deploying applications..."
kubectl apply -f backend/k8s/ -f streamlit-frontend/k8s/ -f react-frontend/k8s/

# Wait for deployments to be ready
echo "⏳ Waiting for pods to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/ichimoku-backend
kubectl wait --for=condition=available --timeout=300s deployment/ichimoku-streamlit-frontend  
kubectl wait --for=condition=available --timeout=300s deployment/ichimoku-react-frontend

# Test the deployment
echo "🧪 Testing deployment..."
sleep 10  # Give services time to start

# Test backend health
echo "   Testing backend health..."
if curl -f -s http://localhost:30000/ > /dev/null; then
    echo "   ✅ Backend is responding"
else
    echo "   ⚠️ Backend may not be ready yet"
fi

# Test AWS status
echo "   Testing AWS integration..."
AWS_STATUS=$(curl -s http://localhost:30000/aws/status || echo '{"s3_connected": false}')
S3_CONNECTED=$(echo $AWS_STATUS | grep -o '"s3_connected":[^,}]*' | cut -d: -f2)

if [[ "$S3_CONNECTED" == "true" ]]; then
    echo "   ✅ AWS S3 integration working"
else
    echo "   ❌ AWS S3 integration failed"
    echo "   Response: $AWS_STATUS"
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
echo "   - Cleanup:           ./cleanup-k8s.sh"
echo ""

# Show pod status
echo "📊 Current pod status:"
kubectl get pods -o wide