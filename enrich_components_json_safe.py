import json
import re
import time
import argparse
from pathlib import Path

import requests

from config_keys import MOUSER_API_KEY


def normalize_part(part_number: str) -> str:
    if not part_number:
        return ""
    return re.sub(r"[^A-Z0-9]", "", part_number.upper())


def is_generic_part(part_number: str) -> bool:
    if not part_number:
        return True

    p = part_number.strip().upper()

    generic_prefixes = (
        "R", "C", "L", "D", "J", "P", "TP", "LED", "SW", "F", "X", "Y"
    )
    generic_exact = {
        "GND", "3V3", "5V", "12V", "24V", "VCC", "VIN", "USB", "HEADER",
        "CONN", "CONNECTOR", "TEST", "JUMPER"
    }

    if p in generic_exact:
        return True

    if any(word in p for word in ("HEADER", "CONN", "CONNECTOR", "JUMPER", "TERMINAL")):
        return True

    if p.startswith(generic_prefixes) and len(p) <= 6:
        return True

    return False


def query_mouser(part_number: str) -> dict | None:
    url = "https://api.mouser.com/api/v1/search/partnumber"
    payload = {
        "SearchByPartRequest": {
            "mouserPartNumber": part_number,
            "partSearchOptions": ""
        }
    }

    try:
        response = requests.post(
            url,
            params={"apiKey": MOUSER_API_KEY},
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return None

    parts = data.get("SearchResults", {}).get("Parts", [])
    if not parts:
        return None

    best = None
    target = normalize_part(part_number)

    for part in parts:
        mpn = (part.get("ManufacturerPartNumber") or "").strip()
        mouser_pn = (part.get("MouserPartNumber") or "").strip()

        score = 0
        if normalize_part(mpn) == target:
            score += 100
        elif target and target in normalize_part(mpn):
            score += 30

        if normalize_part(mouser_pn) == target:
            score += 80
        elif target and target in normalize_part(mouser_pn):
            score += 20

        if best is None or score > best["score"]:
            best = {
                "score": score,
                "manufacturer": part.get("Manufacturer") or "",
                "description": part.get("Description") or "",
                "datasheet_url": part.get("DataSheetUrl") or "",
                "manufacturer_part_number": mpn,
                "mouser_part_number": mouser_pn,
            }

    if not best:
        return None

    if best["score"] < 100:
        return None

    return best


def enrich_json(json_path: str, output_path: str | None = None, delay: float = 0.35) -> None:
    json_file = Path(json_path)
    if not json_file.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    with json_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    components = data.get("components", [])
    if not isinstance(components, list):
        raise ValueError("JSON must contain a 'components' list")

    updated_count = 0
    skipped_count = 0
    unresolved = []

    for component in components:
        part_number = (component.get("part_number") or "").strip()

        if not part_number or is_generic_part(part_number):
            skipped_count += 1
            unresolved.append({
                "part_number": part_number,
                "reason": "generic_or_empty"
            })
            continue

        manufacturer_missing = not (component.get("manufacturer") or "").strip()
        description_missing = not (component.get("description") or "").strip()
        datasheet_missing = not (component.get("datasheet_url") or "").strip()

        if not (manufacturer_missing or description_missing or datasheet_missing):
            continue

        print(f"Checking: {part_number}")
        result = query_mouser(part_number)

        if not result:
            skipped_count += 1
            unresolved.append({
                "part_number": part_number,
                "reason": "no_safe_match"
            })
            time.sleep(delay)
            continue

        changed = False

        if manufacturer_missing and result["manufacturer"]:
            component["manufacturer"] = result["manufacturer"]
            changed = True

        if description_missing and result["description"]:
            component["description"] = result["description"]
            changed = True

        if datasheet_missing and result["datasheet_url"]:
            component["datasheet_url"] = result["datasheet_url"]
            changed = True

        if changed:
            updated_count += 1
        else:
            skipped_count += 1
            unresolved.append({
                "part_number": part_number,
                "reason": "match_but_no_missing_fields_filled"
            })

        time.sleep(delay)

    if output_path is None:
        output_path = str(json_file.with_name(json_file.stem + "_safe_enriched.json"))

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    unresolved_path = str(Path(output_path).with_name(Path(output_path).stem + "_unresolved.json"))
    with open(unresolved_path, "w", encoding="utf-8") as f:
        json.dump({"unresolved": unresolved}, f, indent=2, ensure_ascii=False)

    print()
    print(f"Saved enriched JSON: {output_path}")
    print(f"Saved unresolved list: {unresolved_path}")
    print(f"Updated: {updated_count}")
    print(f"Skipped/unresolved: {skipped_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Safely enrich component JSON from Mouser.")
    parser.add_argument("json_file", help="Input JSON file")
    parser.add_argument("--output", help="Output JSON file")
    parser.add_argument("--delay", type=float, default=0.35, help="Delay between requests in seconds")
    args = parser.parse_args()

    enrich_json(args.json_file, args.output, args.delay)