#!/bin/bash

echo "Installing Prometheus and Grafana monitoring stack..."

# Add Prometheus helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus and Grafana
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace mlops-monitoring \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set grafana.adminPassword=admin123 \
  --set prometheus.service.type=NodePort \
  --set prometheus.service.nodePort=30090 \
  --set grafana.service.type=NodePort \
  --set grafana.service.nodePort=30091 \
  --wait

echo "Monitoring stack installed!"
echo "Prometheus: http://localhost:30090"
echo "Grafana: http://localhost:30091 (admin/admin123)"