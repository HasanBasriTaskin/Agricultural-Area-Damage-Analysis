from typing import Protocol, Optional
from ..entities import User

class IAuthProvider(Protocol):
    """
    Authentication Provider Interface
    Allows for Strategy Pattern implementation of different auth methods
    (e.g., Local JWT, NextAuth/Credentials, OAuth2/SSO)
    """
    
    async def authenticate(self, credentials: dict) -> Optional[User]:
        """
        Authenticate a user given a set of credentials.
        Returns the User entity if successful, None otherwise.
        """
        ...
    
    async def create_user(self, data: dict) -> User:
        """
        Register a new user.
        """
        ...

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by their email.
        """
        ...
