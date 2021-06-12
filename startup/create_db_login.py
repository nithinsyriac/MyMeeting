import boto3

def create_table(dynamodb=None):
    if not dynamodb:
        dynamodb = boto3.resource("dynamodb")
    
    table = dynamodb.create_table(
        TableName = "Music",
        KeySchema = [
            {
                "AttributeName": "partition_key",
                "KeyType": "HASH" 
            },
            {
                "AttributeName": "sort_key",
                "KeyType": "RANGE" 
            }
        ],
        AttributeDefinitions = [
            {
                "AttributeName": "partition_key",
                "AttributeType": "S"
            },
            {
                "AttributeName": "sort_key",
                "AttributeType": "S"
            },
        ],
        ProvisionedThroughput = {
            "ReadCapacityUnits": 10,
            "WriteCapacityUnits": 10
        }
    )
    return table

if __name__ == "__main__":
    music_table = create_table()
    