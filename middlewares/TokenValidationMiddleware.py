from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from utils.utils import decode_token


class TokenValidationMiddleware:
    
    async def __call__(self, request: Request, call_next):
        token = request.cookies.get("token")
        
        if not token:
            # Redirect to login
            return RedirectResponse(url="/login") 
        
        try:
            payload = decode_token(token)
        except HTTPException as e:
            return e
        
        response = await call_next(request)
        return response