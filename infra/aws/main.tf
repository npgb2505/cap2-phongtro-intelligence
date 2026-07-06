terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.56"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

locals {
  database_url = "postgresql+psycopg://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.address}:5432/phongtro"
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_s3_bucket" "raw_zone" {
  bucket = "${var.project_name}-raw-${var.environment}"
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "raw_zone" {
  bucket = aws_s3_bucket.raw_zone.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}-backend-${var.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

resource "aws_ecr_repository" "crawler" {
  name                 = "${var.project_name}-crawler-${var.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

resource "aws_secretsmanager_secret" "database_url" {
  name = "${var.project_name}/${var.environment}/database-url"
  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = local.database_url
}

resource "aws_db_instance" "postgres" {
  identifier              = "${var.project_name}-${var.environment}"
  engine                  = "postgres"
  engine_version          = "16.3"
  instance_class          = "db.t4g.micro"
  allocated_storage       = 20
  db_name                 = "phongtro"
  username                = var.db_username
  password                = var.db_password
  publicly_accessible     = true
  skip_final_snapshot     = true
  deletion_protection     = false
  backup_retention_period = 1
  vpc_security_group_ids  = [aws_security_group.postgres.id]

  lifecycle {
    precondition {
      condition     = var.paid_deploy_acknowledgement == "CHECKED_BILLING_BUDGET_APPROVED_100_USD"
      error_message = "Refusing to create paid AWS resources. Check AWS Credits/Billing, create Budget alerts, then set paid_deploy_acknowledgement = \"CHECKED_BILLING_BUDGET_APPROVED_100_USD\"."
    }

    precondition {
      condition     = var.monthly_credit_limit_usd <= 100
      error_message = "This pilot is capped at 100 USD credit. Keep monthly_credit_limit_usd <= 100."
    }
  }

  tags = local.common_tags
}

resource "aws_security_group" "postgres" {
  name        = "${var.project_name}-${var.environment}-postgres"
  description = "Pilot PostgreSQL access"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = var.db_ingress_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_ecs_cluster" "crawler" {
  name = "${var.project_name}-${var.environment}"
  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "crawler" {
  name              = "/ecs/${var.project_name}/${var.environment}/crawler"
  retention_in_days = 14
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/apprunner/${var.project_name}/${var.environment}/backend"
  retention_in_days = 14
  tags              = local.common_tags
}

resource "aws_security_group" "crawler" {
  name        = "${var.project_name}-${var.environment}-crawler"
  description = "Scheduled crawler egress"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-${var.environment}-ecs-task-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name = "${var.project_name}-${var.environment}-ecs-secrets"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue"
      ]
      Resource = aws_secretsmanager_secret.database_url.arn
    }]
  })
}

resource "aws_iam_role" "crawler_task" {
  name = "${var.project_name}-${var.environment}-crawler-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "crawler_task" {
  name = "${var.project_name}-${var.environment}-crawler-task"
  role = aws_iam_role.crawler_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.raw_zone.arn,
          "${aws_s3_bucket.raw_zone.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.database_url.arn
      }
    ]
  })
}

resource "aws_ecs_task_definition" "crawler" {
  count                    = var.crawler_image_identifier == "" ? 0 : 1
  family                   = "${var.project_name}-${var.environment}-crawler"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.crawler_task.arn

  container_definitions = jsonencode([
    {
      name      = "crawler"
      image     = var.crawler_image_identifier
      essential = true
      command   = var.crawler_command
      environment = [
        { name = "PT_LOCAL_ARTIFACT_DIR", value = "/app/artifacts" },
        { name = "PT_S3_BUCKET", value = aws_s3_bucket.raw_zone.id },
        { name = "PT_S3_PREFIX", value = "crawler/${var.environment}" },
        { name = "PT_CITY", value = "all" },
        { name = "PT_PAGES", value = "3" },
        { name = "PT_MAX_DETAIL_PAGES", value = "20" },
        { name = "PT_DETAIL_WORKERS", value = "6" },
        { name = "PT_EXACT_GEOCODE_LIMIT", value = "0" },
        { name = "PT_SOURCES", value = "all" }
      ]
      secrets = [
        { name = "PT_DATABASE_URL", valueFrom = aws_secretsmanager_secret.database_url.arn }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.crawler.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "crawler"
        }
      }
    }
  ])

  tags = local.common_tags
}

resource "aws_iam_role" "eventbridge_scheduler" {
  count = var.crawler_image_identifier == "" ? 0 : 1
  name  = "${var.project_name}-${var.environment}-scheduler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "scheduler.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "eventbridge_scheduler" {
  count = var.crawler_image_identifier == "" ? 0 : 1
  name  = "${var.project_name}-${var.environment}-scheduler"
  role  = aws_iam_role.eventbridge_scheduler[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ecs:RunTask"
        Resource = aws_ecs_task_definition.crawler[0].arn
      },
      {
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = [
          aws_iam_role.ecs_task_execution.arn,
          aws_iam_role.crawler_task.arn
        ]
      }
    ]
  })
}

resource "aws_scheduler_schedule" "crawler_daily" {
  count      = var.crawler_image_identifier == "" ? 0 : 1
  name       = "${var.project_name}-${var.environment}-crawler-daily"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = var.crawler_schedule_expression

  target {
    arn      = aws_ecs_cluster.crawler.arn
    role_arn = aws_iam_role.eventbridge_scheduler[0].arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.crawler[0].arn
      launch_type         = "FARGATE"

      network_configuration {
        subnets          = data.aws_subnets.default.ids
        security_groups  = [aws_security_group.crawler.id]
        assign_public_ip = true
      }
    }
  }
}

resource "aws_iam_role" "apprunner_access" {
  count = var.backend_image_identifier == "" ? 0 : 1
  name  = "${var.project_name}-${var.environment}-apprunner-access"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "build.apprunner.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "apprunner_access" {
  count      = var.backend_image_identifier == "" ? 0 : 1
  role       = aws_iam_role.apprunner_access[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

resource "aws_iam_role" "apprunner_instance" {
  count = var.backend_image_identifier == "" ? 0 : 1
  name  = "${var.project_name}-${var.environment}-apprunner-instance"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "tasks.apprunner.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "apprunner_instance_secrets" {
  count = var.backend_image_identifier == "" ? 0 : 1
  name  = "${var.project_name}-${var.environment}-apprunner-secrets"
  role  = aws_iam_role.apprunner_instance[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue"
      ]
      Resource = aws_secretsmanager_secret.database_url.arn
    }]
  })
}

resource "aws_apprunner_service" "backend" {
  count        = var.backend_image_identifier == "" ? 0 : 1
  service_name = "${var.project_name}-${var.environment}-backend"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_access[0].arn
    }

    image_repository {
      image_identifier      = var.backend_image_identifier
      image_repository_type = "ECR"

      image_configuration {
        port = "8000"
        runtime_environment_variables = {
          PT_APP_ENV      = "production"
          PT_APP_DEBUG    = "false"
          PT_CORS_ORIGINS = var.backend_cors_origins
        }
        runtime_environment_secrets = {
          PT_DATABASE_URL = aws_secretsmanager_secret.database_url.arn
        }
      }
    }

    auto_deployments_enabled = true
  }

  instance_configuration {
    cpu               = "0.25 vCPU"
    memory            = "0.5 GB"
    instance_role_arn = aws_iam_role.apprunner_instance[0].arn
  }

  tags = local.common_tags
}
