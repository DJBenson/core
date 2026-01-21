"""Repairs for Evohome integration."""

from __future__ import annotations

from typing import cast

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN


class YAMLDeprecatedRepairFlow(RepairsFlow):
    """Handler for YAML deprecation repair."""

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of the repair flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the confirm step of the repair flow."""
        if user_input is not None:
            ir.async_delete_issue(self.hass, DOMAIN, self.issue_id)
            return self.async_create_entry(data={})

        return self.async_show_form(step_id="confirm")


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str] | None,
) -> RepairsFlow:
    """Create flow."""
    if issue_id == "yaml_deprecated":
        return YAMLDeprecatedRepairFlow()
    raise ValueError(f"Unknown issue_id: {issue_id}")
