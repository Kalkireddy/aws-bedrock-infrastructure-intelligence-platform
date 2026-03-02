import json
import boto3
import logging
from datetime import datetime
import os

logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))

ec2_client = boto3.client('ec2')
sns_client = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')
ssm_client = boto3.client('ssm')

SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')
PARAMETER_STORE_PREFIX = os.getenv('PARAMETER_STORE_PREFIX', '/sre/dev')
DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE', 'sre-automation-resize-requests')

# Instance type upgrade path (for demo: only scale UP, t3.micro -> t3.small -> t3.medium)
INSTANCE_TYPE_UPGRADES = {
    't3.micro': 't3.small',
    't3.small': 't3.medium',
    't3.medium': 't3.large',
    't3.large': 't3.xlarge',
    't3.xlarge': 't3.2xlarge',
}


def get_approved_resize_requests():
    """Get all approved resize requests from DynamoDB"""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        # Note: In production, would use GSI for status-based queries
        # For now, scan and filter
        response = table.scan(
            FilterExpression='#status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':status': 'approved'}
        )
        
        items = response.get('Items', [])
        logger.info(f"Found {len(items)} approved resize requests")
        
        return items
    except Exception as e:
        logger.error(f"Error querying DynamoDB: {str(e)}")
        return []


def get_current_instance_type(instance_id):
    """Get current instance type"""
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance_type = response['Reservations'][0]['Instances'][0]['InstanceType']
        logger.info(f"Instance {instance_id} current type: {instance_type}")
        return instance_type
    except Exception as e:
        logger.error(f"Error getting instance type: {str(e)}")
        return None


def stop_instance(instance_id):
    """Stop EC2 instance"""
    try:
        ec2_client.stop_instances(InstanceIds=[instance_id])
        logger.info(f"Stopped instance {instance_id}")
        return True
    except Exception as e:
        logger.error(f"Error stopping instance: {str(e)}")
        return False


def change_instance_type(instance_id, new_instance_type):
    """Change instance type"""
    try:
        ec2_client.modify_instance_attribute(
            InstanceId=instance_id,
            InstanceType={'Value': new_instance_type}
        )
        logger.info(f"Changed instance type to {new_instance_type}")
        return True
    except Exception as e:
        logger.error(f"Error changing instance type: {str(e)}")
        return False


def start_instance(instance_id):
    """Start EC2 instance"""
    try:
        ec2_client.start_instances(InstanceIds=[instance_id])
        logger.info(f"Started instance {instance_id}")
        return True
    except Exception as e:
        logger.error(f"Error starting instance: {str(e)}")
        return False


def wait_for_state(instance_id, target_state, max_attempts=60):
    """Wait for instance to reach target state"""
    attempts = 0
    while attempts < max_attempts:
        try:
            response = ec2_client.describe_instances(InstanceIds=[instance_id])
            current_state = response['Reservations'][0]['Instances'][0]['State']['Name']
            
            if current_state == target_state:
                logger.info(f"Instance {instance_id} reached state {target_state}")
                return True
            
            logger.info(f"Waiting for {instance_id} to reach {target_state}... (current: {current_state})")
            attempts += 1
            
        except Exception as e:
            logger.error(f"Error checking instance state: {str(e)}")
        
        # In Lambda context, we have limited time. Return after reasonable wait.
        if attempts >= 10:
            logger.warning(f"Reached max attempts waiting for {target_state}")
            return False
    
    return False


def resize_instance(instance_id):
    """Execute instance resize: stop -> change type -> start"""
    try:
        logger.info(f"Starting resize process for {instance_id}")
        
        current_type = get_current_instance_type(instance_id)
        if not current_type:
            raise ValueError(f"Could not determine instance type for {instance_id}")
        
        # Get target instance type
        new_type = INSTANCE_TYPE_UPGRADES.get(current_type)
        if not new_type:
            logger.warning(f"No upgrade path defined for {current_type}")
            return {
                'success': False,
                'instance_id': instance_id,
                'reason': f'No upgrade path for {current_type}'
            }
        
        logger.info(f"Upgrade path: {current_type} -> {new_type}")
        
        # 1. Stop instance
        if not stop_instance(instance_id):
            raise Exception("Failed to stop instance")
        
        # 2. Wait for stopped state
        if not wait_for_state(instance_id, 'stopped'):
            logger.warning(f"Instance {instance_id} may not be fully stopped, continuing anyway")
        
        # 3. Change instance type
        if not change_instance_type(instance_id, new_type):
            raise Exception("Failed to change instance type")
        
        # 4. Start instance
        if not start_instance(instance_id):
            raise Exception("Failed to start instance")
        
        # 5. Wait for running state
        if not wait_for_state(instance_id, 'running'):
            logger.warning(f"Instance {instance_id} may not be fully running")
        
        logger.info(f"Successfully resized {instance_id} from {current_type} to {new_type}")
        
        return {
            'success': True,
            'instance_id': instance_id,
            'previous_type': current_type,
            'new_type': new_type
        }
        
    except Exception as e:
        logger.error(f"Error resizing instance: {str(e)}")
        return {
            'success': False,
            'instance_id': instance_id,
            'error': str(e)
        }


def update_resize_request_status(instance_id, status, details):
    """Update resize request status in DynamoDB"""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        # For simplicity, update the latest request for this instance
        response = table.query(
            KeyConditionExpression='instance_id = :iid',
            ExpressionAttributeValues={':iid': instance_id},
            ScanIndexForward=False,
            Limit=1
        )
        
        if response['Items']:
            item = response['Items'][0]
            table.update_item(
                Key={
                    'instance_id': item['instance_id'],
                    'timestamp': item['timestamp']
                },
                UpdateExpression='SET #status = :status, #updated = :updated, #details = :details',
                ExpressionAttributeNames={
                    '#status': 'status',
                    '#updated': 'updated_at',
                    '#details': 'resize_details'
                },
                ExpressionAttributeValues={
                    ':status': status,
                    ':updated': datetime.utcnow().isoformat(),
                    ':details': details
                }
            )
            logger.info(f"Updated resize request status to {status}")
            return True
    except Exception as e:
        logger.error(f"Error updating resize request: {str(e)}")
    
    return False


def send_notification(instance_id, status, details):
    """Send SNS notification"""
    try:
        message = {
            'notification_type': 'resize-completion',
            'instance_id': instance_id,
            'status': status,
            'timestamp': datetime.utcnow().isoformat(),
            'details': details
        }
        
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"SRE Automation: Resize {status.upper()} for {instance_id}",
            Message=json.dumps(message, indent=2, default=str),
            MessageAttributes={
                'notification_type': {
                    'DataType': 'String',
                    'StringValue': 'resize-completion'
                }
            }
        )
        logger.info(f"Notification sent")
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")


def lambda_handler(event, context):
    """
    Maintenance window Lambda handler
    Triggered by EventBridge at 2 AM UTC daily
    """
    logger.info(f"Maintenance window triggered at {datetime.utcnow().isoformat()}")
    
    try:
        # Get all approved resize requests
        approved_requests = get_approved_resize_requests()
        
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_requests': len(approved_requests),
            'executed': [],
            'failed': []
        }
        
        for request in approved_requests:
            instance_id = request['instance_id']
            logger.info(f"Processing resize for {instance_id}")
            
            # Execute resize
            resize_result = resize_instance(instance_id)
            
            if resize_result['success']:
                # Update status
                update_resize_request_status(instance_id, 'completed', resize_result)
                
                # Send notification
                send_notification(instance_id, 'completed', resize_result)
                
                results['executed'].append(resize_result)
                
            else:
                # Mark as failed
                update_resize_request_status(instance_id, 'failed', resize_result)
                
                # Send notification
                send_notification(instance_id, 'failed', resize_result)
                
                results['failed'].append(resize_result)
        
        logger.info(f"Maintenance window complete: {json.dumps(results, default=str)}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(results, default=str)
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
