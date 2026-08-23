from pydantic import BaseModel, ConfigDict, Field


class ExtractResponse(BaseModel):
    """The JSON shape that /v1/extract returns."""

    # extra="forbid" reject unknown keys instead of ignoring them.
    model_config = ConfigDict(extra='forbid')

    # the raw text OCR found?
    raw_text: str = Field(..., description="Raw text extracted from the document")
    # how many pages were OCR found
    num_pages: int = Field(..., ge=1, description="Number of pages processed")
