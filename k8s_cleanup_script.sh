#!/bin/bash

# cleanup-k8s.sh - Clean up Kubernetes deployment

echo "🧹 Cleaning up Kubernetes resources..."

# Delete deployments and services
echo "   Deleting applications..."
kubectl delete -f backend/k8s/ -f streamlit-frontend/k8s/ -f react-frontend/k8s/ 2>/dev/null || true

# Delete secrets and configmaps
echo "   Deleting secrets and config..."
kubectl delete secret aws-credentials 2>/dev/null || true
kubectl delete configmap aws-config 2>/dev/null || true

# Wait for cleanup
sleep 5

echo "✅ Cleanup complete!"
echo ""
echo "🔍 Remaining resources:"
kubectl get pods,secrets,configmaps | grep -E "(ichimoku|aws-)" || echo "   No ichimoku resources found"