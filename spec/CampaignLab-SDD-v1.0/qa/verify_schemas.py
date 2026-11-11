"""Validate the handoff's typed payloads after installing the dev dependency jsonschema."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main():
    api = read("contracts/openapi.json")
    schemas = api["components"]["schemas"]
    checker = FormatChecker()

    def component(name, body):
        wrapper = {"$ref": f"#/components/schemas/{name}", "components": {"schemas": schemas}}
        Draft202012Validator(wrapper, format_checker=checker).validate(body)

    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
    standalone = sorted((ROOT / "contracts").glob("*.schema.json"))
    for path in standalone:
        Draft202012Validator.check_schema(read(path.relative_to(ROOT)))
    for schema, fixture in (
        ("source-mapping","fixtures/banks/map-a.json"),
        ("source-mapping","fixtures/banks/map-b.json"),
        ("source-json","fixtures/banks/csv-mini/source.json"),
        ("source-metadata","fixtures/banks/csv-mini/metadata.json"),
    ):
        Draft202012Validator(read(f"contracts/{schema}.schema.json"),format_checker=checker).validate(read(fixture))
    for rule in read("fixtures/cases/rules.json").values():
        component("RuleContent", rule)
    for case in read("fixtures/cases/golden-cases.json"):
        component("CaseInput",case["input"])
        for key in ("expected_baseline","expected_candidate","observed_original"):
            if case[key] is not None:
                component("Outcome",case[key])
    questions = read("fixtures/questions.json")
    for question in questions:
        component("Scope",question["context"])
        if question["plan"] is not None:
            component("QuestionPlan",question["plan"])
    ops = {item["id"]:item for item in read("contracts/operations.json")}
    payloads = read("fixtures/api-examples.json")
    for example in payloads["examples"]:
        operation = ops[example["operationId"]]
        if operation["status"] != example["status"]:
            raise ValueError(example["operationId"])
        component(operation["request"],example["request"])
    component("Estimate",payloads["estimate_response"])
    print(f"SCHEMA PASS {len(schemas)} components, {len(standalone)} standalone, {len(payloads['examples'])} API requests, {len(questions)} question entries")


if __name__ == "__main__":
    main()
