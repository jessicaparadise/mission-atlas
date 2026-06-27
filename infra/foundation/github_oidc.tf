# ── 1. Register GitHub as a trusted OIDC identity provider ──
# This tells AWS: "I recognize and trust tokens issued by GitHub Actions."
data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github.certificates[0].sha1_fingerprint]
}

# ── 2. The role GitHub Actions will assume ──
variable "github_repo" {
  description = "owner/repo allowed to assume this role"
  type        = string
  default     = "jessicaparadise/mission-atlas"
}

data "aws_iam_policy_document" "github_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    # Audience check — must be AWS STS
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # THE crucial line — only YOUR repo can assume this role.
    # Without this, ANY GitHub repo on earth could assume it. This is the lock.
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:*"]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name               = "atlas-github-actions"
  assume_role_policy = data.aws_iam_policy_document.github_assume.json
}

# ── 3. What the role is allowed to DO ──
# Starting permissive to keep you unblocked; we tighten this in Phase 4.
# The ADR documents this as a conscious, temporary tradeoff.
resource "aws_iam_role_policy_attachment" "github_admin" {
  role       = aws_iam_role.github_actions.name
  policy_arn = "arn:aws:iam::aws:policy/PowerUserAccess"
}

output "github_actions_role_arn" {
  value       = aws_iam_role.github_actions.arn
  description = "Paste this ARN into your GitHub Actions workflow"
}