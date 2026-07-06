variable "aws_region" {
  type    = string
  default = "ap-southeast-1"
}

variable "project_name" {
  type    = string
  default = "phongtro-intelligence"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "db_username" {
  type    = string
  default = "postgres"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "monthly_credit_limit_usd" {
  type        = number
  default     = 100
  description = "Maximum AWS credit/budget limit approved for this pilot."

  validation {
    condition     = var.monthly_credit_limit_usd > 0 && var.monthly_credit_limit_usd <= 100
    error_message = "monthly_credit_limit_usd must be between 1 and 100 for the current pilot."
  }
}

variable "paid_deploy_acknowledgement" {
  type        = string
  default     = ""
  description = "Set to CHECKED_BILLING_BUDGET_APPROVED_100_USD only after checking credits and creating AWS Budget alerts."

  validation {
    condition = contains([
      "",
      "CHECKED_BILLING_BUDGET_APPROVED_100_USD"
    ], var.paid_deploy_acknowledgement)
    error_message = "paid_deploy_acknowledgement must be empty or CHECKED_BILLING_BUDGET_APPROVED_100_USD."
  }
}

variable "backend_image_identifier" {
  type        = string
  default     = ""
  description = "Optional full ECR image identifier for the backend App Runner service."
}

variable "crawler_image_identifier" {
  type        = string
  default     = ""
  description = "Optional full ECR image identifier for the scheduled crawler ECS task."
}

variable "crawler_schedule_expression" {
  type        = string
  default     = "cron(15 19 * * ? *)"
  description = "UTC EventBridge schedule. Default is 02:15 Asia/Saigon."
}

variable "backend_cors_origins" {
  type        = string
  default     = "*"
  description = "Comma-separated CORS origins for the backend."
}

variable "crawler_command" {
  type        = list(string)
  default     = ["python", "-m", "app.cloud_job"]
  description = "Command used by the scheduled crawler task."
}

variable "db_ingress_cidrs" {
  type        = list(string)
  default     = ["0.0.0.0/0"]
  description = "Pilot DB ingress CIDRs. Tighten this before production."
}
