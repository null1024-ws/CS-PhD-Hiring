"""Repository paths shared by pipeline scripts."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SCHOOLS_PATH = DATA_DIR / "schools.json"
LISTINGS_PATH = DATA_DIR / "listings.json"
AUDIT_PATH = DATA_DIR / "audit.json"
LLM_REVIEWS_PATH = DATA_DIR / "llm_reviews.json"
HOMEPAGE_OVERRIDES_PATH = DATA_DIR / "homepage_overrides.json"
RAW_DIR = DATA_DIR / "raw"
RAW_XHS = RAW_DIR / "xhs"
RAW_1P3A = RAW_DIR / "1p3a"
RAW_IMAGES = RAW_DIR / "images"
RAW_OCR = RAW_DIR / "ocr"
RAW_INDEX = RAW_DIR / "index.json"
RAW_1P3A_INDEX = RAW_1P3A / "index.json"
BUNDLES_DIR = DATA_DIR / "bundles"
PIS_DIR = DATA_DIR / "pis"
SITE_DIR = ROOT / "site"
SITE_DIST = SITE_DIR / "dist"
TESTS_DIR = ROOT / "tests"
FIXTURES_DIR = TESTS_DIR / "fixtures"


def ensure_dirs() -> None:
    for path in (RAW_XHS, RAW_1P3A, RAW_IMAGES, RAW_OCR, BUNDLES_DIR, PIS_DIR, SITE_DIST):
        path.mkdir(parents=True, exist_ok=True)
