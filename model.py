from typing import Literal, Optional, List
from pydantic import BaseModel, ConfigDict, Field


class BaseSearch(BaseModel):

    def to_params(self) -> dict:
        """Return dict with correct aliases for requests.get(params=...)."""
        params = self.model_dump(by_alias=True, exclude_none=True)
        return params



class SearchQuery(BaseSearch):

    model_config = ConfigDict(validate_by_alias=True, validate_by_name=True)

    query: str = Field(..., alias="q", description="The search query string")
    time_range: Optional[Literal["day", "month", "year"]] = Field(None, description="Time range filter")
    format: Literal["json"] = Field("json", description="Output format, fixed to json for now")


class WebSearch(BaseSearch):
    query: SearchQuery = Field(..., description="Query object with respective search parameters")
    full_content: bool = Field(False, description="Whether you want full text content from result urls")
    max_results: int = Field(..., ge=3, le=10, description="Top n search results")


# output

class Result(BaseModel):
    url: str
    title: str
    snippet: str = Field(..., description="Short snippet from web page")
    content: Optional[str] = Field(None, description="Fully extracted text content from webpage")


class SearchResults(BaseModel):
    results: List[Result]
    query: Optional[SearchQuery] = None
    total_results: Optional[int] = None