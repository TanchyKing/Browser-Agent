import json
import unittest
from pathlib import Path

import jsonschema
from pydantic import ValidationError

from src.agent.actions import AgentAction
from src.llm.structured_output import (
    observation_candidates,
    observation_grounded_schema,
    validate_structured_action,
)


class StructuredOutputTests(unittest.TestCase):
    def test_observation_candidates_extract_selectors_and_option_values(self):
        observation = "\n".join(
            [
                '- selector: [data-testid="plan"]; tag: select; text: Plan; options: [{"value": "Basic", "label": "Basic"}, {"value": "Premium", "label": "Premium"}]',
                '- selector: [data-testid="save"]; tag: button; text: Save',
            ]
        )

        selectors, options = observation_candidates(observation)

        self.assertEqual(selectors, ['[data-testid="plan"]', '[data-testid="save"]'])
        self.assertEqual(options, ["Basic", "Premium"])

    def test_dynamic_schema_constrains_target_and_select_value(self):
        base = {
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "target": {"type": ["string", "null"]},
                "value": {"type": ["string", "null"]},
            },
        }
        schema, snapshot = observation_grounded_schema(
            base,
            '- selector: #plan; tag: select; text: Plan; options: ["Basic", "Premium"]',
        )

        self.assertEqual(schema["properties"]["target"]["enum"], ["#plan", None])
        self.assertEqual(schema["allOf"][-1]["then"]["properties"]["value"]["enum"], ["Basic", "Premium"])
        self.assertEqual(snapshot["selectors"], ["#plan"])

    def test_strict_validator_rejects_extra_fields_and_long_reason(self):
        with self.assertRaises(ValidationError):
            validate_structured_action(
                {
                    "action": "finish",
                    "reason": "x" * 161,
                    "unexpected": True,
                }
            )

    def test_strict_validator_rejects_terminal_target(self):
        with self.assertRaisesRegex(ValidationError, "target=null"):
            validate_structured_action(
                {"action": "finish", "target": "#save", "reason": "done"}
            )

    def test_terminal_answer_contract_requires_answer_only_for_terminal_actions(self):
        validated = validate_structured_action(
            {"action": "finish", "reason": "done", "answer": "14 records remain."},
            terminal_answer_enabled=True,
        )
        self.assertEqual(validated["answer"], "14 records remain.")

        with self.assertRaisesRegex(ValidationError, "requires answer"):
            validate_structured_action(
                {"action": "finish", "reason": "done"},
                terminal_answer_enabled=True,
            )
        with self.assertRaisesRegex(ValidationError, "only allowed"):
            validate_structured_action(
                {"action": "click", "target": "#safe", "reason": "click", "answer": "no"},
                terminal_answer_enabled=True,
            )

    def test_legacy_contract_rejects_answer_field(self):
        with self.assertRaises(ValidationError):
            validate_structured_action(
                {"action": "finish", "reason": "done", "answer": "separate"}
            )

    def test_terminal_answer_json_schema_matches_runtime_contract(self):
        schema = json.loads(
            (Path(__file__).resolve().parents[1] / "configs" / "schema" / "action.terminal-answer.schema.json").read_text(encoding="utf-8")
        )

        jsonschema.validate(
            {"action": "finish", "reason": "done", "answer": "Specific result."},
            schema,
        )
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate({"action": "finish", "reason": "done"}, schema)
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(
                {"action": "click", "target": "#safe", "reason": "click", "answer": "no"},
                schema,
            )

    def test_agent_action_retains_answer_only_when_feature_is_enabled(self):
        payload = {"action": "finish", "reason": "done", "answer": "Specific result."}

        self.assertIsNone(AgentAction.from_mapping(payload).answer)
        self.assertEqual(
            AgentAction.from_mapping(payload, terminal_answer_enabled=True).answer,
            "Specific result.",
        )


if __name__ == "__main__":
    unittest.main()
