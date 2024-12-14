"""
API Gateway Module

Handles routing, request validation, and rate limiting for the Genesis Replicator Framework.
"""
from typing import Dict, Any, Optional, Callable, List
import logging
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
import jwt
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Route:
    """Represents an API route configuration."""
    path: str
    method: str
    handler: Callable
    requires_auth: bool = True
    rate_limit: Optional[int] = None  # requests per minute

class APIGateway:
    """Main API Gateway implementation."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        jwt_secret: str = "your-secret-key"
    ):
        """Initialize the API Gateway."""
        self.app = FastAPI(title="Genesis Replicator API")
        self.redis = redis.from_url(redis_url)
        self.jwt_secret = jwt_secret
        self.routes: List[Route] = []
        self._setup_middleware()
        self._setup_auth()
        logger.info("API Gateway initialized")

    def _setup_middleware(self) -> None:
        """Configure middleware for the API Gateway."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_auth(self) -> None:
        """Set up authentication for the API Gateway."""
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    async def validate_token(
        self,
        token: str = Depends(OAuth2PasswordBearer(tokenUrl="token"))
    ) -> Dict[str, Any]:
        """
        Validate JWT token.

        Args:
            token: JWT token to validate

        Returns:
            Token payload if valid

        Raises:
            HTTPException: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    async def check_rate_limit(
        self,
        request: Request,
        limit: int
    ) -> None:
        """
        Check rate limit for request.

        Args:
            request: FastAPI request object
            limit: Rate limit (requests per minute)

        Raises:
            HTTPException: If rate limit exceeded
        """
        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"

        current = self.redis.get(key)
        if current is None:
            self.redis.setex(key, 60, 1)
        else:
            current_count = int(current)
            if current_count >= limit:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded"
                )
            self.redis.incr(key)

    def register_route(self, route: Route) -> None:
        """
        Register a new API route.

        Args:
            route: Route configuration
        """
        async def route_handler(request: Request, response: Response):
            if route.requires_auth:
                token = await self.oauth2_scheme(request)
                await self.validate_token(token)

            if route.rate_limit:
                await self.check_rate_limit(request, route.rate_limit)

            return await route.handler(request)

        self.app.add_api_route(
            route.path,
            route_handler,
            methods=[route.method]
        )
        self.routes.append(route)
        logger.info(f"Registered route: {route.method} {route.path}")

    def get_routes(self) -> List[Route]:
        """
        Get all registered routes.

        Returns:
            List of registered routes
        """
        return self.routes

    async def start(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        """
        Start the API Gateway.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        import uvicorn
        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

    def add_error_handler(
        self,
        exc_class: type,
        handler: Callable
    ) -> None:
        """
        Add custom error handler.

        Args:
            exc_class: Exception class to handle
            handler: Handler function
        """
        self.app.add_exception_handler(exc_class, handler)
        logger.info(f"Added error handler for: {exc_class.__name__}")

    async def health_check(self) -> Dict[str, str]:
        """
        Health check endpoint.

        Returns:
            Health status
        """
        return {"status": "healthy"}
