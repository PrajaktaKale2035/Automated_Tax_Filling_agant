"""
Server-Driven UI (SDUI) Schemas

Defines the Pydantic models for the UI components that the backend can instruct the frontend to render.
This allows the backend to dynamically control the layout and content of the dashboard.
"""
from pydantic import BaseModel, Field
from typing import List, Literal, Union, Dict, Any, Optional

class UIComponent(BaseModel):
    """
    Base model for any UI component.
    """
    type: str = Field(..., description="The type of component to render (e.g., 'Card', 'Button')")
    props: Dict[str, Any] = Field(default_factory=dict, description="Properties to pass to the Vue component")
    children: List['UIComponent'] = Field(default_factory=list, description="Nested child components")
    id: Optional[str] = Field(None, description="Unique identifier for the component")

class Screen(BaseModel):
    """
    Represents a full screen or page layout.
    """
    id: str
    title: str
    layout: Literal["single-column", "two-column", "bento-grid", "dashboard-layout"]
    components: List[UIComponent]

# Recursive self-reference for children (Pydantic v2 API).
UIComponent.model_rebuild()
