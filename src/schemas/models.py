"""
Pydantic 数据验证模型
提供严格的输入/输出数据校验。
"""
from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ACIInput(BaseModel):
    date: datetime
    sales_area: float = Field(ge=0, description="商品房销售面积")
    inventory_area: float = Field(ge=0, description="商品房待售面积")
    aci: float = Field(ge=0, description="去化周期(月)")
    
    model_config = ConfigDict(from_attributes=True)

class FPIInput(BaseModel):
    date: datetime
    net_financing_cash_flow: float = Field(description="净融资现金流")
    ticker: str
    data_frequency: str = Field(description="数据频率")
    
    model_config = ConfigDict(from_attributes=True)

class LPRInput(BaseModel):
    date: datetime
    premium_rate: float = Field(ge=0, description="土地溢价率(%)")
    land_volume: float = Field(ge=0, description="土地成交面积")
    
    model_config = ConfigDict(from_attributes=True)

class CIResultSchema(BaseModel):
    date: datetime
    ci: float
    i_aci: int = Field(ge=0, le=1)
    i_fpi: int = Field(ge=0, le=1)
    i_lpr: int = Field(ge=0, le=1)
    weights: str
    status: Literal["strong", "weak", "none"]
    
    model_config = ConfigDict(from_attributes=True)
