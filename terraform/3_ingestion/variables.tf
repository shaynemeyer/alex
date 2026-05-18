variable "aws_region" {
  description = "AWS region for resources"
  type        = string
}

variable "sagemaker_endpoint_name" {
  description = "Name of the SageMaker endpoint"
  type        = string
}

variable "supabase_url" { 
  description = "The Supabase URL for the database"
  type = string 
  default = "" 
}

variable "supabase_service_key" { 
  description = "The service key for the Supabase database"
  type = string 
  default = "" 
}
