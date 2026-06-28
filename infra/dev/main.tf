terraform {
    required_version = ">= 1.10"

    required_providers {
        aws = {
            source  = "hashicorp/aws"
            version = "~> 6.0"
        }
    }

    backend "s3" {
        bucket       = "atlas-tfstate-988787367176"
        key          = "dev/terraform.tfstate"
        region       = "us-east-1"
        encrypt      = true
        use_lockfile = true
    }
}

provider "aws" {
    region = "us-east-1"

    default_tags {
        tags = {
            project = "atlas"
            env     = "dev"
            owner   = "jessi"
            managed = "terraform"
        }
    }
}