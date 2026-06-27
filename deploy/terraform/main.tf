# =============================================================================
# HECATE Production Edition — Terraform Provisioning Template
# Provisions network layer, EKS cluster, RDS Postgres database, and MSK Kafka brokers.
# =============================================================================

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ---------------------------------------------------------------------------
# VPC & Networking
# ---------------------------------------------------------------------------
resource "aws_vpc" "hecate_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "hecate-vpc-${var.environment}"
    Project     = "HECATE"
    Environment = var.environment
  }
}

resource "aws_subnet" "public_1" {
  vpc_id            = aws_vpc.hecate_vpc.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = {
    Name = "hecate-public-1-${var.environment}"
  }
}

resource "aws_subnet" "public_2" {
  vpc_id            = aws_vpc.hecate_vpc.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.aws_region}b"
  map_public_ip_on_launch = true

  tags = {
    Name = "hecate-public-2-${var.environment}"
  }
}

resource "aws_subnet" "private_1" {
  vpc_id            = aws_vpc.hecate_vpc.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "${var.aws_region}a"

  tags = {
    Name = "hecate-private-1-${var.environment}"
  }
}

resource "aws_subnet" "private_2" {
  vpc_id            = aws_vpc.hecate_vpc.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "${var.aws_region}b"

  tags = {
    Name = "hecate-private-2-${var.environment}"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.hecate_vpc.id

  tags = {
    Name = "hecate-igw-${var.environment}"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.hecate_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

resource "aws_route_table_association" "public_1" {
  subnet_id      = aws_subnet.public_1.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_2" {
  subnet_id      = aws_subnet.public_2.id
  route_table_id = aws_route_table.public.id
}

# ---------------------------------------------------------------------------
# IAM Roles & Policies for EKS
# ---------------------------------------------------------------------------
resource "aws_iam_role" "eks_cluster" {
  name = "hecate-eks-cluster-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

# ---------------------------------------------------------------------------
# EKS Cluster
# ---------------------------------------------------------------------------
resource "aws_eks_cluster" "eks" {
  name     = "hecate-eks-${var.environment}"
  role_arn = aws_iam_role.eks_cluster.arn

  vpc_config {
    subnet_ids = [
      aws_subnet.public_1.id,
      aws_subnet.public_2.id,
      aws_subnet.private_1.id,
      aws_subnet.private_2.id
    ]
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy
  ]
}

# ---------------------------------------------------------------------------
# RDS Postgres Database
# ---------------------------------------------------------------------------
resource "aws_db_subnet_group" "rds" {
  name       = "hecate-rds-subnet-group-${var.environment}"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]
}

resource "aws_db_instance" "postgres" {
  allocated_storage      = 20
  db_name                = "hecatedb"
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = var.db_instance_class
  username               = "hecadeadmin"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.rds.name
  vpc_security_group_ids = [aws_security_group.db.id]
  skip_final_snapshot    = true
}

resource "aws_security_group" "db" {
  name        = "hecate-sg-db-${var.environment}"
  description = "Allow EKS nodes access to Postgres DB"
  vpc_id      = aws_vpc.hecate_vpc.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.hecate_vpc.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------------------------------------------------------------------------
# Amazon MSK (Managed Streaming for Kafka)
# ---------------------------------------------------------------------------
resource "aws_security_group" "msk" {
  name        = "hecate-sg-msk-${var.environment}"
  description = "Allow EKS nodes access to MSK Kafka brokers"
  vpc_id      = aws_vpc.hecate_vpc.id

  ingress {
    from_port   = 9092
    to_port     = 9094
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.hecate_vpc.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_msk_cluster" "kafka" {
  cluster_name           = "hecate-msk-${var.environment}"
  kafka_version          = "3.2.0"
  number_of_broker_nodes = 2

  broker_node_group_info {
    instance_type = "kafka.t3.small"
    client_subnets = [
      aws_subnet.private_1.id,
      aws_subnet.private_2.id
    ]
    security_groups = [aws_security_group.msk.id]
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "PLAINTEXT"
      in_cluster    = true
    }
  }

  tags = {
    Environment = var.environment
  }
}
