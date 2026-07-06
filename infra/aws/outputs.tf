output "raw_bucket_name" {
  value = aws_s3_bucket.raw_zone.id
}

output "postgres_endpoint" {
  value = aws_db_instance.postgres.address
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.crawler.name
}

output "backend_ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "crawler_ecr_repository_url" {
  value = aws_ecr_repository.crawler.repository_url
}

output "database_url_secret_arn" {
  value = aws_secretsmanager_secret.database_url.arn
}

output "backend_apprunner_url" {
  value = try(aws_apprunner_service.backend[0].service_url, null)
}

output "crawler_schedule_name" {
  value = try(aws_scheduler_schedule.crawler_daily[0].name, null)
}
