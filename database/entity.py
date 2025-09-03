from dataclasses import dataclass
from typing import Any
import datetime

@dataclass 
class Paper:
    "An entity in the system like an author"
    title: str
    
    author: list[str] 
    
    doi: str
    
    date : datetime.date

    journal: str 

    subject: list[str] 

    attributes: dict[str , Any]
 

    @classmethod
    def from_dict(
        cls,
        d: dict[str, Any],
        title_key: str = "title",
        author_key: str = "author",
        doi_key: str = "doi",
        date_key: str = "date",
        journal_key: str = "journal",
        subject_key: str = "subject",
        attributes_key: str = "attributes",
    ) -> "Paper":
        
        """Create a new Paper from dict data."""
        # Handle date conversion if it's a string
        date_value = d[date_key]
        if isinstance(date_value, str):
            # Try common date formats
            try:
                date_value = datetime.datetime.fromisoformat(date_value).date()
            except ValueError:
                try:
                    date_value = datetime.datetime.strptime(date_value, "%Y-%m-%d").date()
                except ValueError:
                    raise ValueError(f"Unable to parse date: {date_value}")
        elif isinstance(date_value, datetime.datetime):
            date_value = date_value.date()
        
        return Paper(
            title=d[title_key],
            author=d[author_key],
            doi=d[doi_key],
            date=date_value,
            journal=d[journal_key],
            subject=d[subject_key],
            attributes=d.get(attributes_key, {}),
        )

    