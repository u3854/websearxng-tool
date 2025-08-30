from typing import Literal, Optional, List
from pydantic import BaseModel, ConfigDict, Field, model_validator


class BaseSearch(BaseModel):
    def to_params(self) -> dict:
        """Return dict with correct aliases for requests.get(params=...)."""
        params = self.model_dump(by_alias=True, exclude_none=True)
        return params


class SearchQuery(BaseSearch):
    model_config = ConfigDict(validate_by_alias=True, validate_by_name=True)

    query: str = Field(..., alias="q", description="The search query string")
    time_range: Optional[Literal["day", "month", "year"]] = Field(
        None, description="Time range filter"
    )
    format: Literal["json"] = Field(
        "json", description="Output format, fixed to json for now"
    )


class WebSearch(BaseSearch):
    query: SearchQuery = Field(
        ..., description="Query object with respective search parameters"
    )
    full_content: bool = Field(
        False, description="Whether you want full text content from result urls"
    )
    max_results: int = Field(..., ge=3, le=10, description="Top n search results")


# output


class Result(BaseModel):
    url: str = Field(..., alias="href")
    title: str
    snippet: Optional[str] = Field(..., description="Short snippet from web page")
    full_content: Optional[str] = Field(
        None, description="Fully extracted text content from webpage"
    )

    @model_validator(mode="before")
    def handle_aliases(cls, values):
        if "body" in values:
            values["snippet"] = values["body"]
        elif "content" in values:
            values["snippet"] = values["content"]


class SearchResults(BaseModel):
    results: List[Result]
    query: Optional[SearchQuery] = None
    total_results: Optional[int] = None

    def report(self) -> str:
        """Combines all search results in a single string.

        Returns:
            str: Formated search results.
        """
        text = "---"
        for res in self.results:
            text += f"\nurl: {res.url}"
            if res.content:
                text += f"\ncontent: {res.full_content}"
            else:
                text += f"\ncontent snippet: {res.snippet}"
            text += "\n---"
        return text
