class ValidationError(Exception):
    
    message: str
    validator: str
    validator_value: str
    path: str
    schema_path: str