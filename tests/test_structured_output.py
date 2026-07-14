import unittest

from pydantic import ValidationError

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


if __name__ == "__main__":
    unittest.main()
