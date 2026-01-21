"""
Request schemas - Pydantic models for API input validation
"""

from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class WebsiteIntelligenceRequest(BaseModel):
    """Request to analyze a website for email campaign intelligence"""

    url: HttpUrl = Field(..., description="Website URL to analyze")

    model_config = {"json_schema_extra": {"examples": [{"url": "https://th.cos.com"}]}}


class EmailDesignRequest(BaseModel):
    """Request to generate email designs from brand intelligence"""

    brand_intelligence: dict = Field(
        ..., description="Brand intelligence data from website analysis"
    )
    campaign_goal: str = Field(
        default="Promote new arrivals and drive sales", description="Campaign objective"
    )
    num_designs: int = Field(
        default=3, ge=1, le=5, description="Number of design variations (1-5)"
    )
    parallel: bool = Field(default=True, description="Run design agents in parallel")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "brand_intelligence": {
                        "brand_name": "COS",
                        "brand_colors": ["#000000", "#FFFFFF"],
                        "brand_tones": ["minimalist", "luxury"],
                    },
                    "campaign_goal": "Launch spring collection",
                    "num_designs": 3,
                    "parallel": True,
                }
            ]
        }
    }


class FullCampaignRequest(BaseModel):
    """Request for full pipeline: website analysis + email design generation"""

    website_url: HttpUrl = Field(..., description="Website URL to analyze")
    campaign_goal: str = Field(
        default="Promote new arrivals and drive conversions",
        description="Campaign objective",
    )
    num_designs: int = Field(
        default=3, ge=1, le=5, description="Number of design variations"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "website_url": "https://th.cos.com",
                    "campaign_goal": "Spring collection launch",
                    "num_designs": 3,
                }
            ]
        }
    }
