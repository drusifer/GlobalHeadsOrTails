"""Read URL Tool - Display current NDEF URL from tag."""

from ntag424_sdm_provisioner.hal import NTag424CardConnection
from ntag424_sdm_provisioner.tools.base import TagState, ToolResult
from ntag424_sdm_provisioner.tools.tool_helpers import read_ndef_file


class ReadUrlTool:
    """Display current NDEF URL without modifying tag."""

    name = "Read Current URL"
    description = "Display NDEF URL from tag (read-only)"

    def is_available(self, tag_state: TagState) -> bool | tuple[bool, str]:
        """Always available if tag has NDEF."""
        if not tag_state.has_ndef:
            return False, "no NDEF content on tag"
        return True

    def get_confirmation_request(self) -> None:
        """No confirmation needed for read-only operation."""
        return None

    def execute(self, card: NTag424CardConnection) -> ToolResult:
        """Read and return current URL."""
        from ntag424_sdm_provisioner.constants import SDMConfiguration

        ndef_data = read_ndef_file(card)

        # Parse SDM configuration from NDEF
        sdm_config = SDMConfiguration.from_ndef_data(ndef_data)

        if not sdm_config or not sdm_config.url:
            return ToolResult(
                success=False,
                message="Could not extract URL from NDEF data",
                details={},
            )

        url = sdm_config.url

        # Check for SDM placeholders
        has_placeholders = "00000000000000" in url or "000000" in url

        return ToolResult(
            success=True,
            message="Current URL" + (" (contains placeholders)" if has_placeholders else ""),
            details={
                "url": url,
                "length": len(url),
                "has_sdm_placeholders": has_placeholders,
                "has_sdm_parameters": sdm_config.has_sdm_parameters,
                "base_url": sdm_config.base_url,
            },
        )
