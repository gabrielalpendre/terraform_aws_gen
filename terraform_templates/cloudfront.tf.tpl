resource "aws_cloudfront_distribution" "from_import" {
  enabled             = local.config.enabled
  is_ipv6_enabled     = local.config.is_ipv6_enabled
  comment             = local.config.comment
  default_root_object = local.config.default_root_object
  price_class         = local.config.price_class
  web_acl_id          = local.config.web_acl_id != "" ? local.config.web_acl_id : null
  aliases             = try(toset(local.config.aliases), [])

  dynamic "origin" {
    for_each = { for o in local.config.origins : o.id => o }
    content {
      domain_name              = origin.value.domain_name
      origin_id                = origin.value.id
      origin_path              = lookup(origin.value, "origin_path", null)
      connection_attempts      = lookup(origin.value, "connection_attempts", 3)
      connection_timeout       = lookup(origin.value, "connection_timeout", 10)
      origin_access_control_id = lookup(origin.value, "origin_access_control_id", "") != "" ? origin.value.origin_access_control_id : null

      dynamic "origin_shield" {
        for_each = try(origin.value.origin_shield.enabled, false) ? [origin.value.origin_shield] : []
        content {
          enabled              = origin_shield.value.enabled
          origin_shield_region = try(origin_shield.value.origin_shield_region, null)
        }
      }

      dynamic "custom_header" {
        for_each = { for idx, h in try(origin.value.custom_headers.items, []) : idx => h }
        content {
          name  = custom_header.value.header_name
          value = custom_header.value.header_value
        }
      }

      dynamic "s3_origin_config" {
        for_each = lookup(origin.value, "s3_origin_config", null) != null ? [lookup(origin.value, "s3_origin_config", null)] : []
        content {
          origin_access_identity = s3_origin_config.value.origin_access_identity
        }
      }

      dynamic "custom_origin_config" {
        for_each = lookup(origin.value, "custom_origin_config", null) != null ? [lookup(origin.value, "custom_origin_config", null)] : []
        content {
          http_port                = coalesce(lookup(custom_origin_config.value, "http_port", null), lookup(custom_origin_config.value, "h_t_t_p_port", 80))
          https_port               = coalesce(lookup(custom_origin_config.value, "https_port", null), lookup(custom_origin_config.value, "h_t_t_p_s_port", 443))
          origin_protocol_policy   = custom_origin_config.value.origin_protocol_policy
          origin_ssl_protocols     = toset(try(custom_origin_config.value.origin_ssl_protocols.items, try(tolist(custom_origin_config.value.origin_ssl_protocols), [])))
          origin_read_timeout      = lookup(custom_origin_config.value, "origin_read_timeout", 30)
          origin_keepalive_timeout = lookup(custom_origin_config.value, "origin_keepalive_timeout", 5)
        }
      }
    }
  }

  default_cache_behavior {
    target_origin_id       = local.config.default_cache_behavior.target_origin_id
    viewer_protocol_policy = local.config.default_cache_behavior.viewer_protocol_policy
    allowed_methods        = try(local.config.default_cache_behavior.allowed_methods.items, ["GET", "HEAD", "OPTIONS"])
    cached_methods         = try(local.config.default_cache_behavior.cached_methods.items, ["GET", "HEAD", "OPTIONS"])
    compress               = try(local.config.default_cache_behavior.compress, true)
    min_ttl                = try(local.config.default_cache_behavior.min_ttl, 0)
    default_ttl            = try(local.config.default_cache_behavior.default_ttl, 86400)
    max_ttl                = try(local.config.default_cache_behavior.max_ttl, 31536000)

    dynamic "function_association" {
      for_each = try(local.config.default_cache_behavior.function_association.items, [])
      content {
        event_type   = function_association.value.event_type
        function_arn = function_association.value.function_arn
      }
    }

    dynamic "lambda_function_association" {
      for_each = try(local.config.default_cache_behavior.lambda_function_association.items, [])
      content {
        event_type   = lambda_function_association.value.event_type
        lambda_arn   = lambda_function_association.value.lambda_function_arn
        include_body = try(lambda_function_association.value.include_body, false)
      }
    }
  }

  dynamic "ordered_cache_behavior" {
    for_each = local.config.ordered_cache_behavior
    content {
      path_pattern           = ordered_cache_behavior.value.path_pattern
      target_origin_id       = ordered_cache_behavior.value.target_origin_id
      viewer_protocol_policy = ordered_cache_behavior.value.viewer_protocol_policy
      allowed_methods        = try(ordered_cache_behavior.value.allowed_methods.items, ["GET", "HEAD", "OPTIONS"])
      cached_methods         = try(ordered_cache_behavior.value.cached_methods.items, ["GET", "HEAD", "OPTIONS"])

      dynamic "function_association" {
        for_each = try(ordered_cache_behavior.value.function_association.items, [])
        content {
          event_type   = function_association.value.event_type
          function_arn = function_association.value.function_arn
        }
      }

      dynamic "lambda_function_association" {
        for_each = try(ordered_cache_behavior.value.lambda_function_association.items, [])
        content {
          event_type   = lambda_function_association.value.event_type
          lambda_arn   = lambda_function_association.value.lambda_function_arn
          include_body = try(lambda_function_association.value.include_body, false)
        }
      }
    }
  }

  dynamic "custom_error_response" {
    for_each = try(local.config.custom_error_responses, [])
    content {
      error_code            = custom_error_response.value.error_code
      response_code         = try(custom_error_response.value.response_code, null)
      response_page_path    = try(custom_error_response.value.response_page_path, null)
      error_caching_min_ttl = try(custom_error_response.value.error_caching_min_ttl, null)
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = local.config.restrictions.geo_restriction.restriction_type
      locations        = lookup(local.config.restrictions.geo_restriction, "items", [])
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = lookup(local.config.viewer_certificate, "cloudfront_default_certificate", null)
    acm_certificate_arn            = lookup(local.config.viewer_certificate, "acm_certificate_arn", null)
    ssl_support_method             = lookup(local.config.viewer_certificate, "ssl_support_method", null)
    minimum_protocol_version       = lookup(local.config.viewer_certificate, "minimum_protocol_version", "TLSv1")
  }

  tags = local.config.tags
}