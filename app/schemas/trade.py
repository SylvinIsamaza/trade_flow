from pydantic import BaseModel, ConfigDict, field_serializer, field_validator, model_validator
from typing import Optional, List, Union
from datetime import datetime, time


class TradeBase(BaseModel):
    """Base trade schema."""
    model_config = ConfigDict(from_attributes=True)
    
    symbol: str
    side: str
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    close_price: Optional[float] = None
    quantity: Optional[float] = None
    pnl: Optional[float] = None
    commission: float = 0
    swap: float = 0
    duration: Optional[str] = None
    trade_type: Optional[str] = None
    execution_type: Optional[str] = None
    status: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    setups: Optional[List[str]] = None
    general_tags: Optional[List[str]] = None
    exit_tags: Optional[List[str]] = None
    process_tags: Optional[List[str]] = None
    notes: Optional[str] = None
    executed_at: datetime
    closed_at: Optional[datetime] = None
    date: datetime
    time: Optional[str] = None  # Store as string HH:mm
    close_time: Optional[str] = None  # Store as string HH:mm
    
    @field_validator('time', 'close_time', mode='before')
    @classmethod
    def convert_time_to_string(cls, value: Optional[Union[str, time]]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, time):
            return value.strftime('%H:%M')
        return str(value)


class TradeCreate(TradeBase):
    """Schema for creating a new trade."""
    account_id: str


class TradeUpdate(BaseModel):
    """Schema for updating trade information."""
    symbol: Optional[str] = None
    side: Optional[str] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    close_price: Optional[float] = None
    quantity: Optional[float] = None
    pnl: Optional[float] = None
    commission: Optional[float] = None
    swap: Optional[float] = None
    duration: Optional[str] = None
    trade_type: Optional[str] = None
    execution_type: Optional[str] = None
    status: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    setups: Optional[List[str]] = None
    general_tags: Optional[List[str]] = None
    exit_tags: Optional[List[str]] = None
    process_tags: Optional[List[str]] = None
    notes: Optional[str] = None
    executed_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    date: Optional[datetime] = None
    time: Optional[str] = None
    close_time: Optional[str] = None


class TradeResponse(TradeBase):
    """Schema for trade response."""
    id: str
    account_id: str