from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContractorCategory(str, Enum):
    PLUMBER = "plumber"
    ELECTRICIAN = "electrician"
    ROOFER = "roofer"
    HVAC = "hvac"
    PAINTER = "painter"
    CARPENTER = "carpenter"
    GENERAL_CONTRACTOR = "general_contractor"
    LANDSCAPER = "landscaper"
    MASON = "mason"
    MECHANIC = "mechanic"
    AUTO_REPAIR = "auto_repair"
    AUTO_BODY = "auto_body"
    TIRE_SHOP = "tire_shop"


CATEGORY_SEARCH_TERMS = {
    ContractorCategory.PLUMBER: ["plumber", "plumbing"],
    ContractorCategory.ELECTRICIAN: ["electrician", "electrical contractor"],
    ContractorCategory.ROOFER: ["roofer", "roofing contractor"],
    ContractorCategory.HVAC: ["hvac", "heating and cooling", "air conditioning"],
    ContractorCategory.PAINTER: ["painter", "painting contractor"],
    ContractorCategory.CARPENTER: ["carpenter", "carpentry"],
    ContractorCategory.GENERAL_CONTRACTOR: ["general contractor", "home builder"],
    ContractorCategory.LANDSCAPER: ["landscaper", "landscaping", "lawn care"],
    ContractorCategory.MASON: ["mason", "masonry", "concrete contractor"],
    ContractorCategory.MECHANIC: ["mechanic", "auto mechanic"],
    ContractorCategory.AUTO_REPAIR: ["auto repair", "car repair"],
    ContractorCategory.AUTO_BODY: ["auto body", "body shop", "collision repair"],
    ContractorCategory.TIRE_SHOP: ["tire shop", "tire dealer"],
}


class Location(BaseModel):
    id: Optional[int] = None
    name: str
    city: str
    state: str
    country: str = "USA"

    @property
    def search_string(self) -> str:
        return f"{self.city}, {self.state}"


DEFAULT_LOCATIONS = [
    Location(id=1, name="Berkeley County, WV", city="Martinsburg", state="WV"),
    Location(id=2, name="Jefferson County, WV", city="Charles Town", state="WV"),
    Location(id=3, name="Frederick County, VA", city="Winchester", state="VA"),
    Location(id=4, name="Washington County, MD", city="Hagerstown", state="MD"),
]


class Contractor(BaseModel):
    id: Optional[int] = None
    name: str  # Business name
    owner_name: Optional[str] = None  # Owner/contact person name
    category: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    source: str
    location_searched: str
    created_at: Optional[datetime] = None


class Job(BaseModel):
    id: Optional[int] = None
    location: str
    categories: List[str]
    status: JobStatus = JobStatus.PENDING
    total_found: int = 0
    progress: int = 0
    total_categories: int = 0
    current_category: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobCreate(BaseModel):
    location: str
    categories: List[str]
    thread_count: int = 3


class JobResponse(BaseModel):
    id: int
    location: str
    categories: List[str]
    status: str
    total_found: int
    progress: int
    total_categories: int
    current_category: Optional[str]
    error_message: Optional[str]
    created_at: str
    completed_at: Optional[str]


class ContractorResponse(BaseModel):
    id: int
    name: str
    owner_name: Optional[str]
    category: str
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    website: Optional[str]
    source: str
    location_searched: str
    created_at: str


class PaginatedContractors(BaseModel):
    items: List[ContractorResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class StatsResponse(BaseModel):
    total_contractors: int
    with_owner: int
    with_phone: int
    with_email: int
    total_jobs: int
    active_jobs: int
    categories_breakdown: dict
