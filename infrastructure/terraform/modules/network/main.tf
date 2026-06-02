# HECATE — Network Module
# Creates VPC, public/private subnets, Internet Gateway, NAT Gateway,
# route tables, and baseline security groups.

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ─────────────────────────────────────────────
# VPC
# ─────────────────────────────────────────────

resource "aws_vpc" "hecate" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-vpc"
  })
}

# ─────────────────────────────────────────────
# Subnets — Public (one per AZ)
# ─────────────────────────────────────────────

resource "aws_subnet" "public" {
  count = length(var.availability_zones)

  vpc_id                  = aws_vpc.hecate.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(var.common_tags, {
    Name                     = "${var.environment}-hecate-public-${var.availability_zones[count.index]}"
    "kubernetes.io/role/elb" = "1"
  })
}

# ─────────────────────────────────────────────
# Subnets — Private (one per AZ)
# ─────────────────────────────────────────────

resource "aws_subnet" "private" {
  count = length(var.availability_zones)

  vpc_id            = aws_vpc.hecate.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + length(var.availability_zones))
  availability_zone = var.availability_zones[count.index]

  tags = merge(var.common_tags, {
    Name                              = "${var.environment}-hecate-private-${var.availability_zones[count.index]}"
    "kubernetes.io/role/internal-elb" = "1"
  })
}

# ─────────────────────────────────────────────
# Internet Gateway
# ─────────────────────────────────────────────

resource "aws_internet_gateway" "hecate" {
  vpc_id = aws_vpc.hecate.id

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-igw"
  })
}

# ─────────────────────────────────────────────
# Elastic IPs for NAT Gateways
# ─────────────────────────────────────────────

resource "aws_eip" "nat" {
  count  = var.single_nat_gateway ? 1 : length(var.availability_zones)
  domain = "vpc"

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-nat-eip-${count.index}"
  })

  depends_on = [aws_internet_gateway.hecate]
}

# ─────────────────────────────────────────────
# NAT Gateways (in public subnets)
# ─────────────────────────────────────────────

resource "aws_nat_gateway" "hecate" {
  count = var.single_nat_gateway ? 1 : length(var.availability_zones)

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-nat-${count.index}"
  })

  depends_on = [aws_internet_gateway.hecate]
}

# ─────────────────────────────────────────────
# Route Tables — Public
# ─────────────────────────────────────────────

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.hecate.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.hecate.id
  }

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-rt-public"
  })
}

resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ─────────────────────────────────────────────
# Route Tables — Private (one per AZ)
# ─────────────────────────────────────────────

resource "aws_route_table" "private" {
  count  = length(var.availability_zones)
  vpc_id = aws_vpc.hecate.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = var.single_nat_gateway ? aws_nat_gateway.hecate[0].id : aws_nat_gateway.hecate[count.index].id
  }

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-rt-private-${var.availability_zones[count.index]}"
  })
}

resource "aws_route_table_association" "private" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# ─────────────────────────────────────────────
# Security Groups
# ─────────────────────────────────────────────

# Baseline security group — deny all ingress, allow all egress
resource "aws_security_group" "baseline" {
  name        = "${var.environment}-hecate-baseline-sg"
  description = "Baseline security group — deny all ingress"
  vpc_id      = aws_vpc.hecate.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-baseline-sg"
  })
}

# EKS control-plane security group
resource "aws_security_group" "eks_control_plane" {
  name        = "${var.environment}-hecate-eks-cp-sg"
  description = "Security group for EKS control plane"
  vpc_id      = aws_vpc.hecate.id

  ingress {
    description = "Allow HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-eks-cp-sg"
  })
}

# RDS security group — only accessible from EKS node CIDR
resource "aws_security_group" "rds" {
  name        = "${var.environment}-hecate-rds-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = aws_vpc.hecate.id

  ingress {
    description = "PostgreSQL from private subnets"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [for s in aws_subnet.private : s.cidr_block]
  }

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-rds-sg"
  })
}

# MSK (Kafka) security group
resource "aws_security_group" "msk" {
  name        = "${var.environment}-hecate-msk-sg"
  description = "Security group for Amazon MSK Kafka brokers"
  vpc_id      = aws_vpc.hecate.id

  ingress {
    description = "Kafka plaintext from private subnets"
    from_port   = 9092
    to_port     = 9092
    protocol    = "tcp"
    cidr_blocks = [for s in aws_subnet.private : s.cidr_block]
  }

  ingress {
    description = "Kafka TLS from private subnets"
    from_port   = 9094
    to_port     = 9094
    protocol    = "tcp"
    cidr_blocks = [for s in aws_subnet.private : s.cidr_block]
  }

  ingress {
    description = "ZooKeeper from private subnets"
    from_port   = 2181
    to_port     = 2181
    protocol    = "tcp"
    cidr_blocks = [for s in aws_subnet.private : s.cidr_block]
  }

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-msk-sg"
  })
}
