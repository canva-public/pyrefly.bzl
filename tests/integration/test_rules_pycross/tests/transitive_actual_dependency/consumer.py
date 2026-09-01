from pydantic_core import SchemaValidator

validator = SchemaValidator({"type": "int"})
value: int = validator.validate_python("1")
