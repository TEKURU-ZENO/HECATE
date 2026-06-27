# HECATE v2.0 Production Edition Deployment Guide

This guide details how to deploy the HECATE platform across local and remote Kubernetes environments.

## 1. Infrastructure Provisioning (Terraform)
Navigate to the Terraform deployment folder to provision AWS resources:
```bash
cd deploy/terraform
terraform init
terraform plan
terraform apply
```
This provisions:
- AWS VPC (Public & Private subnets)
- EKS Cluster
- RDS PostgreSQL
- Amazon MSK (Managed Kafka)

## 2. Kubernetes Packaging (Helm)
To deploy all microservices to Kubernetes via Helm:
```bash
helm install hecate deploy/helm/hecate -n hecate-system --create-namespace
```
To override values for specific environments:
```bash
helm install hecate deploy/helm/hecate -f deploy/helm/hecate/values.yaml -n hecate-system
```

## 3. Configuration Management (Kustomize)
To apply local or staging overlays:
```bash
# Local development overlay
kubectl apply -k deploy/kustomize/overlays/dev

# Production overlay
kubectl apply -k deploy/kustomize/overlays/prod
```
