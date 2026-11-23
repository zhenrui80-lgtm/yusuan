"""Executable boundary tests; all fixtures are synthetic, not project data."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from reconcile import ValidationError, load_json, main, reconcile, verify_readback


def material(identity="M1", qty="8", **overrides):
    row = {"id": identity, "work_ids": ["W1"], "name": "标准成品",
           "spec": "规格A", "unit": "个", "kind": "main", "qty": qty,
           "source_refs": ["example:quantity/1"], "spec_refs": ["example:spec/1"],
           "quantity_basis": "estimated", "owner_line_id": None,
           "loss": {"rate": "0", "already_in_quota": False, "refs": []},
           "indivisible": True, "scope_key": "zone-a"}
    row.update(overrides)
    return row


def model(*rows):
    return {"schema_version": "physical-materials/1",
            "display": {"default_decimals": 3, "unit_decimals": {"个": 0}, "rounding": "ROUND_HALF_UP"},
            "decisions": {"ledger_mode": "equal_adopted", "equal_adopted_authorized": True,
                          "dates": "blank", "blank_dates_authorized": True},
            "works": [{"id": "W1", "name": "成品安装", "qty": "8", "unit": "套",
                       "source_refs": ["example:work/1"]}],
            "owner_lines": [], "materials": list(rows) if rows else [material()]}


def owner_model(*quantities):
    rows = [material(f"M{i}", qty, quantity_basis="owner_actual", owner_line_id="O1")
            for i, qty in enumerate(quantities or ["8"], 1)]
    result = model(*rows)
    result["owner_lines"] = [{"id": "O1", "qty": "8", "unit": "个", "basis": "issued",
                              "source_refs": ["example:owner/1"]}]
    return result


class AggregationTests(unittest.TestCase):
    def test_eight_finished_items_stay_eight(self):
        result = reconcile(model())
        self.assertEqual(result["confirmation"]["materials"][0]["display_qty"], "8")
        self.assertEqual(result["ledger"][0]["in_qty"], "8")
        self.assertFalse(result["artifact_verified"])

    def test_fractional_finished_item_is_rejected_not_rounded(self):
        with self.assertRaisesRegex(ValidationError, "integer"):
            reconcile(model(material(qty="8.08")))

    def test_finished_item_loss_is_rejected(self):
        row = material(loss={"rate": "0.01", "already_in_quota": False, "refs": ["example:loss"]})
        with self.assertRaisesRegex(ValidationError, "indivisible"):
            reconcile(model(row))

    def test_explicit_loss_and_base_are_distinct(self):
        row = material(qty="10", unit="m", indivisible=False,
                       loss={"rate": "0.03", "already_in_quota": False, "refs": ["example:loss"]})
        item = reconcile(model(row))["confirmation"]["materials"][0]
        self.assertEqual((item["base_qty"], item["adopted_qty"], item["display_qty"]), ("10", "10.3", "10.300"))

    def test_quota_loss_cannot_be_added_twice(self):
        row = material(unit="m", indivisible=False,
                       loss={"rate": "0.02", "already_in_quota": True, "refs": ["example:quota"]})
        with self.assertRaisesRegex(ValidationError, "already contains"):
            reconcile(model(row))

    def test_owner_full_quantity_not_repeated(self):
        with self.assertRaisesRegex(ValidationError, "multiple times"):
            reconcile(owner_model("8", "8"))

    def test_owner_split_requires_evidence_and_conservation(self):
        data = owner_model("3", "5")
        for row in data["materials"]:
            row["allocation_refs"] = ["example:allocation/1"]
        self.assertEqual(reconcile(data)["ledger"][0]["qty"], "8")
        data["materials"][1]["qty"] = "8"
        with self.assertRaisesRegex(ValidationError, "does not equal"):
            reconcile(data)

    def test_owner_no_loss_and_no_implicit_unit_conversion(self):
        data = owner_model()
        data["materials"][0]["indivisible"] = False
        data["materials"][0]["loss"] = {"rate": "0.01", "already_in_quota": False, "refs": ["example:loss"]}
        with self.assertRaisesRegex(ValidationError, "owner actual"):
            reconcile(data)
        data = owner_model()
        data["materials"][0]["unit"] = "箱"
        with self.assertRaisesRegex(ValidationError, "unit differs"):
            reconcile(data)

    def test_owner_material_unit_can_differ_from_work_unit(self):
        data = owner_model()
        self.assertEqual(data["works"][0]["unit"], "套")
        self.assertEqual(reconcile(data)["ledger"][0]["unit"], "个")

    def test_unknown_quantity_has_null_total_and_known_subtotal(self):
        data = model(material(qty="8"), material("M2", None, pending_reason="待计量"))
        result = reconcile(data)
        row = result["ledger"][0]
        self.assertEqual(row["known_subtotal"], "8")
        self.assertIsNone(row["qty"])
        self.assertIsNone(row["in_qty"])
        self.assertFalse(row["quantity_complete"])
        self.assertFalse(result["complete"])

    def test_unknown_spec_is_not_fabricated(self):
        row = material(spec=None, spec_refs=[], pending_reason="待规格凭证")
        result = reconcile(model(row))
        self.assertIsNone(result["ledger"][0]["spec"])
        self.assertFalse(result["complete"])
        with self.assertRaisesRegex(ValidationError, "unknown specifications"):
            reconcile(model(row, material("M2", spec="", spec_refs=[], pending_reason="待规格凭证")))

    def test_pending_and_evidence_required(self):
        for row in [material(qty=None), material(spec=None, spec_refs=[]), material(spec_refs=[]), material(source_refs=[])]:
            with self.subTest(row=row), self.assertRaises(ValidationError):
                reconcile(model(row))

    def test_different_spec_unit_scope_never_merge(self):
        data = model(material(), material("M2", spec="规格B"), material("M3", unit="套"), material("M4", scope_key="zone-b"))
        self.assertEqual(len(reconcile(data)["ledger"]), 4)

    def test_round_each_contribution_before_sum(self):
        data = model(material(qty="0.0045", unit="kg", indivisible=False),
                     material("M2", "0.0045", unit="kg", indivisible=False))
        result = reconcile(data)
        self.assertEqual([x["display_qty"] for x in result["confirmation"]["materials"]], ["0.005", "0.005"])
        self.assertEqual(result["ledger"][0]["qty"], "0.010")

    def test_machines_in_confirmation_auxiliary_excluded(self):
        data = model(material(), material("M2", kind="machine", unit="台班", indivisible=False), material("M3", kind="auxiliary"))
        result = reconcile(data)
        self.assertEqual(len(result["confirmation"]["materials"]), 2)
        self.assertEqual(len(result["ledger"]), 1)
        self.assertEqual(len(result["excluded_auxiliary"]), 1)

    def test_shared_work_reference_does_not_repeat_quantity(self):
        data = model()
        data["works"].append({**data["works"][0], "id": "W2"})
        data["materials"][0]["work_ids"].append("W2")
        self.assertEqual(reconcile(data)["ledger"][0]["qty"], "8")

    def test_policies_must_be_explicit_and_actual_is_rejected(self):
        for key, value in [("ledger_mode", "actual"), ("equal_adopted_authorized", False), ("blank_dates_authorized", False)]:
            data = model()
            data["decisions"][key] = value
            with self.subTest(key=key), self.assertRaises(ValidationError):
                reconcile(data)

    def test_numeric_json_nan_negative_and_duplicate_ids_rejected(self):
        for qty in [8, 8.08, "NaN", "-1", "1e2"]:
            with self.subTest(qty=qty), self.assertRaises(ValidationError):
                reconcile(model(material(qty=qty)))
        with self.assertRaisesRegex(ValidationError, "duplicate id"):
            reconcile(model(material(), material()))


class ReadbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        sources = {}
        for role, name in [("confirmation", "fixture.docx"), ("ledger", "fixture.xlsx")]:
            # Synthetic bytes only test hash plumbing; they are not extractors
            # or real Office artifacts and cannot demonstrate layout fidelity.
            path = self.folder / name
            path.write_bytes(b"synthetic fixture for hash checks")
            sources[role] = {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        self.report = reconcile(model())
        # Handwritten observed records, deliberately not generated from report.
        self.readback = {"schema_version": "physical-materials-readback/1",
                         "extraction": {"independent": True, "method": "synthetic unit-test fixture", "sources": sources},
                         "confirmation": {
                             "works": [{"id": "W1", "name": "成品安装", "qty": "8", "unit": "套"}],
                             "materials": [{"id": "M1", "work_ids": ["W1"], "name": "标准成品", "spec": "规格A", "unit": "个", "kind": "main", "scope_key": "zone-a", "qty": "8"}],
                             "date_fields": {"sign_date": ""}},
                         "ledger": {"rows": [{"name": "标准成品", "spec": "规格A", "unit": "个", "scope_key": "zone-a", "in_qty": "8", "out_qty": "8", "in_date": "", "out_date": None}]}}

    def verify(self):
        return verify_readback(self.report, self.readback, self.folder)

    def test_valid_readback(self):
        self.assertTrue(self.verify()["artifact_verified"])

    def test_missing_material(self):
        self.readback["confirmation"]["materials"] = []
        with self.assertRaisesRegex(ValidationError, "missing or extra"):
            self.verify()

    def test_duplicate_material(self):
        self.readback["confirmation"]["materials"] *= 2
        with self.assertRaisesRegex(ValidationError, "duplicate id"):
            self.verify()

    def test_quantity_difference(self):
        self.readback["confirmation"]["materials"][0]["qty"] = "8.08"
        with self.assertRaisesRegex(ValidationError, "quantity mismatch"):
            self.verify()

    def test_source_work_quantity_must_not_change(self):
        self.readback["confirmation"]["works"][0]["qty"] = "9"
        with self.assertRaisesRegex(ValidationError, "quantity mismatch"):
            self.verify()

    def test_ledger_specs_units_duplicate_and_outflow(self):
        for field, value in [("spec", "规格B"), ("unit", "箱"), ("out_qty", "7")]:
            baseline = copy.deepcopy(self.readback)
            self.readback["ledger"]["rows"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                self.verify()
            self.readback = baseline
        self.readback["ledger"]["rows"] *= 2
        with self.assertRaisesRegex(ValidationError, "duplicate aggregate"):
            self.verify()

    def test_nonblank_dates_rejected(self):
        self.readback["ledger"]["rows"][0]["in_date"] = "2030-01-01"
        with self.assertRaisesRegex(ValidationError, "must be blank"):
            self.verify()
        self.readback["ledger"]["rows"][0]["in_date"] = ""
        self.readback["confirmation"]["date_fields"]["sign_date"] = "2030-01-01"
        with self.assertRaisesRegex(ValidationError, "must be blank"):
            self.verify()

    def test_unknown_cannot_read_back_as_zero_or_subtotal(self):
        self.report = reconcile(model(material(qty=None, pending_reason="待计量")))
        self.readback["confirmation"]["materials"][0]["qty"] = None
        for fake_qty in ["0", "8"]:
            self.readback["ledger"]["rows"][0]["in_qty"] = fake_qty
            with self.subTest(fake_qty=fake_qty), self.assertRaisesRegex(ValidationError, "quantity mismatch"):
                self.verify()
        self.readback["ledger"]["rows"][0].update(in_qty=None, out_qty=None)
        self.assertTrue(self.verify()["artifact_verified"])
        self.assertFalse(self.report["complete"])

    def test_false_independence_or_changed_file_rejected(self):
        self.readback["extraction"]["independent"] = False
        with self.assertRaisesRegex(ValidationError, "independent extraction"):
            self.verify()
        self.readback["extraction"]["independent"] = True
        (self.folder / "fixture.docx").write_bytes(b"changed")
        with self.assertRaisesRegex(ValidationError, "hash mismatch"):
            self.verify()

    def test_cli_overwrites_stale_pass_with_error(self):
        path, out = self.folder / "model.json", self.folder / "report.json"
        path.write_text(json.dumps(model(), ensure_ascii=False), encoding="utf8")
        self.assertEqual(main([str(path), "--out", str(out)]), 0)
        data = model()
        data["decisions"]["ledger_mode"] = "actual"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf8")
        self.assertEqual(main([str(path), "--out", str(out)]), 2)
        report = load_json(out)
        self.assertFalse(report["artifact_verified"])
        self.assertIn("actual receipt/issue flows", report["error"])

    def test_json_duplicate_keys_fail(self):
        path = self.folder / "duplicate.json"
        path.write_text('{"qty":"8","qty":"9"}', encoding="utf8")
        with self.assertRaisesRegex(ValidationError, "duplicate JSON"):
            load_json(path)

    def test_report_cannot_overwrite_any_input_or_source_file(self):
        model_path, read_path = self.folder / "model.json", self.folder / "readback.json"
        model_path.write_text(json.dumps(model(), ensure_ascii=False), encoding="utf8")
        read_path.write_text(json.dumps(self.readback, ensure_ascii=False), encoding="utf8")
        for target in [model_path, read_path, self.folder / "fixture.docx", self.folder / "fixture.xlsx"]:
            before = target.read_bytes()
            with self.subTest(target=target):
                self.assertEqual(main([str(model_path), "--readback", str(read_path), "--output", str(target)]), 2)
                self.assertEqual(target.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
