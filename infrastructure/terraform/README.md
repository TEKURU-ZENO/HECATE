# HECATE — Terraform Infrastructure

This directory contains all Terraform code for provisioning the HECATE platform on AWS. The infrastructure follows a **module-based** design with separate environment configurations for dev, staging, and production.

---

## Architecture Overview

```
infrastructure/terraform/
├── modules/
│   ├── network/        # VPC, subnets, NAT gateway, security groups
│   ├── eks/            # EKS cluster, node groups, add-ons
│   ├── rds/            # PostgreSQL RDS for incident and audit storage
│   ├── redis/          # ElastiCache Redis for caching and pub/sub
│   ├── kafka/          # Amazon MSK (Managed Streaming for Kafka)
│   ├── monitoring/     # Prometheus, Grafana, AlertManager on EKS
│   └── security/       # IAM roles, KMS keys, HashiCorp Vault
└── environments/
    ├── dev/
    ├── staging/
    └── prod/
```

---

## Module Overview

| Module | Description | Key Resources |
|--------|-------------|---------------|
| `network` | Core networking layer | VPC, public/private subnets, IGW, NAT, route tables, security groups |
| `eks` | Kubernetes control plane | EKS cluster, managed node groups, IRSA, cluster add-ons |
| `rds` | Relational database | PostgreSQL 15 RDS, parameter group, subnet group, automated backups |
| `redis` | In-memory cache | ElastiCache Redis cluster, replication group |
| `kafka` | Event streaming | MSK cluster, broker nodes, Kafka topics, ACLs |
| `monitoring` | Observability stack | Prometheus, Grafana, AlertManager, Loki (via Helm on EKS) |
| `security` | Access control | IAM roles/policies, IRSA mappings, KMS CMKs, Vault cluster |

---

## Environments

| Environment | AWS Region | EKS Node Size | RDS Instance | Purpose |
|-------------|------------|---------------|--------------|---------|
| `dev` | us-east-1 | t3.medium (2) | db.t3.micro | Development and unit testing |
| `staging` | us-east-1 | t3.large (3) | db.t3.small | Integration testing, pre-prod validation |
| `prod` | us-east-1 | m5.xlarge (5+) | db.r6g.large | Production workloads |

---

## Prerequisites

- **AWS CLI** ≥ 2.13 configured with appropriate credentials (`aws configure`)
- **Terraform** ≥ 1.6.0 ([download](https://www.terraform.io/downloads))
- **kubectl** ≥ 1.28 ([install guide](https://kubernetes.io/docs/tasks/tools/))
- **Helm** ≥ 3.12 (for monitoring module)
- S3 bucket and DynamoDB table for remote state (see State Management)

---

## Usage

### Initialize and Deploy (Dev)

```bash
# Navigate to the dev environment
cd environments/dev

# Initialize Terraform (downloads providers, configures backend)
terraform init

# Preview the plan
terraform plan -out=tfplan

# Apply the plan
terraform apply tfplan
```

### Targeting a Specific Module

```bash
# Only apply network changes
terraform plan -target=module.network
terraform apply -target=module.network
```

### Destroying an Environment

```bash
# Only use in dev/staging — NEVER in prod without approval
terraform destroy
```

---

## State Management

Remote state is stored in **S3** with **DynamoDB** for state locking:

| Resource | Name |
|----------|------|
| S3 Bucket | `hecate-terraform-state-{env}` |
| DynamoDB Table | `hecate-terraform-lock` |
| S3 Key | `{env}/terraform.tfstate` |
| Encryption | AES-256 (SSE-S3) |

### Creating the State Backend (one-time, per account)

```bash
# Create the S3 bucket
aws s3api create-bucket \
  --bucket hecate-terraform-state-dev \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket hecate-terraform-state-dev \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket hecate-terraform-state-dev \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Create DynamoDB lock table
aws dynamodb create-table \
  --table-name hecate-terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

---

## Variable Management

Sensitive variables (AWS credentials, DB passwords, API keys) are **never** stored in `terraform.tfvars` or committed to Git. Use:

1. **AWS Secrets Manager** for runtime secrets (referenced via `data` sources)
2. **Environment variables** (`TF_VAR_*`) in CI/CD pipelines
3. **terraform.tfvars.example** files document required variable shapes without values

---

## CI/CD Integration

Terraform is run in GitHub Actions via the `.github/workflows/terraform.yml` pipeline:

- **PR**: `terraform fmt -check`, `terraform validate`, `terraform plan` (plan output posted as PR comment)
- **Merge to main**: `terraform apply` with manual approval gate for staging/prod

---

## Security Notes

- All resources are tagged with `Project=HECATE`, `Environment`, and `ManagedBy=Terraform`
- RDS and MSK are deployed in **private subnets only** — no public endpoints
- EKS API server endpoint is restricted to a VPN CIDR allowlist in staging/prod
- KMS CMKs are used for EKS secrets encryption, RDS at-rest encryption, and S3 state bucket
