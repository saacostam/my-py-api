from dataclasses import dataclass


@dataclass
class User:
    id: str
    name: str


@dataclass
class UserWithPwHash(User):
    pw_hash: str
