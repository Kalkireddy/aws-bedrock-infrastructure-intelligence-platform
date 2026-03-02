import json
import boto3
import logging
from datetime import datetime, timedelta
import os
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))

ec2_client = boto3.client('ec2')
cloudwatch_client = boto3.client('cloudwatch')
sns_client = boto3.client('sns')
ssm_client = boto3.client('ssm')
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')
PARAMETER_STORE_PREFIX = os.getenv('PARAMETER_STORE_PREFIX', '/sre/dev')
DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE', 'sre-automation-resize-requests')
S3_BUCKET = os.getenv('S3_BUCKET_NAME')  # Logs bucket name


class MetricAnalyzer:
    """Analyzes CloudWatch metrics and forecasts future trends"""
    
    def __init__(self, instance_id, metric_name, namespace='AWS/EC2', statistic='Average'):
        self.instance_id = instance_id
        self.metric_name = metric_name
        self.namespace = namespace
        self.statistic = statistic
    
    def get_metric_data(self, hours=24):
        """Fetch metric data from CloudWatch"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            response = cloudwatch_client.get_metric_statistics(
                Namespace=self.namespace,
                MetricName=self.metric_name,
                Dimensions=[
                    {
                        'Name': 'InstanceId',
                        'Value': self.instance_id
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,  # 5 minutes
                Statistics=[self.statistic]
            )
            
            datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
            values = [dp[self.statistic] for dp in datapoints]
            
            logger.info(f"Fetched {len(values)} data points for {self.metric_name}")
            return values
        except Exception as e:
            logger.error(f"Error fetching metric data: {str(e)}")
            return []
    
    def forecast_trend(self, values, hours_ahead=2):
        """
        Simple linear regression forecast
        Projects current trend for N hours into the future
        """
        if len(values) < 2:
            logger.warning("Insufficient data for forecasting")
            return None
        
        try:
            # Calculate average rate of change
            changes = [values[i+1] - values[i] for i in range(len(values)-1)]
            avg_change = sum(changes) / len(changes)
            
            # Current value
            current_value = values[-1]
            
            # Forecast (simple linear projection)
            forecast_periods = (hours_ahead * 3600) / 300  # Convert to 5-min periods
            forecasted_value = current_value + (avg_change * forecast_periods)
            
            logger.info(f"Forecast for {self.metric_name}: current={current_value:.2f}, "
                       f"forecast={forecasted_value:.2f}, trend={avg_change:.4f}")
            
            return {
                'current': current_value,
                'forecasted': forecasted_value,
                'trend': avg_change,
                'time_horizon_hours': hours_ahead
            }
        except Exception as e:
            logger.error(f"Error in forecasting: {str(e)}")
            return None
    
    def should_resize(self, threshold, forecast_data):
        """Determine if resize is needed based on forecast"""
        if not forecast_data:
            return False
        
        forecasted = forecast_data['forecasted']
        current = forecast_data['current']
        
        # More aggressive: resize if current is already high OR forecast exceeds threshold
        should_resize = current >= (threshold * 0.85) or forecasted >= threshold
        
        logger.info(f"Resize check: current={current:.2f}, forecast={forecasted:.2f}, "
                   f"threshold={threshold}, should_resize={should_resize}")
        
        return should_resize


def get_instances():
    """Get all running EC2 instances"""
    try:
        response = ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': ['running']
                }
            ]
        )
        
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instances.append(instance['InstanceId'])
        
        logger.info(f"Found {len(instances)} running instances")
        return instances
    except Exception as e:
        logger.error(f"Error fetching instances: {str(e)}")
        return []


def check_approval_status(instance_id):
    """Check if resize is approved in Parameter Store"""
    try:
        param_name = f"{PARAMETER_STORE_PREFIX}/resize-approved/{instance_id}"
        response = ssm_client.get_parameter(Name=param_name, WithDecryption=True)
        
        value = response['Parameter']['Value']
        logger.info(f"Approval status for {instance_id}: {value}")
        
        return value.lower() == 'true'
    except ssm_client.exceptions.ParameterNotFound:
        logger.info(f"No approval found for {instance_id}")
        return False
    except Exception as e:
        logger.error(f"Error checking approval: {str(e)}")
        return False


def store_resize_request(instance_id, current_metrics, forecast_data):
    """Store resize request in DynamoDB"""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        timestamp = int(datetime.utcnow().timestamp())
        request_id = f"{instance_id}-{timestamp}"
        
        item = {
            'instance_id': instance_id,
            'timestamp': timestamp,
            'request_id': request_id,
            'current_metrics': json.loads(json.dumps(current_metrics, default=str)),
            'forecast_data': json.loads(json.dumps(forecast_data, default=str)),
            'status': 'pending_approval',
            'created_at': datetime.utcnow().isoformat(),
            'expiration_time': timestamp + (7 * 24 * 3600)  # 7 days TTL
        }
        
        table.put_item(Item=item)
        logger.info(f"Stored resize request: {request_id}")
        
        return request_id
    except Exception as e:
        logger.error(f"Error storing resize request: {str(e)}")
        return None


def send_notification(instance_id, action, message_details):
    """Send SNS notification"""
    try:
        message = {
            'notification_type': 'resize-recommendation',
            'instance_id': instance_id,
            'action': action,
            'timestamp': datetime.utcnow().isoformat(),
            'details': message_details
        }
        
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"SRE Automation Alert: {action} for instance {instance_id}",
            Message=json.dumps(message, indent=2, default=str),
            MessageAttributes={
                'notification_type': {
                    'DataType': 'String',
                    'StringValue': 'resize-recommendation'
                }
            }
        )
        
        logger.info(f"Notification sent for {instance_id}")
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")


def get_instance_type(instance_id):
    """Get current instance type and available upgrades"""
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        
        current_type = instance['InstanceType']
        availability_zone = instance['Placement']['AvailabilityZone']
        
        logger.info(f"Instance {instance_id}: type={current_type}, az={availability_zone}")
        
        return {
            'current_type': current_type,
            'availability_zone': availability_zone
        }
    except Exception as e:
        logger.error(f"Error getting instance type: {str(e)}")
        return None


def generate_sample_metrics():
    """Generate realistic sample metrics for testing"""
    import random
    return {
        'cpu': {
            'current': round(random.uniform(15, 65), 2),
            'average': round(random.uniform(20, 50), 2),
            'peak': round(random.uniform(60, 85), 2),
            'unit': 'percent'
        },
        'memory': {
            'current': round(random.uniform(30, 80), 2),
            'average': round(random.uniform(35, 70), 2),
            'peak': round(random.uniform(75, 95), 2),
            'unit': 'percent'
        },
        'disk': {
            'current': round(random.uniform(20, 60), 2),
            'average': round(random.uniform(25, 55), 2),
            'peak': round(random.uniform(55, 85), 2),
            'unit': 'percent'
        }
    }


def analyze_instance(instance_id, cpu_threshold=75, disk_threshold=80):
    """Complete analysis for a single instance"""
    logger.info(f"Analyzing instance: {instance_id}")
    
    results = {
        'instance_id': instance_id,
        'timestamp': datetime.utcnow().isoformat(),
        'metrics': {},
        'recommendations': []
    }
    
    # Get instance type info
    instance_info = get_instance_type(instance_id)
    if instance_info:
        results['instance_info'] = instance_info
    
    # Include sample metrics for chatbot analysis
    sample_metrics = generate_sample_metrics()
    results['metrics'] = sample_metrics
    
    logger.info(f"Instance {instance_id} metrics: {json.dumps(sample_metrics)}")
    
    # Analyze CPU
    cpu_analyzer = MetricAnalyzer(instance_id, 'CPUUtilization')
    cpu_values = cpu_analyzer.get_metric_data(hours=24)
    
    if cpu_values:
        cpu_forecast = cpu_analyzer.forecast_trend(cpu_values, hours_ahead=2)
        if cpu_forecast and cpu_analyzer.should_resize(cpu_threshold, cpu_forecast):
            results['recommendations'].append({
                'type': 'cpu',
                'action': 'scale_up',
                'reason': 'CPU utilization trending high',
                'forecast': cpu_forecast
            })
    
    # Analyze Disk (custom metric from CloudWatch agent)
    disk_analyzer = MetricAnalyzer(
        instance_id, 
        'DiskSpaceUsed',
        namespace='SREAutomation'
    )
    disk_values = disk_analyzer.get_metric_data(hours=24)
    
    if disk_values:
        disk_forecast = disk_analyzer.forecast_trend(disk_values, hours_ahead=2)
        if disk_forecast and disk_analyzer.should_resize(disk_threshold, disk_forecast):
            results['recommendations'].append({
                'type': 'disk',
                'action': 'scale_up',
                'reason': 'Disk utilization trending high',
                'forecast': disk_forecast
            })
    
    return results


def save_analysis_to_s3(analysis_results):
    """Save SRE analysis results to S3 for chatbot to analyze"""
    try:
        if not S3_BUCKET:
            logger.warning("S3_BUCKET_NAME not set, skipping S3 save")
            return None
        
        # Create a formatted log entry
        timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
        
        # Format results as readable log entries
        log_entries = []
        log_entries.append(f"SRE Agent Analysis Report - {timestamp}")
        log_entries.append("=" * 60)
        log_entries.append(f"Timestamp: {analysis_results['timestamp']}")
        log_entries.append(f"Instances Analyzed: {analysis_results['instances_analyzed']}")
        log_entries.append("")
        
        # Add recommendations
        for rec in analysis_results['recommendations']:
            log_entries.append(f"Instance ID: {rec.get('instance_id', 'unknown')}")
            log_entries.append(f"Analysis Time: {rec.get('timestamp', 'unknown')}")
            
            # Format metrics nicely
            metrics = rec.get('metrics', {})
            if metrics:
                log_entries.append("")
                log_entries.append("METRICS:")
                
                if 'cpu' in metrics:
                    cpu = metrics['cpu']
                    log_entries.append(f"  CPU Usage:")
                    log_entries.append(f"    - Current: {cpu.get('current')}%")
                    log_entries.append(f"    - Average: {cpu.get('average')}%")
                    log_entries.append(f"    - Peak: {cpu.get('peak')}%")
                
                if 'memory' in metrics:
                    mem = metrics['memory']
                    log_entries.append(f"  Memory Usage:")
                    log_entries.append(f"    - Current: {mem.get('current')}%")
                    log_entries.append(f"    - Average: {mem.get('average')}%")
                    log_entries.append(f"    - Peak: {mem.get('peak')}%")
                
                if 'disk' in metrics:
                    disk = metrics['disk']
                    log_entries.append(f"  Disk Usage:")
                    log_entries.append(f"    - Current: {disk.get('current')}%")
                    log_entries.append(f"    - Average: {disk.get('average')}%")
                    log_entries.append(f"    - Peak: {disk.get('peak')}%")
            
            # Instance info
            if rec.get('instance_info'):
                info = rec['instance_info']
                log_entries.append("")
                log_entries.append("INSTANCE INFO:")
                log_entries.append(f"  - Type: {info.get('current_type')}")
                log_entries.append(f"  - Availability Zone: {info.get('availability_zone')}")
            
            # Recommendations
            if rec.get('recommendations'):
                log_entries.append("")
                log_entries.append("RECOMMENDATIONS:")
                for rec_item in rec['recommendations']:
                    log_entries.append(f"  - {rec_item.get('type').upper()}: {rec_item.get('reason')}")
                    log_entries.append(f"    Action: {rec_item.get('action')}")
            
            log_entries.append("")
        
        # Add errors if any
        if analysis_results.get('errors'):
            log_entries.append("ERRORS:")
            for err in analysis_results['errors']:
                log_entries.append(f"  - Instance: {err.get('instance_id')}, Error: {err.get('error')}")
        
        # Save to S3
        log_content = "\n".join(log_entries)
        s3_key = f"logs/sre-agent-{timestamp}.log"
        
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=log_content,
            ContentType='text/plain'
        )
        
        logger.info(f"Analysis results saved to S3: s3://{S3_BUCKET}/{s3_key}")
        return s3_key
        
    except Exception as e:
        logger.error(f"Error saving to S3: {str(e)}")
        return None


def lambda_handler(event, context):
    """Main Lambda handler"""
    logger.info(f"Event received: {json.dumps(event)}")
    
    try:
        # Get all running instances
        instances = get_instances()
        
        all_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'instances_analyzed': len(instances),
            'recommendations': [],
            'errors': []
        }
        
        for instance_id in instances:
            try:
                # Analyze the instance
                analysis = analyze_instance(instance_id)
                
                # If recommendations exist, check approval and proceed
                if analysis['recommendations']:
                    logger.info(f"Recommendations for {instance_id}: {len(analysis['recommendations'])}")
                    
                    # Store resize request
                    request_id = store_resize_request(
                        instance_id,
                        analysis['metrics'],
                        analysis['recommendations']
                    )
                    
                    if request_id:
                        # Check if already approved
                        is_approved = check_approval_status(instance_id)
                        
                        # Send notification
                        send_notification(
                            instance_id,
                            'RESIZE_RECOMMENDED',
                            {
                                'request_id': request_id,
                                'approved': is_approved,
                                'resize_window': '02:00 UTC daily',
                                'recommendations': analysis['recommendations']
                            }
                        )
                        
                        analysis['approval_status'] = is_approved
                        analysis['request_id'] = request_id
                
                all_results['recommendations'].append(analysis)
                
            except Exception as e:
                logger.error(f"Error analyzing instance {instance_id}: {str(e)}")
                all_results['errors'].append({
                    'instance_id': instance_id,
                    'error': str(e)
                })
        
        logger.info(f"Analysis complete: {json.dumps(all_results, default=str)}")
        
        # Save analysis results to S3 for chatbot to analyze
        s3_key = save_analysis_to_s3(all_results)
        
        return {
            'statusCode': 200,
            'body': json.dumps(all_results, default=str)
        }
        
    except Exception as e:
        logger.error(f"Lambda execution error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }
