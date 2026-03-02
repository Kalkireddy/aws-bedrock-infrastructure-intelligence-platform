#!/usr/bin/env python3
"""
Generate sample logs that mimic real application and database logs.
Used for testing the AI Chatbot Lambda function.
"""

import json
import random
import sys
from datetime import datetime, timedelta
import argparse
import boto3

# Log patterns
OPERATIONS = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'QUERY']
DBUSERS = ['appuser', 'analytics_user', 'root', 'backup_user', 'readonly_user', 'etl_user']
TABLES = ['customers', 'orders', 'products', 'transactions', 'logs', 'users', 'sessions']
ERRORS = [
    'Connection timeout',
    'Disk space exhausted',
    'Out of memory',
    'Deadlock detected',
    'Query timeout',
    'Connection refused',
    'Authentication failed',
    'Permission denied',
    'Index corruption detected',
    'Replication lag exceeded'
]

WARNINGS = [
    'Long running query detected',
    'Table fragmentation high',
    'Cache hit ratio low',
    'Slow query',
    'High CPU usage',
    'High memory usage'
]

def generate_database_logs(num_logs=100):
    """Generate realistic database logs"""
    logs = []
    now = datetime.utcnow()
    
    for i in range(num_logs):
        timestamp = now - timedelta(minutes=random.randint(0, 60))
        
        if random.random() > 0.05:  # 95% normal queries
            operation = random.choice(OPERATIONS)
            user = random.choice(DBUSERS)
            table = random.choice(TABLES)
            duration_ms = random.randint(10, 5000)
            
            log_entry = f"{timestamp.isoformat()} INFO [{user}] {operation} FROM {table} took {duration_ms}ms"
        else:  # 5% errors
            user = random.choice(DBUSERS)
            error = random.choice(ERRORS)
            log_entry = f"{timestamp.isoformat()} ERROR [DATABASE] {error} for user {user}"
        
        logs.append(log_entry)
    
    return logs

def generate_application_logs(num_logs=100):
    """Generate realistic application logs"""
    logs = []
    now = datetime.utcnow()
    
    endpoints = ['/api/users', '/api/orders', '/api/products', '/health', '/metrics']
    status_codes = [200, 201, 400, 404, 500, 503]
    
    for i in range(num_logs):
        timestamp = now - timedelta(minutes=random.randint(0, 60))
        
        if random.random() > 0.10:  # 90% successful requests
            endpoint = random.choice(endpoints)
            method = random.choice(['GET', 'POST', 'PUT', 'DELETE'])
            status = random.choice([200, 201, 204])
            duration_ms = random.randint(5, 1000)
            
            log_entry = f"{timestamp.isoformat()} {method} {endpoint} {status} {duration_ms}ms"
        else:  # 10% errors
            endpoint = random.choice(endpoints)
            method = random.choice(['GET', 'POST', 'PUT', 'DELETE'])
            status = random.choice([400, 404, 500, 503])
            error = random.choice(ERRORS)
            
            log_entry = f"{timestamp.isoformat()} ERROR {method} {endpoint} {status} - {error}"
        
        logs.append(log_entry)
    
    return logs

def generate_system_logs(num_logs=100):
    """Generate realistic system/infrastructure logs"""
    logs = []
    now = datetime.utcnow()
    
    for i in range(num_logs):
        timestamp = now - timedelta(minutes=random.randint(0, 60))
        
        if random.random() > 0.08:  # 92% normal operations
            cpu = random.randint(5, 80)
            memory = random.randint(10, 75)
            disk = random.randint(20, 90)
            
            log_entry = f"{timestamp.isoformat()} SYSTEM CPU:{cpu}% MEM:{memory}% DISK:{disk}%"
        else:  # 8% warnings/errors
            warning = random.choice(WARNINGS + ERRORS)
            log_entry = f"{timestamp.isoformat()} WARNING/ERROR {warning}"
        
        logs.append(log_entry)
    
    return logs

def generate_combined_logs(num_logs=100):
    """Generate combined logs from all sources"""
    db_logs = generate_database_logs(num_logs // 3)
    app_logs = generate_application_logs(num_logs // 3)
    sys_logs = generate_system_logs(num_logs // 3)
    
    all_logs = db_logs + app_logs + sys_logs
    random.shuffle(all_logs)
    
    return all_logs

def save_to_file(logs, filename):
    """Save logs to file"""
    with open(filename, 'w') as f:
        for log in logs:
            f.write(log + '\n')
    print(f"✓ Saved {len(logs)} log entries to {filename}")

def upload_to_s3(logs, bucket, key):
    """Upload logs to S3"""
    try:
        s3 = boto3.client('s3')
        logs_text = '\n'.join(logs)
        
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=logs_text.encode('utf-8'),
            ContentType='text/plain'
        )
        print(f"✓ Uploaded {len(logs)} log entries to s3://{bucket}/{key}")
        return True
    except Exception as e:
        print(f"✗ Error uploading to S3: {str(e)}")
        return False

def upload_to_cloudwatch(logs, log_group, log_stream):
    """Upload logs to CloudWatch"""
    try:
        logs_client = boto3.client('logs')
        
        # Create log group if needed
        try:
            logs_client.create_log_group(logGroupName=log_group)
            print(f"✓ Created log group: {log_group}")
        except logs_client.exceptions.ResourceAlreadyExistsException:
            pass
        
        # Create log stream
        try:
            logs_client.create_log_stream(
                logGroupName=log_group,
                logStreamName=log_stream
            )
        except logs_client.exceptions.ResourceAlreadyExistsException:
            pass
        
        # Upload logs
        events = [
            {
                'timestamp': int(datetime.utcnow().timestamp() * 1000) - (i * 1000),
                'message': log
            }
            for i, log in enumerate(reversed(logs))
        ]
        
        logs_client.put_log_events(
            logGroupName=log_group,
            logStreamName=log_stream,
            logEvents=events
        )
        
        print(f"✓ Uploaded {len(logs)} log entries to CloudWatch: {log_group}/{log_stream}")
        return True
    except Exception as e:
        print(f"✗ Error uploading to CloudWatch: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Generate sample logs for testing')
    parser.add_argument('--type', choices=['database', 'application', 'system', 'combined'],
                       default='combined', help='Type of logs to generate')
    parser.add_argument('--count', type=int, default=100, help='Number of log entries')
    parser.add_argument('--file', help='Save to file')
    parser.add_argument('--s3-bucket', help='Upload to S3 bucket')
    parser.add_argument('--s3-key', default='sample-logs.txt', help='S3 object key')
    parser.add_argument('--cloudwatch-group', help='Upload to CloudWatch log group')
    parser.add_argument('--cloudwatch-stream', default='sample-logs', help='CloudWatch log stream name')
    
    args = parser.parse_args()
    
    # Generate logs
    print(f"Generating {args.type} logs...")
    if args.type == 'database':
        logs = generate_database_logs(args.count)
    elif args.type == 'application':
        logs = generate_application_logs(args.count)
    elif args.type == 'system':
        logs = generate_system_logs(args.count)
    else:  # combined
        logs = generate_combined_logs(args.count)
    
    print(f"✓ Generated {len(logs)} log entries\n")
    
    # Save locally
    if args.file:
        save_to_file(logs, args.file)
    
    # Upload to S3
    if args.s3_bucket:
        upload_to_s3(logs, args.s3_bucket, args.s3_key)
    
    # Upload to CloudWatch
    if args.cloudwatch_group:
        upload_to_cloudwatch(logs, args.cloudwatch_group, args.cloudwatch_stream)
    
    # Print sample
    print("\n📋 Sample log entries:")
    for log in logs[:10]:
        print(f"  {log}")

if __name__ == '__main__':
    main()
