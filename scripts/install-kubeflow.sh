#!/bin/bash

echo "Installing Kubeflow Pipelines..."

# Install Kubeflow Pipelines standalone
export PIPELINE_VERSION=2.0.5
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref=$PIPELINE_VERSION"
kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io

# Install Kubeflow Pipelines multi-user
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic-multi-user?ref=$PIPELINE_VERSION"

# Wait for deployments to be ready
echo "Waiting for Kubeflow Pipelines to be ready..."
kubectl wait --for=condition=available --timeout=600s deployment/ml-pipeline -n kubeflow
kubectl wait --for=condition=available --timeout=600s deployment/ml-pipeline-ui -n kubeflow

# Port forward to access UI
echo "Kubeflow Pipelines installed successfully!"
echo "Access the UI at: http://localhost:8080"
echo "To port-forward: kubectl port-forward -n kubeflow svc/ml-pipeline-ui 8080:80"

# Apply healthcare-specific configuration
kubectl apply -f infrastructure/kubernetes/kubeflow/kubeflow-setup.yaml

echo "Healthcare-specific Kubeflow configuration applied!"