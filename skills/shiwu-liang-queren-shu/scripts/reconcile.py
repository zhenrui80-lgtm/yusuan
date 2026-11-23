#!/usr/bin/env python3
"""Decimal material aggregation and independent two-form readback checks.

Standard library only. See ../references/data-model.md for the exact contract.
This does not extract files, infer evidence, convert units, or authorize policies.
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import hashlib
import json
import os
from pathlib import Path
import re
import sys

MODEL_SCHEMA = "physical-materials/1"
READBACK_SCHEMA = "physical-materials-readback/1"
DECIMAL_RE = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")


class ValidationError(ValueError):
    pass


class OutputConflict(ValidationError):
    pass


def require(ok, message):
    if not ok:
        raise ValidationError(message)


def obj(value, label):
    require(isinstance(value, dict), f"{label}: expected object")
    return value


def arr(value, label):
    require(isinstance(value, list), f"{label}: expected array")
    return value


def string(value, label):
    require(isinstance(value, str) and value and value == value.strip(),
            f"{label}: expected nonempty string without outer whitespace")
    return value


def refs(value, label, required=True):
    arr(value, label)
    require(not required or bool(value), f"{label}: evidence references required")
    for ref in value:
        string(ref, label)
    return value


def number(value, label, nullable=False):
    if value is None and nullable:
        return None
    require(isinstance(value, str) and bool(DECIMAL_RE.fullmatch(value)),
            f"{label}: expected nonnegative decimal STRING or allowed null")
    require(len(value.replace('.', '')) <= 36 and
            ('.' not in value or len(value.split('.')[1]) <= 18),
            f"{label}: supported limit is 36 digits and 18 decimal places")
    return Decimal(value)


def decimal_text(value):
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def pending(row, label):
    string(row.get("pending_reason"), label + ".pending_reason")


def specification(row, label):
    value = row.get("spec")
    if value is None or value == "":
        pending(row, label)
        return None
    return string(value, label + ".spec")


def indexed(rows, label):
    result = {}
    for index, row in enumerate(arr(rows, label)):
        obj(row, f"{label}[{index}]")
        identity = string(row.get("id"), f"{label}[{index}].id")
        require(identity not in result, f"{label}: duplicate id {identity}")
        result[identity] = row
    return result


def ledger_key(row):
    return (row["name"], row["spec"] or None, row["unit"], row["scope_key"])


def reconcile(model):
    """Return expected rows, never claim final artifacts were checked."""
    obj(model, "model")
    require(model.get("schema_version") == MODEL_SCHEMA, "unsupported model schema")
    decisions = obj(model.get("decisions"), "decisions")
    mode = decisions.get("ledger_mode")
    require(mode == "equal_adopted",
            f"ledger_mode={mode!r} unsupported: actual receipt/issue flows must not be forced equal; only equal_adopted is implemented")
    require(decisions.get("equal_adopted_authorized") is True,
            "equal_adopted requires explicit equal_adopted_authorized=true")
    require(decisions.get("dates") == "blank" and
            decisions.get("blank_dates_authorized") is True,
            "only explicitly authorized blank dates are supported")
    display = obj(model.get("display"), "display")
    require(display.get("rounding") == "ROUND_HALF_UP", "only ROUND_HALF_UP is supported")
    places = display.get("default_decimals")
    require(type(places) is int and 0 <= places <= 12, "default_decimals must be 0..12")
    unit_places = obj(display.get("unit_decimals"), "display.unit_decimals")
    for unit, count in unit_places.items():
        string(unit, "display.unit_decimals key")
        require(type(count) is int and 0 <= count <= 12, "unit decimals must be 0..12")

    works = indexed(model.get("works"), "works")
    require(bool(works), "works must not be empty")
    expected_works = []
    for identity, work in works.items():
        label = f"work {identity}"
        name = string(work.get("name"), label + ".name")
        unit = string(work.get("unit"), label + ".unit")
        qty = number(work.get("qty"), label + ".qty", nullable=True)
        if qty is None:
            pending(work, label)
        refs(work.get("source_refs"), label + ".source_refs")
        expected_works.append({"id": identity, "name": name, "unit": unit,
                               "qty": None if qty is None else decimal_text(qty)})

    owner_lines = indexed(model.get("owner_lines"), "owner_lines")
    for identity, line in owner_lines.items():
        label = f"owner_line {identity}"
        number(line.get("qty"), label + ".qty")
        string(line.get("unit"), label + ".unit")
        require(line.get("basis") in ("received", "issued"),
                label + ".basis must explicitly select received or issued")
        refs(line.get("source_refs"), label + ".source_refs")

    materials = indexed(model.get("materials"), "materials")
    contributions, excluded, groups, used_owner_lines = [], [], {}, {}
    # Inputs have at most 36 digits each; 100 digits retains products and sums
    # exactly for practical model sizes before the explicit display quantize.
    with localcontext() as context:
        context.prec = 100
        for identity, row in materials.items():
            label = f"material {identity}"
            work_ids = arr(row.get("work_ids"), label + ".work_ids")
            require(bool(work_ids) and all(isinstance(x, str) for x in work_ids),
                    label + ".work_ids must contain work ids")
            require(len(work_ids) == len(set(work_ids)), label + ": duplicate work_ids")
            require(all(x in works for x in work_ids), label + ": unknown work id")
            name = string(row.get("name"), label + ".name")
            unit = string(row.get("unit"), label + ".unit")
            scope = string(row.get("scope_key"), label + ".scope_key")
            spec = specification(row, label)
            refs(row.get("source_refs"), label + ".source_refs")
            refs(row.get("spec_refs"), label + ".spec_refs", required=spec is not None)
            kind = row.get("kind")
            require(kind in ("main", "auxiliary", "machine"), label + ": invalid kind")
            qty = number(row.get("qty"), label + ".qty", nullable=True)
            if qty is None:
                pending(row, label)
            basis = row.get("quantity_basis")
            require(basis in ("estimated", "owner_actual"), label + ": invalid quantity_basis")
            require(type(row.get("indivisible")) is bool, label + ".indivisible must be boolean")
            loss = obj(row.get("loss"), label + ".loss")
            rate = number(loss.get("rate"), label + ".loss.rate")
            require(rate <= 1, label + ": additional loss rate above 100% is unsupported")
            require(type(loss.get("already_in_quota")) is bool,
                    label + ".loss.already_in_quota must be boolean")
            refs(loss.get("refs"), label + ".loss.refs",
                 required=rate > 0 or loss["already_in_quota"])
            require(not loss["already_in_quota"] or rate == 0,
                    label + ": quota already contains loss; cannot add it again")
            if row["indivisible"]:
                require(rate == 0, label + ": indivisible finished items cannot add loss")
                require(qty is None or qty == qty.to_integral_value(),
                        label + ": indivisible quantity must already be an integer (do not round 8.08 to 8)")
            owner_id = row.get("owner_line_id")
            if basis == "owner_actual":
                require(qty is not None, label + ": owner_actual requires a known quantity")
                require(rate == 0, label + ": owner actual quantity cannot add loss")
                string(owner_id, label + ".owner_line_id")
                require(owner_id in owner_lines, label + ": owner_line_id not found")
                owner = owner_lines[owner_id]
                require(unit == owner["unit"], label + ": owner unit differs; evidence-backed conversion must be done upstream")
                allocation = refs(row.get("allocation_refs", []), label + ".allocation_refs", required=False)
                used_owner_lines.setdefault(owner_id, []).append({"id": identity, "qty": qty,
                                                                 "allocation_refs": allocation})
            else:
                require(owner_id is None, label + ": estimated row cannot claim an owner line")
            digits = 0 if row["indivisible"] else unit_places.get(unit, places)
            adopted = None if qty is None else qty * (1 + rate)
            shown = None if adopted is None else adopted.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
            result = {"id": identity, "work_ids": list(work_ids), "name": name,
                      "spec": spec, "unit": unit, "kind": kind, "scope_key": scope,
                      "base_qty": None if qty is None else decimal_text(qty),
                      "adopted_qty": None if adopted is None else decimal_text(adopted),
                      "display_qty": None if shown is None else format(shown, "f"),
                      "quantity_basis": basis, "owner_line_id": owner_id,
                      "pending_reason": row.get("pending_reason")}
            if kind == "auxiliary":
                excluded.append(result)
                continue
            contributions.append(result)
            if kind != "main":
                continue
            key = ledger_key(result)
            if key not in groups:
                groups[key] = {"name": name, "spec": spec, "unit": unit,
                               "scope_key": scope, "material_ids": [],
                               "indivisible": row["indivisible"], "digits": digits,
                               "subtotal": Decimal(0), "unknown_ids": []}
            group = groups[key]
            require(spec is not None or not group["material_ids"],
                    label + ": multiple unknown specifications cannot be merged; assign distinct scope_key values")
            require(group["indivisible"] == row["indivisible"],
                    label + ": same aggregate has conflicting indivisible flags")
            group["material_ids"].append(identity)
            if shown is None:
                group["unknown_ids"].append(identity)
            else:
                group["subtotal"] += shown
        allocations = {}
        for owner_id, uses in used_owner_lines.items():
            owner = owner_lines[owner_id]
            require(len(uses) == 1 or all(x["allocation_refs"] for x in uses),
                    f"owner line {owner_id} used multiple times without allocation_refs on every contribution")
            total = sum((x["qty"] for x in uses), Decimal(0))
            require(total == number(owner["qty"], "owner quantity"),
                    f"owner line {owner_id}: allocated quantity does not equal adopted source quantity")
            allocations[owner_id] = {"material_ids": [x["id"] for x in uses],
                                     "adopted_source_qty": owner["qty"], "unit": owner["unit"],
                                     "basis": owner["basis"], "allocated_qty": decimal_text(total),
                                     "split_evidence_required": len(uses) > 1}
        ledger = []
        for group in groups.values():
            known = format(group.pop("subtotal"), f".{group.pop('digits')}f")
            group.pop("indivisible")
            quantity_complete = not group["unknown_ids"]
            group.update({"known_subtotal": known, "quantity_complete": quantity_complete,
                          "complete": quantity_complete and group["spec"] is not None,
                          "qty": known if quantity_complete else None,
                          "in_qty": known if quantity_complete else None,
                          "out_qty": known if quantity_complete else None,
                          "in_date": "", "out_date": ""})
            ledger.append(group)
    return {"schema_version": "physical-materials-report/1", "model_valid": True,
            "artifact_verified": False, "complete":
            all(w["qty"] is not None for w in expected_works) and
            all(m["display_qty"] is not None and m["spec"] is not None for m in contributions),
            "decisions": dict(decisions),
            "confirmation": {"works": expected_works, "materials": contributions},
            "ledger": ledger, "excluded_auxiliary": excluded,
            "owner_line_allocations": allocations,
            "unused_owner_line_ids": sorted(set(owner_lines) - set(used_owner_lines)),
            "limits": ["Evidence references and ownership are not independently authenticated.",
                       "Base-quantity formulas, assumptions, full work scope and material matching are supplied upstream, not verified here.",
                       "No file extraction, implicit unit conversion, or actual-flow reconciliation.",
                       "A valid model alone does not verify final Word/Excel files.",
                       "artifact_verified covers only normalized quantity/specification/unit/date/ID fields and source-file hashes, not full wording, signatures, approvals or rendered pages."]}


def same_number(value, expected, label):
    actual = number(value, label, nullable=True)
    target = number(expected, label + ".expected", nullable=True)
    require(actual == target, f"{label}: quantity mismatch: {value!r} != {expected!r}")


def blank(value):
    return value is None or (isinstance(value, str) and value.strip() == "")


def verify_readback(report, readback, base_dir=None):
    """Check independently extracted rows and the identified source-file hashes.

    The extraction declaration cannot prove independence; the caller must truly
    read the final files. No extractor is bundled or simulated by this script.
    """
    base_dir = Path.cwd() if base_dir is None else Path(base_dir)
    obj(readback, "readback")
    require(readback.get("schema_version") == READBACK_SCHEMA, "unsupported readback schema")
    extraction = obj(readback.get("extraction"), "readback.extraction")
    require(extraction.get("independent") is True, "readback must declare independent extraction")
    string(extraction.get("method"), "readback.extraction.method")
    sources = obj(extraction.get("sources"), "readback.extraction.sources")
    for role in ("confirmation", "ledger"):
        source = obj(sources.get(role), "readback source " + role)
        raw_path = string(source.get("path"), "readback source path")
        expected_hash = source.get("sha256")
        require(isinstance(expected_hash, str) and bool(re.fullmatch(r"[a-fA-F0-9]{64}", expected_hash)),
                "readback source requires SHA256")
        path = Path(raw_path)
        path = path if path.is_absolute() else base_dir / path
        require(path.is_file(), f"readback source file missing: {path}")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash.lower(),
                f"readback source hash mismatch: {role}")
    confirmation = obj(readback.get("confirmation"), "readback.confirmation")
    read_works = indexed(confirmation.get("works"), "readback works")
    expected_works = {x["id"]: x for x in report["confirmation"]["works"]}
    require(set(read_works) == set(expected_works), "readback works: missing or extra work ids")
    for identity, expected in expected_works.items():
        row = read_works[identity]
        for field in ("name", "unit"):
            require(row.get(field) == expected[field], f"readback work {identity}: {field} mismatch")
        require("qty" in row, f"readback work {identity}: missing qty field")
        same_number(row.get("qty"), expected["qty"], f"readback work {identity}")
    read_materials = indexed(confirmation.get("materials"), "readback materials")
    expected_materials = {x["id"]: x for x in report["confirmation"]["materials"]}
    require(set(read_materials) == set(expected_materials), "readback materials: missing or extra ids (machines included; auxiliaries excluded)")
    for identity, expected in expected_materials.items():
        row = read_materials[identity]
        for field in ("name", "unit", "scope_key", "kind"):
            require(row.get(field) == expected[field], f"readback material {identity}: {field} mismatch")
        require("spec" in row and (row["spec"] or None) == expected["spec"], f"readback material {identity}: spec mismatch")
        ids = arr(row.get("work_ids"), "readback work_ids")
        require(all(isinstance(x, str) for x in ids), "readback work_ids must be strings")
        require(Counter(ids) == Counter(expected["work_ids"]), f"readback material {identity}: work_ids mismatch")
        require("qty" in row, f"readback material {identity}: missing qty field")
        same_number(row.get("qty"), expected["display_qty"], f"readback material {identity}")
    date_fields = obj(confirmation.get("date_fields"), "readback.confirmation.date_fields")
    require(all(blank(x) for x in date_fields.values()), "confirmation date must be blank")
    rows = arr(obj(readback.get("ledger"), "readback.ledger").get("rows"), "readback ledger rows")
    actual_ledger = {}
    for row in rows:
        obj(row, "readback ledger row")
        for field in ("name", "unit", "scope_key"):
            string(row.get(field), "readback ledger " + field)
        require("spec" in row, "readback ledger must include spec (null when unknown)")
        require(row["spec"] is None or isinstance(row["spec"], str), "readback ledger spec must be a string or null")
        key = ledger_key(row)
        require(key not in actual_ledger, "readback ledger: duplicate aggregate key")
        actual_ledger[key] = row
    expected_ledger = {ledger_key(x): x for x in report["ledger"]}
    require(set(actual_ledger) == set(expected_ledger), "readback ledger: missing/extra aggregate or name/spec/unit/scope mismatch")
    for key, expected in expected_ledger.items():
        row = actual_ledger[key]
        for field in ("in_qty", "out_qty"):
            require(field in row, "readback ledger missing " + field)
            same_number(row[field], expected[field], "readback ledger " + field)
        if "known_subtotal" in row:
            same_number(row["known_subtotal"], expected["known_subtotal"], "readback known_subtotal")
        for field in ("in_date", "out_date"):
            require(field in row and blank(row[field]), "readback ledger " + field + " must be blank")
    report["artifact_verified"] = True
    report["readback_verified"] = {"confirmation_works": len(read_works),
                                   "confirmation_materials": len(read_materials),
                                   "ledger_rows": len(actual_ledger), "sources": sources,
                                   "independence_is_caller_assertion": True}
    return report


def reject_duplicate_keys(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=reject_duplicate_keys)


def protect_inputs(output, paths):
    if output is None:
        return
    target = os.path.normcase(str(output.resolve()))
    for source in paths:
        source = Path(source)
        same_path = target == os.path.normcase(str(source.resolve()))
        same_file = output.exists() and source.exists() and output.samefile(source)
        if same_path or same_file:
            raise OutputConflict(f"report output would overwrite an input/source file: {source}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("--readback", type=Path, help="independent final-file extraction JSON")
    parser.add_argument("--out", "--output", dest="out", type=Path, help="report path; default stdout")
    args = parser.parse_args(argv)
    unsafe_output = False
    try:
        inputs = [args.model] + ([args.readback] if args.readback else [])
        protect_inputs(args.out, inputs)
        readback = load_json(args.readback) if args.readback else None
        if isinstance(readback, dict):
            extraction = readback.get("extraction")
            sources = extraction.get("sources") if isinstance(extraction, dict) else None
            if isinstance(sources, dict):
                for source in sources.values():
                    if isinstance(source, dict) and isinstance(source.get("path"), str):
                        path = Path(source["path"])
                        inputs.append(path if path.is_absolute() else args.readback.parent / path)
            protect_inputs(args.out, inputs)
        report = reconcile(load_json(args.model))
        report["model_sha256"] = hashlib.sha256(args.model.read_bytes()).hexdigest()
        if args.readback:
            verify_readback(report, readback, args.readback.parent)
        exit_code = 0
    except (ValidationError, OSError, json.JSONDecodeError, InvalidOperation) as error:
        report = {"model_valid": False, "artifact_verified": False, "error": str(error)}
        unsafe_output = isinstance(error, OutputConflict)
        exit_code = 2
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out and not unsafe_output:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output, end="", file=sys.stderr if unsafe_output else sys.stdout)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
