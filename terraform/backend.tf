terraform {
  # Using local backend for development/testing
  # To use S3 backend in production:
  # 1. Create S3 bucket: sre-automation-terraform-state
  # 2. Create DynamoDB table: terraform-locks
  # 3. Uncomment the backend block below and run: terraform init -migrate-state
  
  # backend "s3" {
  #   bucket         = "sre-automation-terraform-state"
  #   key            = "sre-automation/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-locks"
  # }
}
