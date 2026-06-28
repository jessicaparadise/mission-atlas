resource "aws_kinesis_stream" "telemetry" {
  name = "atlas-telemetry-dev"

  # On-demand mode: AWS auto-scales capacity, you pay per usage.
  # Perfect for spiky dev/test traffic — no shards to manage or pay for idle.
  stream_mode_details {
    stream_mode = "ON_DEMAND"
  }

  # How long records stay in the stream before aging out (hours).
  # 24h is the minimum; plenty for dev. Lets you replay recent data.
  retention_period = 24

  # Encrypt records at rest using AWS-managed KMS key.
  encryption_type = "KMS"
  kms_key_id      = "alias/aws/kinesis"
}

output "stream_name" {
  value       = aws_kinesis_stream.telemetry.name
  description = "Kinesis stream name for the producer to write to"
}

output "stream_arn" {
  value       = aws_kinesis_stream.telemetry.arn
  description = "Kinesis stream ARN"
}