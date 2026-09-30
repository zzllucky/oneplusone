import datetime as dt

from pydantic import BaseModel


class SettingsOut(BaseModel):
    daily_goal: int
    updated_at: dt.datetime


class SettingsUpdate(BaseModel):
    daily_goal: int
