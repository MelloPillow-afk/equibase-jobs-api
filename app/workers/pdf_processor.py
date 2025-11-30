"""PDF processing worker for background tasks."""

import csv
import io
import logging
import re
from datetime import UTC, datetime

import pdfplumber

from app.database.jobs import get_job, update_job
from app.database.storage import download_pdf, upload_csv
from app.workers import async_celery_task

logger = logging.getLogger(__name__)

# Constants
VALID_SURFACES = ["Dirt", "Turf", "All Weather", "Tapeta"]
CSV_FIELDNAMES = [
    "Date",
    "Race #",
    "Surface",
    "Distance",
    "Jockey",
    "Trainer",
    "WIN",
    "PLACE",
    "SHOW",
]


# Parsing functions
def parse_header(text):
    """
    Parses the header to extract Track, Date, and Race number.
    Handles compressed spaces like "AQUEDUCT-January1,2025-Race1"

    Returns:
        tuple: (track, date_str, race_num) or (None, None, None) if not found
    """
    match = re.search(r"([A-Z\s\.]+?)\s*-\s*(.*?)\s*-\s*Race\s*(\d+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
    return None, None, None


def parse_distance_surface(text):
    """
    Parses the distance and surface from text.
    Handles compressed spaces like "Distance:SixFurlongsOnTheDirt"

    Returns:
        tuple: (distance, surface) or (None, None) if not found
    """
    match = re.search(r"Distance:\s*(.*?)\s*On\s*The\s*(.*)", text, re.IGNORECASE)
    if match:
        distance = match.group(1).strip()
        surface_raw = match.group(2).strip()

        # Identify surface type
        surface = "Unknown"
        for vs in VALID_SURFACES:
            if vs.lower() in surface_raw.lower():
                surface = vs
                break

        # Clean up distance (add spaces between capitalized words)
        if " " not in distance and len(distance) > 3:
            distance = re.sub(r"(?<!^)(?=[A-Z])", " ", distance)

        return distance, surface
    return None, None


def parse_trainers_footer(text):
    """
    Parses the Trainers footer section to extract trainer names by program number.
    Stops parsing when "Owners:" is encountered.

    Returns:
        dict: Mapping of program number (str) to trainer name (str)
    """
    trainer_map = {}
    # Capture text between "Trainers:" and "Owners:"
    # Use non-greedy match .*? and lookahead for Owners: or end of string
    match = re.search(r"Trainers:\s*(.*?)(?=\s*Owners:|$)", text, re.IGNORECASE | re.DOTALL)
    if match:
        content = match.group(1).replace("\n", " ")  # Handle multi-line entries
        entries = re.split(r"[;]", content)  # Split by semicolon
        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue
            # Look for "PGM - Name"
            # Regex: Start with digits (and optional letters), then hyphen, then rest.
            m = re.match(r"(\d+[A-Za-z]*)\s*-\s*(.*)", entry)
            if m:
                pgm = m.group(1)
                trainer = m.group(2).strip()
                if trainer.endswith("."):
                    trainer = trainer[:-1]

                # Format name: Ensure space after comma if missing
                if "," in trainer and ", " not in trainer:
                    trainer = trainer.replace(",", ", ")

                # Handle CamelCase in trainer name (e.g. BarreraIII -> Barrera III)
                # Also "Bond, H.James" -> "Bond, H. James"

                # CamelCase split
                # trainer_orig = trainer

                # Avoid splitting DeXxxx, McXxxx, MacXxxx, O'Xxxx
                # Use negative lookbehind?
                # (?<!\bDe)(?<!\bMc)(?<!\bMac)(?<!\bO')(?<=[a-z])(?=[A-Z])
                # But "De" might be start of string.
                # Let's try a simpler approach: Split, then fix if it was De/Mc/Mac.

                trainer = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", trainer)

                # Fix De Lauro -> DeLauro, Mc Cormack -> McCormack, etc.
                trainer = re.sub(r"\b(De|Mc|Mac|O)\s+([A-Z])", r"\1\2", trainer)

                # Space after period if followed by uppercase
                trainer = re.sub(r"\.(?=[A-Z])", ". ", trainer)

                trainer_map[pgm] = trainer
    return trainer_map


def extract_jockey_and_horse(text):
    """
    Extracts Horse Name and Jockey from a string like "HorseName(Jockey)".
    Handles nested parens and multiple paren groups by finding the last balanced group.

    Returns:
        tuple: (HorseName, Jockey) or (None, None)
    """
    if not text.endswith(")"):
        return None, None

    # Find the matching opening parenthesis for the last closing parenthesis
    balance = 0
    open_idx = -1
    for i in range(len(text) - 1, -1, -1):
        char = text[i]
        if char == ")":
            balance += 1
        elif char == "(":
            balance -= 1
            if balance == 0:
                open_idx = i
                break

    if open_idx != -1:
        jockey = text[open_idx + 1 : -1].strip()
        horse = text[:open_idx].strip()

        # Format jockey name: Ensure space after comma if missing
        if "," in jockey and ", " not in jockey:
            jockey = jockey.replace(",", ", ")

        # Handle CamelCase in jockey name (e.g. RodriguezCastro -> Rodriguez Castro)
        jockey = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", jockey)

        # Ensure space before '(' if missing
        if "(" in jockey and " (" not in jockey:
            jockey = jockey.replace("(", " (")

        return horse, jockey

    return None, None


def parse_horse_row(line):
    """
    Parses a single line to extract horse data (PGM and Jockey).

    Args:
        line: Text line to parse

    Returns:
        dict: {"pgm": str, "jockey": str} or None if not a valid horse row
    """
    line = line.strip()
    if not line:
        return None

    # Filter out wager lines
    if line.startswith("$") or "Pick" in line or "Double" in line or "Exacta" in line:
        return None

    parts = line.split()
    if not parts:
        return None

    # Find PGM: First token that looks like a PGM (digits, optionally followed by letters)
    # e.g. "1", "1A", "10"
    pgm = None
    pgm_idx = -1
    for i, part in enumerate(parts):
        # Allow 1A, 2B etc. Must start with digit.
        # Exclude purely alpha tokens or tokens with other chars (like dates 4Dec22)
        # Dates usually have 3 alpha chars in middle.
        # PGM is usually short (1-3 chars).
        if part[0].isdigit():
            # Check if it's a date-like string (e.g. 18Dec22)
            if re.search(r"\d+[A-Za-z]{3}\d+", part):
                continue
            # Check if it's a PGM (digits + optional suffix)
            if re.match(r"^\d+[A-Za-z]*$", part):
                pgm = part
                pgm_idx = i
                break

    if not pgm:
        return None

    # Safer: Look for the token immediately following PGM?
    # If PGM is index 0, check index 1.
    if len(parts) > pgm_idx + 1:
        candidate = parts[pgm_idx + 1]
        if "(" in candidate and ")" in candidate:
            horse, jockey = extract_jockey_and_horse(candidate)
            if horse and jockey and "," in jockey:
                return {"pgm": pgm, "jockey": jockey}

    # Fallback: Scan all tokens for one that looks like Horse(Jockey)
    for part in parts[pgm_idx + 1 :]:
        if "(" in part and part.endswith(")"):
            horse, jockey = extract_jockey_and_horse(part)
            if horse and jockey and "," in jockey:
                return {"pgm": pgm, "jockey": jockey}

    return None


def format_date(date_str):
    """
    Formats date string from PDF format to readable format.
    Handles dates with or without spaces (e.g., "January 1, 2025" or "January1,2023").

    Args:
        date_str: Date string from PDF (e.g., "January 1, 2025" or "January1,2023")

    Returns:
        str: Formatted date string or original if parsing fails
    """
    # Normalize date string by adding spaces if missing
    # Pattern: "January1,2023" -> "January 1, 2023"
    normalized = re.sub(r"([a-zA-Z]+)(\d+)", r"\1 \2", date_str)  # Add space between month and day
    normalized = re.sub(r"(\d+),(\d+)", r"\1, \2", normalized)  # Add space after comma
    return normalized


def extract_race_data_from_pdf(pdf_bytes: bytes) -> list:
    """
    Extracts race data from PDF bytes.

    Args:
        pdf_bytes: Binary content of the PDF file

    Returns:
        list: List of dictionaries containing race data
    """
    all_races = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True)
            if not text:
                continue

            # Parse header information
            track, date_str, race_num = parse_header(text)
            if not track:
                continue

            date = format_date(date_str)
            distance, surface = parse_distance_surface(text)
            trainer_map = parse_trainers_footer(text)

            # Collect horse rows
            horse_rows = []
            lines = text.split("\n")
            for line in lines:
                row_data = parse_horse_row(line)
                if row_data:
                    horse_rows.append(row_data)

            # Process collected rows (assume sorted by finish position)
            for i, row in enumerate(horse_rows):
                rank = i + 1
                win = 1 if rank == 1 else 0
                place = 1 if rank == 2 else 0
                show = 1 if rank == 3 else 0

                trainer = trainer_map.get(row["pgm"], "")

                all_races.append(
                    {
                        "Date": date,
                        "Race #": race_num,
                        "Surface": surface,
                        "Distance": distance,
                        "Jockey": row["jockey"],
                        "Trainer": trainer,
                        "WIN": win,
                        "PLACE": place,
                        "SHOW": show,
                    }
                )

    return all_races


def process_pdf_to_csv(pdf_data: bytes) -> bytes:
    """
    Process PDF data and convert to CSV format.

    Args:
        pdf_data: Binary content of the PDF file

    Returns:
        bytes: CSV data as bytes
    """
    # Extract race data from PDF
    race_data = extract_race_data_from_pdf(pdf_data)

    # Convert to CSV bytes
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDNAMES, quoting=csv.QUOTE_NONNUMERIC)
    writer.writeheader()
    writer.writerows(race_data)

    # Return as bytes
    return output.getvalue().encode("utf-8")


@async_celery_task(bind=True, name="process_pdf")
async def process_pdf(self, job_id: int):
    """
    Celery task to process a PDF file and generate CSV output.

    Args:
        job_id: ID of the job to process
    """
    logger.info(f"Starting PDF processing for job {job_id}")

    try:
        # Get job details
        job = await get_job(job_id)

        if not job or len(job) == 0:
            logger.error(f"Job {job_id} not found")
            raise ValueError(f"Job {job_id} not found")

        pdf_url = job.get("pdf_url")

        # Step 1: Download PDF from Supabase Storage
        logger.info(f"Downloading PDF from {pdf_url}")
        pdf_data = await download_pdf(pdf_url)

        # Step 2: Process PDF to CSV
        logger.info(f"Processing PDF for job {job_id}")
        csv_data = process_pdf_to_csv(pdf_data)

        # Step 3: Upload CSV to Supabase Storage
        csv_filename = f"public/job-{job_id}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.csv"
        logger.info(f"Uploading CSV to {csv_filename}")
        csv_url = await upload_csv(csv_filename, csv_data)

        # Step 4: Update job status to completed
        logger.info(f"Updating job {job_id} status to completed")
        await update_job(
            job_id=job_id, status="completed", download_url=csv_url, completed_at=datetime.now(UTC)
        )

        logger.info(f"Successfully completed processing job {job_id}")
        return {"job_id": job_id, "status": "completed", "csv_url": csv_url}

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)

        # Update job status to failed
        try:
            await update_job(
                job_id=job_id, status="failed", download_url=None, completed_at=datetime.now(UTC)
            )
        except Exception as update_error:
            logger.error(f"Failed to update job status: {str(update_error)}")

        # Re-raise the exception so Celery knows the task failed
        raise
