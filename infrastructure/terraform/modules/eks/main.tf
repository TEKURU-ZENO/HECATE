# HECATE — EKS Module
# Creates an EKS cluster with managed node groups, IRSA, and essential add-ons.

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

# ─────────────────────────────────────────────
# IAM Role for EKS Cluster
# ─────────────────────────────────────────────

resource "aws_iam_role" "eks_cluster" {
  name = "${var.environment}-hecate-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.eks_cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_iam_role_policy_attachment" "eks_vpc_resource_controller" {
  role       = aws_iam_role.eks_cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
}

# ─────────────────────────────────────────────
# EKS Cluster
# ─────────────────────────────────────────────

resource "aws_eks_cluster" "hecate" {
  name     = "${var.environment}-hecate"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = var.private_subnet_ids
    security_group_ids      = [var.control_plane_sg_id]
    endpoint_private_access = true
    endpoint_public_access  = var.environment == "dev" ? true : false
    public_access_cidrs     = var.environment == "dev" ? ["0.0.0.0/0"] : var.allowed_cidrs
  }

  encryption_config {
    resources = ["secrets"]
    provider {
      key_arn = var.kms_key_arn
    }
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-eks"
  })

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller,
  ]
}

# ─────────────────────────────────────────────
# OIDC Provider (for IRSA)
# ─────────────────────────────────────────────

data "tls_certificate" "hecate" {
  url = aws_eks_cluster.hecate.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "hecate" {
  url             = aws_eks_cluster.hecate.identity[0].oidc[0].issuer
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.hecate.certificates[0].sha1_fingerprint]

  tags = var.common_tags
}

# ─────────────────────────────────────────────
# IAM Role for Node Groups
# ─────────────────────────────────────────────

resource "aws_iam_role" "eks_node_group" {
  name = "${var.environment}-hecate-eks-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  role       = aws_iam_role.eks_node_group.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  role       = aws_iam_role.eks_node_group.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "eks_ecr_read" {
  role       = aws_iam_role.eks_node_group.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# ─────────────────────────────────────────────
# Managed Node Group — System
# ─────────────────────────────────────────────

resource "aws_eks_node_group" "system" {
  cluster_name    = aws_eks_cluster.hecate.name
  node_group_name = "${var.environment}-hecate-system"
  node_role_arn   = aws_iam_role.eks_node_group.arn
  subnet_ids      = var.private_subnet_ids
  instance_types  = [var.system_node_instance_type]

  scaling_config {
    desired_size = var.system_node_desired
    max_size     = var.system_node_max
    min_size     = var.system_node_min
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    role = "system"
  }

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-system-node"
  })

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_ecr_read,
  ]
}

# ─────────────────────────────────────────────
# Managed Node Group — Agents
# ─────────────────────────────────────────────

resource "aws_eks_node_group" "agents" {
  cluster_name    = aws_eks_cluster.hecate.name
  node_group_name = "${var.environment}-hecate-agents"
  node_role_arn   = aws_iam_role.eks_node_group.arn
  subnet_ids      = var.private_subnet_ids
  instance_types  = [var.agent_node_instance_type]

  scaling_config {
    desired_size = var.agent_node_desired
    max_size     = var.agent_node_max
    min_size     = var.agent_node_min
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    role = "agents"
  }

  taint {
    key    = "dedicated"
    value  = "hecate-agents"
    effect = "NO_SCHEDULE"
  }

  tags = merge(var.common_tags, {
    Name = "${var.environment}-hecate-agents-node"
  })

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_ecr_read,
  ]
}

# ─────────────────────────────────────────────
# EKS Add-ons
# ─────────────────────────────────────────────

resource "aws_eks_addon" "coredns" {
  cluster_name                = aws_eks_cluster.hecate.name
  addon_name                  = "coredns"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  tags = var.common_tags
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = aws_eks_cluster.hecate.name
  addon_name                  = "kube-proxy"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  tags = var.common_tags
}

resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = aws_eks_cluster.hecate.name
  addon_name                  = "vpc-cni"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  tags = var.common_tags
}

resource "aws_eks_addon" "ebs_csi_driver" {
  cluster_name                = aws_eks_cluster.hecate.name
  addon_name                  = "aws-ebs-csi-driver"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"
  service_account_role_arn    = aws_iam_role.ebs_csi_driver.arn

  tags = var.common_tags
}

# IAM role for EBS CSI driver (IRSA)
resource "aws_iam_role" "ebs_csi_driver" {
  name = "${var.environment}-hecate-ebs-csi-driver"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.hecate.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${replace(aws_iam_openid_connect_provider.hecate.url, "https://", "")}:sub" = "system:serviceaccount:kube-system:ebs-csi-controller-sa"
        }
      }
    }]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "ebs_csi_driver" {
  role       = aws_iam_role.ebs_csi_driver.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
}
