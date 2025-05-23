#!/bin/bash

# cleanup-k8s.sh - Clean up Kubernetes deployment

set -e  # Exit on any error

echo "🧹 Cleaning up Kubernetes resources..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ Error: kubectl is not installed or not in PATH!"
    exit 1
fi

# Check if kubectl can connect to cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Error: Cannot connect to Kubernetes cluster!"
    echo "Please ensure kubectl is configured and your cluster is running."
    exit 1
fi

# Delete deployments and services
echo "   Deleting applications..."
kubectl delete -f backend/k8s/ 2>/dev/null || echo "   Backend resources not found or already deleted"
kubectl delete -f streamlit-frontend/k8s/ 2>/dev/null || echo "   Streamlit frontend resources not found or already deleted"
kubectl delete -f react-frontend/k8s/ 2>/dev/null || echo "   React frontend resources not found or already deleted"

# Delete secrets and configmaps
echo "   Deleting secrets and config..."
kubectl delete secret aws-credentials 2>/dev/null || echo "   AWS credentials secret not found or already deleted"
kubectl delete configmap aws-config 2>/dev/null || echo "   AWS config configmap not found or already deleted"

# Wait for cleanup to complete
echo "   Waiting for resources to be fully deleted..."
sleep 10

# Force delete any stuck pods
echo "   Checking for stuck pods..."
STUCK_PODS=$(kubectl get pods --field-selector=status.phase!=Running,status.phase!=Succeeded --no-headers 2>/dev/null | grep ichimoku | awk '{print $1}' || true)

if [ -n "$STUCK_PODS" ]; then
    echo "   Force deleting stuck pods..."
    echo "$STUCK_PODS" | xargs kubectl delete pod --force --grace-period=0 2>/dev/null || true
fi

echo "✅ Cleanup complete!"
echo ""
echo "🔍 Remaining resources:"
REMAINING=$(kubectl get pods,services,deployments,configmaps,secrets --no-headers 2>/dev/null | grep -E "(ichimoku|aws-)" || true)

if [ -n "$REMAINING" ]; then
    echo "$REMAINING"
    echo ""
    echo "⚠️  Some resources are still present. They might be in 'Terminating' state."
    echo "   Wait a few moments and run this script again if needed."
else
    echo "   No ichimoku resources found - cleanup successful!"
fi

echo ""
echo "💡 To redeploy, run: ./k8s_setup_script.sh"