"""
Email Design Multi-Agent System

Architecture:
    DesignOrchestrator
        └── spawns N x EmailDesignAgent (concurrent)
                └── each produces 1 unique design

Each agent has a distinct "persona" that influences design choices:
    - Minimalist: Clean, whitespace-focused, typography-driven
    - Bold: Strong colors, large imagery, impactful CTAs
    - Elegant: Sophisticated, luxury feel, refined details
    - Playful: Fun, colorful, engaging animations
    - Editorial: Magazine-style, content-rich, storytelling
"""

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from abilities.text_completion import text_completion_ability

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================


class DesignPersona(Enum):
    """Design agent personas - each creates distinctly different designs"""

    MINIMALIST = "minimalist"
    BOLD = "bold"
    ELEGANT = "elegant"
    PLAYFUL = "playful"
    EDITORIAL = "editorial"


@dataclass
class EmailDesign:
    """Complete email design output"""

    design_id: str
    persona: str

    # Core Content
    subject_line: str
    preview_text: str
    headline: str
    body_copy: str
    cta_text: str
    cta_url: str

    # Visual Design
    color_scheme: Dict[str, str]  # primary, secondary, accent, background, text
    typography: Dict[str, str]  # heading_font, body_font, cta_font
    layout: str  # single_column, two_column, hero_image, etc.

    # HTML Output
    html_template: str

    # Metadata
    design_rationale: str
    target_audience: str
    estimated_engagement: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BrandIntelligence:
    """Parsed brand data from website intelligence"""

    brand_name: str
    brand_colors: List[str]
    brand_fonts: List[str]
    brand_tones: List[str]
    primary_usp: str
    secondary_usps: List[str]
    product_categories: List[str]
    featured_products: List[Dict[str, Any]]
    pricing_tier: str
    target_demographic: str
    cta_patterns: List[str]
    current_offers: List[str]

    @classmethod
    def from_intelligence_json(cls, data: Dict[str, Any]) -> "BrandIntelligence":
        """Parse from website_intelligence output"""
        return cls(
            brand_name=data.get(
                "brand_name", data.get("brand_identity", {}).get("name", "Brand")
            ),
            brand_colors=data.get(
                "brand_colors",
                data.get("brand_identity", {}).get("colors", ["#000000", "#FFFFFF"]),
            ),
            brand_fonts=data.get(
                "brand_fonts", data.get("brand_identity", {}).get("fonts", ["Arial"])
            ),
            brand_tones=data.get(
                "brand_tones", data.get("brand_voice", {}).get("tone", ["professional"])
            ),
            primary_usp=data.get(
                "primary_usp", data.get("value_propositions", {}).get("primary_usp", "")
            ),
            secondary_usps=data.get(
                "secondary_usps",
                data.get("value_propositions", {}).get("secondary_usps", []),
            ),
            product_categories=data.get(
                "product_categories", data.get("products", {}).get("categories", [])
            ),
            featured_products=data.get(
                "featured_products", data.get("products", {}).get("featured_items", [])
            ),
            pricing_tier=data.get(
                "pricing_tier",
                data.get("products", {}).get("pricing_tier", "mid-range"),
            ),
            target_demographic=data.get(
                "target_demographic",
                data.get("audience", {}).get("target_demographic", ""),
            ),
            cta_patterns=data.get(
                "cta_patterns",
                data.get("brand_voice", {}).get("cta_patterns", ["Shop Now"]),
            ),
            current_offers=data.get(
                "current_offers", data.get("promotions", {}).get("current_offers", [])
            ),
        )


# =============================================================================
# EMAIL DESIGN AGENT
# =============================================================================


class EmailDesignAgent:
    """
    Single design agent with a specific persona.
    Each agent generates one unique email design based on brand intelligence.
    """

    PERSONA_PROMPTS = {
        DesignPersona.MINIMALIST: """
You are a MINIMALIST email designer. Your philosophy:
- Less is more. Ruthlessly eliminate clutter.
- Generous whitespace creates elegance
- Typography is the hero - use font weight and size for hierarchy
- Limited color palette (2-3 colors max)
- Single, focused CTA
- Clean lines, no decorative elements
- Mobile-first, single column layout preferred
""",
        DesignPersona.BOLD: """
You are a BOLD email designer. Your philosophy:
- Make an immediate impact - grab attention in 2 seconds
- Strong, contrasting colors that pop
- Large, dramatic hero images
- Big, impossible-to-miss CTAs with action words
- Confident, direct copy - short sentences
- Dynamic layouts with visual tension
- High contrast between elements
""",
        DesignPersona.ELEGANT: """
You are an ELEGANT/LUXURY email designer. Your philosophy:
- Sophistication through restraint
- Refined typography - serifs for luxury feel
- Muted, sophisticated color palette
- High-quality imagery with editorial feel
- Generous margins and padding
- Subtle animations if any
- Premium feel in every detail
- Understated CTAs that don't scream
""",
        DesignPersona.PLAYFUL: """
You are a PLAYFUL email designer. Your philosophy:
- Energy and joy in every element
- Bright, vibrant color combinations
- Rounded shapes and friendly typography
- Emojis where appropriate
- Engaging, conversational copy
- Fun micro-interactions suggested
- Dynamic, asymmetric layouts
- Personality over perfection
""",
        DesignPersona.EDITORIAL: """
You are an EDITORIAL email designer. Your philosophy:
- Magazine-quality storytelling
- Content-rich with clear hierarchy
- Multi-column layouts for desktop
- Strong headlines that tell a story
- Mix of imagery and text blocks
- Pull quotes and callouts
- Reading experience over quick scanning
- Brand journalism approach
""",
    }

    def __init__(self, persona: DesignPersona, agent_id: Optional[str] = None):
        self.persona = persona
        self.agent_id = agent_id or f"agent_{persona.value}_{uuid.uuid4().hex[:8]}"
        self.logger = logging.getLogger(f"{__name__}.{self.agent_id}")

    def generate_design(
        self, brand: BrandIntelligence, campaign_goal: str
    ) -> EmailDesign:
        """Generate a complete email design based on brand intelligence"""
        self.logger.info(
            f"Agent {self.agent_id} ({self.persona.value}) starting design generation"
        )

        # Build the prompt
        prompt = self._build_design_prompt(brand, campaign_goal)

        # Call LLM
        response = text_completion_ability(prompt, role="executor", return_usage=False)

        # Parse response
        design = self._parse_design_response(response, brand)

        self.logger.info(
            f"Agent {self.agent_id} completed design: {design.subject_line[:50]}..."
        )
        return design

    def _build_design_prompt(self, brand: BrandIntelligence, campaign_goal: str) -> str:
        """Construct the design generation prompt"""
        persona_instruction = self.PERSONA_PROMPTS[self.persona]

        return f"""
{persona_instruction}

## YOUR TASK
Create a complete email design for the brand below. You must produce a UNIQUE design that reflects your {self.persona.value} design philosophy.

## BRAND INTELLIGENCE
- **Brand Name**: {brand.brand_name}
- **Brand Colors**: {", ".join(brand.brand_colors[:5])}
- **Brand Fonts**: {", ".join(brand.brand_fonts[:3]) if brand.brand_fonts else "Use appropriate fonts"}
- **Brand Tone**: {", ".join(brand.brand_tones)}
- **Primary USP**: {brand.primary_usp[:200] if brand.primary_usp else "Quality products"}
- **Secondary USPs**: {", ".join(brand.secondary_usps[:3])}
- **Product Categories**: {", ".join(brand.product_categories[:5])}
- **Pricing Tier**: {brand.pricing_tier}
- **Target Audience**: {brand.target_demographic or "Fashion-conscious consumers"}
- **CTA Patterns Used**: {", ".join(brand.cta_patterns[:3]) if brand.cta_patterns else "Shop Now"}
- **Current Offers**: {", ".join(brand.current_offers[:2]) if brand.current_offers else "None currently"}

## CAMPAIGN GOAL
{campaign_goal}

## REQUIRED OUTPUT FORMAT
Respond with a JSON object containing:

```json
{{
    "subject_line": "Compelling email subject (max 50 chars)",
    "preview_text": "Preview text that complements subject (max 90 chars)",
    "headline": "Main headline in email body",
    "body_copy": "2-3 paragraphs of email body content",
    "cta_text": "Call-to-action button text",
    "cta_url": "#shop-now",
    "color_scheme": {{
        "primary": "#hexcode",
        "secondary": "#hexcode",
        "accent": "#hexcode",
        "background": "#hexcode",
        "text": "#hexcode"
    }},
    "typography": {{
        "heading_font": "Font Name",
        "body_font": "Font Name",
        "cta_font": "Font Name"
    }},
    "layout": "single_column|two_column|hero_image|card_grid",
    "design_rationale": "Brief explanation of design choices (2-3 sentences)",
    "target_audience": "Specific audience segment this design targets",
    "estimated_engagement": "Expected performance (e.g., 'High open rate due to...')"
}}
```

IMPORTANT:
- Make your design DISTINCTLY {self.persona.value.upper()}
- Use brand colors but adapt them to your design philosophy
- The design must be professional and ready for production
- Output ONLY the JSON, no other text
"""

    def _parse_design_response(
        self, response: str, brand: BrandIntelligence
    ) -> EmailDesign:
        """Parse LLM response into EmailDesign object"""
        try:
            # Extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")

            data = json.loads(response[json_start:json_end])

            # Generate HTML template
            html = self._generate_html_template(data, brand)

            return EmailDesign(
                design_id=f"design_{self.persona.value}_{uuid.uuid4().hex[:8]}",
                persona=self.persona.value,
                subject_line=data.get("subject_line", "New Collection"),
                preview_text=data.get("preview_text", "Discover what's new"),
                headline=data.get("headline", "Welcome"),
                body_copy=data.get("body_copy", ""),
                cta_text=data.get("cta_text", "Shop Now"),
                cta_url=data.get("cta_url", "#"),
                color_scheme=data.get("color_scheme", {}),
                typography=data.get("typography", {}),
                layout=data.get("layout", "single_column"),
                html_template=html,
                design_rationale=data.get("design_rationale", ""),
                target_audience=data.get("target_audience", ""),
                estimated_engagement=data.get("estimated_engagement", ""),
            )

        except Exception as e:
            self.logger.error(f"Failed to parse design response: {e}")
            return self._generate_fallback_design(brand)

    def _generate_html_template(
        self, data: Dict[str, Any], brand: BrandIntelligence
    ) -> str:
        """Generate production-ready HTML email template"""
        colors = data.get("color_scheme", {})
        typography = data.get("typography", {})

        primary = colors.get(
            "primary", brand.brand_colors[0] if brand.brand_colors else "#000000"
        )
        secondary = colors.get("secondary", "#666666")
        accent = colors.get("accent", primary)
        background = colors.get("background", "#FFFFFF")
        text_color = colors.get("text", "#333333")

        heading_font = typography.get("heading_font", "Georgia, serif")
        body_font = typography.get("body_font", "Arial, sans-serif")

        # Clean body copy - convert newlines to paragraphs
        body_paragraphs = data.get("body_copy", "").split("\n\n")
        body_html = "".join(
            [
                f'<p style="margin: 0 0 16px 0; line-height: 1.6;">{p.strip()}</p>'
                for p in body_paragraphs
                if p.strip()
            ]
        )

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>{data.get("subject_line", "Email")}</title>
    <!--[if mso]>
    <style type="text/css">
        body, table, td {{font-family: Arial, sans-serif !important;}}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: {body_font};">
    <!-- Preview Text -->
    <div style="display: none; max-height: 0; overflow: hidden;">
        {data.get("preview_text", "")}
    </div>

    <!-- Email Container -->
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f4f4f4;">
        <tr>
            <td align="center" style="padding: 40px 20px;">

                <!-- Email Content -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="background-color: {background}; border-radius: 8px; overflow: hidden;">

                    <!-- Header -->
                    <tr>
                        <td style="background-color: {primary}; padding: 30px 40px; text-align: center;">
                            <h1 style="margin: 0; color: {background}; font-family: {heading_font}; font-size: 28px; font-weight: 700;">
                                {brand.brand_name}
                            </h1>
                        </td>
                    </tr>

                    <!-- Hero Section -->
                    <tr>
                        <td style="padding: 40px;">
                            <h2 style="margin: 0 0 20px 0; color: {primary}; font-family: {heading_font}; font-size: 32px; font-weight: 700; line-height: 1.2;">
                                {data.get("headline", "Welcome")}
                            </h2>

                            <div style="color: {text_color}; font-family: {body_font}; font-size: 16px;">
                                {body_html}
                            </div>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin: 30px 0;">
                                <tr>
                                    <td style="border-radius: 4px; background-color: {accent};">
                                        <a href="{data.get("cta_url", "#")}" target="_blank" style="display: inline-block; padding: 16px 32px; color: {background}; font-family: {body_font}; font-size: 16px; font-weight: 700; text-decoration: none; text-transform: uppercase; letter-spacing: 1px;">
                                            {data.get("cta_text", "Shop Now")}
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f8f8; padding: 30px 40px; text-align: center; border-top: 1px solid #e0e0e0;">
                            <p style="margin: 0 0 10px 0; color: {secondary}; font-family: {body_font}; font-size: 14px;">
                                &copy; {datetime.now().year} {brand.brand_name}. All rights reserved.
                            </p>
                            <p style="margin: 0; color: #999999; font-family: {body_font}; font-size: 12px;">
                                <a href="#unsubscribe" style="color: #999999; text-decoration: underline;">Unsubscribe</a> |
                                <a href="#preferences" style="color: #999999; text-decoration: underline;">Email Preferences</a>
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>'''

    def _generate_fallback_design(self, brand: BrandIntelligence) -> EmailDesign:
        """Generate a basic design if LLM fails"""
        self.logger.warning(f"Using fallback design for agent {self.agent_id}")

        return EmailDesign(
            design_id=f"design_fallback_{uuid.uuid4().hex[:8]}",
            persona=self.persona.value,
            subject_line=f"Discover What's New at {brand.brand_name}",
            preview_text="Explore our latest collection",
            headline="New Arrivals Just Dropped",
            body_copy="Discover our newest pieces, crafted with care for you.",
            cta_text="Shop Now",
            cta_url="#shop",
            color_scheme={
                "primary": brand.brand_colors[0] if brand.brand_colors else "#000000",
                "secondary": "#666666",
                "accent": brand.brand_colors[0] if brand.brand_colors else "#000000",
                "background": "#FFFFFF",
                "text": "#333333",
            },
            typography={
                "heading_font": "Georgia, serif",
                "body_font": "Arial, sans-serif",
                "cta_font": "Arial, sans-serif",
            },
            layout="single_column",
            html_template="<html><body>Fallback template</body></html>",
            design_rationale="Fallback design due to generation error",
            target_audience="General audience",
            estimated_engagement="Standard",
        )


# =============================================================================
# DESIGN ORCHESTRATOR
# =============================================================================


class DesignOrchestrator:
    """
    Orchestrates multiple design agents to generate diverse email designs.
    Can spawn N agents with different personas to run concurrently.
    """

    DEFAULT_PERSONAS = [
        DesignPersona.MINIMALIST,
        DesignPersona.BOLD,
        DesignPersona.ELEGANT,
    ]

    def __init__(
        self, num_designs: int = 3, personas: Optional[List[DesignPersona]] = None
    ):
        self.num_designs = num_designs
        self.personas = personas or self._select_personas(num_designs)
        self.agents: List[EmailDesignAgent] = []
        self.logger = logging.getLogger(f"{__name__}.orchestrator")

        # Initialize agents
        self._initialize_agents()

    def _select_personas(self, num_designs: int) -> List[DesignPersona]:
        """Select diverse personas for the requested number of designs"""
        all_personas = list(DesignPersona)

        if num_designs >= len(all_personas):
            return all_personas

        # Prioritize diversity: minimalist, bold, elegant as defaults
        priority_order = [
            DesignPersona.MINIMALIST,
            DesignPersona.BOLD,
            DesignPersona.ELEGANT,
            DesignPersona.PLAYFUL,
            DesignPersona.EDITORIAL,
        ]

        return priority_order[:num_designs]

    def _initialize_agents(self) -> None:
        """Create agent instances for each persona"""
        self.agents = [EmailDesignAgent(persona=persona) for persona in self.personas]
        self.logger.info(
            f"Initialized {len(self.agents)} design agents: {[a.persona.value for a in self.agents]}"
        )

    def generate_designs(
        self,
        brand_intelligence: Dict[str, Any],
        campaign_goal: str,
        parallel: bool = True,
    ) -> List[EmailDesign]:
        """
        Generate multiple email designs using all agents.

        Args:
            brand_intelligence: Output from website_intelligence_ability
            campaign_goal: What the email campaign should achieve
            parallel: If True, run agents concurrently

        Returns:
            List of EmailDesign objects from each agent
        """
        self.logger.info(f"Starting design generation with {len(self.agents)} agents")

        # Parse brand intelligence
        brand = BrandIntelligence.from_intelligence_json(brand_intelligence)

        designs: List[EmailDesign] = []

        if parallel:
            designs = self._generate_parallel(brand, campaign_goal)
        else:
            designs = self._generate_sequential(brand, campaign_goal)

        self.logger.info(f"Generated {len(designs)} designs successfully")
        return designs

    def _generate_parallel(
        self, brand: BrandIntelligence, campaign_goal: str
    ) -> List[EmailDesign]:
        """Run all agents concurrently using ThreadPoolExecutor"""
        designs = []

        with ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
            future_to_agent = {
                executor.submit(agent.generate_design, brand, campaign_goal): agent
                for agent in self.agents
            }

            for future in as_completed(future_to_agent):
                agent = future_to_agent[future]
                try:
                    design = future.result()
                    designs.append(design)
                except Exception as e:
                    self.logger.error(f"Agent {agent.agent_id} failed: {e}")

        return designs

    def _generate_sequential(
        self, brand: BrandIntelligence, campaign_goal: str
    ) -> List[EmailDesign]:
        """Run agents one by one (useful for debugging)"""
        designs = []

        for agent in self.agents:
            try:
                design = agent.generate_design(brand, campaign_goal)
                designs.append(design)
            except Exception as e:
                self.logger.error(f"Agent {agent.agent_id} failed: {e}")

        return designs


# =============================================================================
# REASONLOOP ABILITY WRAPPER
# =============================================================================


def email_design_ability(
    brand_intelligence_json: str,
    campaign_goal: str = "Promote new arrivals and drive sales",
    num_designs: int = 3,
    parallel: bool = True,
) -> str:
    """
    ReasonLoop ability wrapper for email design generation.

    Args:
        brand_intelligence_json: JSON string from website_intelligence_ability
        campaign_goal: What the campaign should achieve
        num_designs: Number of design variations to generate (default: 3)
        parallel: Run agents concurrently (default: True)

    Returns:
        JSON string with all designs and metadata
    """
    logger.info(
        f"Starting email design generation: {num_designs} designs, parallel={parallel}"
    )

    try:
        # Parse input
        if isinstance(brand_intelligence_json, str):
            brand_data = json.loads(brand_intelligence_json)
        else:
            brand_data = brand_intelligence_json

        # Create orchestrator and generate designs
        orchestrator = DesignOrchestrator(num_designs=num_designs)
        designs = orchestrator.generate_designs(
            brand_intelligence=brand_data,
            campaign_goal=campaign_goal,
            parallel=parallel,
        )

        # Format response
        response = {
            "success": True,
            "num_designs": len(designs),
            "campaign_goal": campaign_goal,
            "designs": [design.to_dict() for design in designs],
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "personas_used": [d.persona for d in designs],
                "parallel_execution": parallel,
            },
        }

        logger.info(f"Email design generation completed: {len(designs)} designs")
        return json.dumps(response, indent=2)

    except json.JSONDecodeError as e:
        error_response = {
            "success": False,
            "error": f"Invalid JSON input: {e}",
            "designs": [],
        }
        return json.dumps(error_response)

    except Exception as e:
        logger.error(f"Email design generation failed: {e}", exc_info=True)
        error_response = {"success": False, "error": str(e), "designs": []}
        return json.dumps(error_response)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def create_email_designs(
    brand_intelligence: Dict[str, Any],
    campaign_goal: str = "Promote new arrivals",
    num_designs: int = 3,
) -> List[EmailDesign]:
    """
    Convenience function for direct Python usage.

    Args:
        brand_intelligence: Dict from website_intelligence_ability
        campaign_goal: Campaign objective
        num_designs: Number of variations

    Returns:
        List of EmailDesign objects
    """
    orchestrator = DesignOrchestrator(num_designs=num_designs)
    return orchestrator.generate_designs(brand_intelligence, campaign_goal)


def save_designs_to_html(
    designs: List[EmailDesign], output_dir: str = "output/emails"
) -> List[str]:
    """
    Save email designs as HTML files.

    Args:
        designs: List of EmailDesign objects
        output_dir: Directory to save files

    Returns:
        List of file paths
    """
    import os

    os.makedirs(output_dir, exist_ok=True)

    paths = []
    for design in designs:
        filename = f"{design.design_id}.html"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(design.html_template)

        paths.append(filepath)
        logger.info(f"Saved design to {filepath}")

    return paths


# Register ability
if __name__ != "__main__":
    from abilities.ability_registry import register_ability

    register_ability("email-design", email_design_ability)
