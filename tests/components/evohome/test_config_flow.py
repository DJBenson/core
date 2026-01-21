"""Test the evohome config flow."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from homeassistant import config_entries
from homeassistant.components.evohome.const import (
    CONF_LOCATION_IDX,
    DOMAIN,
    SCAN_INTERVAL_DEFAULT,
    SCAN_INTERVAL_MINIMUM,
)
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


MOCK_USERNAME = "test@example.com"
MOCK_PASSWORD = "test-password"
MOCK_LOCATION_IDX = 0
MOCK_SCAN_INTERVAL = int(SCAN_INTERVAL_DEFAULT.total_seconds())


@pytest.fixture
def mock_evohome_client():
    """Mock the EvohomeClient."""
    with patch(
        "homeassistant.components.evohome.config_flow.ec2.EvohomeClient"
    ) as mock_client:
        client_instance = Mock()
        client_instance.update = AsyncMock()
        # Mock locations for validation
        client_instance.locations = [Mock(), Mock()]  # Two locations
        mock_client.return_value = client_instance
        yield mock_client


@pytest.fixture
def mock_token_manager():
    """Mock the TokenManager."""
    with patch(
        "homeassistant.components.evohome.config_flow.TokenManager"
    ) as mock_tm:
        yield mock_tm


@pytest.fixture
def mock_setup_entry():
    """Mock setting up a config entry."""
    with patch(
        "homeassistant.components.evohome.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup


async def test_form_user(
    hass: HomeAssistant, mock_setup_entry, mock_evohome_client, mock_token_manager
) -> None:
    """Test we get the user form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result.get("errors") is None or result.get("errors") == {}
    assert result["step_id"] == "user"

    # Test successful config
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_LOCATION_IDX: MOCK_LOCATION_IDX,
            CONF_SCAN_INTERVAL: MOCK_SCAN_INTERVAL,
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == MOCK_USERNAME
    assert result2["data"] == {
        CONF_USERNAME: MOCK_USERNAME,
        CONF_PASSWORD: MOCK_PASSWORD,
        CONF_LOCATION_IDX: MOCK_LOCATION_IDX,
        CONF_SCAN_INTERVAL: MOCK_SCAN_INTERVAL,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_user_already_configured(
    hass: HomeAssistant, mock_setup_entry
) -> None:
    """Test we handle duplicate entries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_USERNAME,
        data={
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_LOCATION_IDX: MOCK_LOCATION_IDX,
            CONF_SCAN_INTERVAL: MOCK_SCAN_INTERVAL,
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_LOCATION_IDX: MOCK_LOCATION_IDX,
            CONF_SCAN_INTERVAL: MOCK_SCAN_INTERVAL,
        },
    )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_import_success(
    hass: HomeAssistant, mock_setup_entry, mock_evohome_client, mock_token_manager
) -> None:
    """Test import from YAML."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_LOCATION_IDX: MOCK_LOCATION_IDX,
            CONF_SCAN_INTERVAL: MOCK_SCAN_INTERVAL,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_USERNAME
    assert result["data"] == {
        CONF_USERNAME: MOCK_USERNAME,
        CONF_PASSWORD: MOCK_PASSWORD,
        CONF_LOCATION_IDX: MOCK_LOCATION_IDX,
        CONF_SCAN_INTERVAL: MOCK_SCAN_INTERVAL,
    }


async def test_import_with_timedelta_scan_interval(
    hass: HomeAssistant, mock_setup_entry, mock_evohome_client, mock_token_manager
) -> None:
    """Test import from YAML with timedelta scan_interval."""
    from datetime import timedelta

    scan_interval_td = timedelta(seconds=300)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_LOCATION_IDX: MOCK_LOCATION_IDX,
            CONF_SCAN_INTERVAL: scan_interval_td,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SCAN_INTERVAL] == 300


async def test_import_with_dict_scan_interval(
    hass: HomeAssistant, mock_setup_entry, mock_evohome_client, mock_token_manager
) -> None:
    """Test import from YAML with dict scan_interval."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_LOCATION_IDX: MOCK_LOCATION_IDX,
            CONF_SCAN_INTERVAL: {"seconds": 300},
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SCAN_INTERVAL] == 300


async def test_import_default_scan_interval(
    hass: HomeAssistant, mock_setup_entry, mock_evohome_client, mock_token_manager
) -> None:
    """Test import from YAML without scan_interval uses default."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SCAN_INTERVAL] == int(
        SCAN_INTERVAL_DEFAULT.total_seconds()
    )
    assert result["data"][CONF_LOCATION_IDX] == 0


async def test_import_missing_credentials(hass: HomeAssistant) -> None:
    """Test import fails with missing credentials."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={CONF_USERNAME: MOCK_USERNAME},
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "import_failed"


async def test_import_invalid_location_idx(
    hass: HomeAssistant, mock_evohome_client, mock_token_manager
) -> None:
    """Test import fails with invalid location_idx."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_LOCATION_IDX: 5,  # Invalid - only 2 locations exist
        },
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "invalid_location_idx"


async def test_import_invalid_scan_interval(
    hass: HomeAssistant, mock_evohome_client, mock_token_manager
) -> None:
    """Test import fails with scan_interval below minimum."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_SCAN_INTERVAL: 10,  # Below minimum
        },
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "invalid_scan_interval"


async def test_import_connection_error(
    hass: HomeAssistant, mock_token_manager
) -> None:
    """Test import fails with connection error."""
    with patch(
        "homeassistant.components.evohome.config_flow.ec2.EvohomeClient"
    ) as mock_client:
        client_instance = Mock()
        client_instance.update = AsyncMock(side_effect=Exception("Connection failed"))
        mock_client.return_value = client_instance

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={
                CONF_USERNAME: MOCK_USERNAME,
                CONF_PASSWORD: MOCK_PASSWORD,
            },
        )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "import_failed"


async def test_import_already_configured(
    hass: HomeAssistant, mock_evohome_client, mock_token_manager, mock_setup_entry
) -> None:
    """Test import aborts if already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_USERNAME,
        data={
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_LOCATION_IDX: MOCK_LOCATION_IDX,
            CONF_SCAN_INTERVAL: MOCK_SCAN_INTERVAL,
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
        },
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_import_none_input(hass: HomeAssistant) -> None:
    """Test import with None input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=None,
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "import_failed"


async def test_reconfigure(hass: HomeAssistant, mock_setup_entry) -> None:
    """Test reconfigure flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_USERNAME,
        data={
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_LOCATION_IDX: MOCK_LOCATION_IDX,
            CONF_SCAN_INTERVAL: MOCK_SCAN_INTERVAL,
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    # Test updating configuration
    new_password = "new-password"
    new_scan_interval = 600

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: new_password,
            CONF_LOCATION_IDX: MOCK_LOCATION_IDX,
            CONF_SCAN_INTERVAL: new_scan_interval,
        },
    )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "reconfigure_successful"

    # Verify the entry was updated
    assert entry.data[CONF_PASSWORD] == new_password
    assert entry.data[CONF_SCAN_INTERVAL] == new_scan_interval


async def test_reconfigure_no_entry(hass: HomeAssistant, mock_setup_entry) -> None:
    """Test reconfigure flow with non-existent entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": "non_existent_id",
        },
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_failed"
