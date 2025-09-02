from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    code: int
    message: str
    data: Optional[T] = None

    @classmethod
    def success_response(cls, data: T = None, message: str = "Success"):
        return cls(success=True, code=200, message=message, data=data)

    @classmethod
    def error_response(cls, message: str, code: int = 400):
        return cls(success=False, code=code, message=message, data=None)