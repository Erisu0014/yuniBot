from pydantic import BaseSettings


class Config(BaseSettings):
    # Your Config Here
    bot_id: str
    bot_guild_id: str

    class Config:
        extra = "ignore"
