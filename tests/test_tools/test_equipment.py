"""Tests for equipment tools."""

from copy import deepcopy
from unittest.mock import AsyncMock, patch

import pytest

from tp_mcp.client.http import APIResponse
from tp_mcp.tools.equipment import (
    tp_create_equipment,
    tp_delete_equipment,
    tp_get_equipment,
    tp_update_equipment,
)

MOCK_EQUIPMENT = [
    {"equipmentId": 1, "name": "Tarmac SL7", "equipmentType": 1, "brand": "Specialized",
     "model": "SL7", "distance": 5000000, "startingDistance": 0, "maxDistance": 0,
     "retired": False, "isDefault": True},
    {"equipmentId": 2, "name": "Vaporfly", "equipmentType": 2, "brand": "Nike",
     "model": "Vaporfly 3", "distance": 500000, "startingDistance": 0, "maxDistance": 800000,
     "retired": False, "isDefault": False},
]


class TestGetEquipment:
    @pytest.mark.asyncio
    async def test_returns_formatted_list(self):
        response = APIResponse(success=True, data=MOCK_EQUIPMENT)
        with patch("tp_mcp.tools.equipment.TPClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.ensure_athlete_id = AsyncMock(return_value=123)
            mock_instance.get = AsyncMock(return_value=response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await tp_get_equipment()

        assert result["count"] == 2
        assert result["equipment"][0]["distance_km"] == 5000.0
        assert result["equipment"][0]["type"] == "bike"
        assert result["equipment"][1]["type"] == "shoe"

    @pytest.mark.asyncio
    async def test_filter_by_type(self):
        response = APIResponse(success=True, data=MOCK_EQUIPMENT)
        with patch("tp_mcp.tools.equipment.TPClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.ensure_athlete_id = AsyncMock(return_value=123)
            mock_instance.get = AsyncMock(return_value=response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await tp_get_equipment(type="bike")

        assert result["count"] == 1
        assert result["equipment"][0]["name"] == "Tarmac SL7"


class TestCreateEquipment:
    @pytest.mark.asyncio
    async def test_create_appends_with_null_id(self):
        get_response = APIResponse(success=True, data=deepcopy(MOCK_EQUIPMENT))
        saved = deepcopy(MOCK_EQUIPMENT) + [
            {
                "equipmentId": 3,
                "name": "New Bike",
                "equipmentType": 1,
                "brand": "Canyon",
                "model": "",
            }
        ]
        put_response = APIResponse(success=True, data=saved)

        with patch("tp_mcp.tools.equipment.TPClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.ensure_athlete_id = AsyncMock(return_value=123)
            mock_instance.get = AsyncMock(return_value=get_response)
            mock_instance.put = AsyncMock(return_value=put_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await tp_create_equipment(name="New Bike", type="bike", brand="Canyon")

        assert result["success"] is True
        assert result["equipment_id"] == "3"
        put_payload = mock_instance.put.call_args[1]["json"]
        assert len(put_payload) == 3  # 2 existing + 1 new
        new_item = put_payload[-1]
        assert new_item["equipmentId"] is None
        assert new_item["name"] == "New Bike"
        assert new_item["equipmentType"] == 1

    @pytest.mark.asyncio
    async def test_create_converts_km_to_metres(self):
        get_response = APIResponse(success=True, data=[])
        put_response = APIResponse(
            success=True,
            data=[
                {
                    "equipmentId": 3,
                    "name": "Used Bike",
                    "equipmentType": 1,
                    "brand": "",
                    "model": "",
                    "startingDistance": 2000000,
                }
            ],
        )

        with patch("tp_mcp.tools.equipment.TPClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.ensure_athlete_id = AsyncMock(return_value=123)
            mock_instance.get = AsyncMock(return_value=get_response)
            mock_instance.put = AsyncMock(return_value=put_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await tp_create_equipment(
                name="Used Bike", type="bike", starting_distance_km=2000.0,
            )

        assert result["success"] is True
        new_item = mock_instance.put.call_args[1]["json"][-1]
        assert new_item["startingDistance"] == 2000000

    @pytest.mark.asyncio
    async def test_create_bike_with_wheels(self):
        get_response = APIResponse(success=True, data=[])
        put_response = APIResponse(
            success=True,
            data=[
                {
                    "equipmentId": 3,
                    "name": "TT Bike",
                    "equipmentType": 1,
                    "brand": "",
                    "model": "",
                    "wheels": "Zipp 808",
                    "crankLength": 172.5,
                }
            ],
        )

        with patch("tp_mcp.tools.equipment.TPClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.ensure_athlete_id = AsyncMock(return_value=123)
            mock_instance.get = AsyncMock(return_value=get_response)
            mock_instance.put = AsyncMock(return_value=put_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await tp_create_equipment(
                name="TT Bike", type="bike", wheels="Zipp 808", crank_length_mm=172.5,
            )

        assert result["success"] is True
        new_item = mock_instance.put.call_args[1]["json"][-1]
        assert new_item["wheels"] == "Zipp 808"
        assert new_item["crankLength"] == 172.5

    @pytest.mark.asyncio
    async def test_create_shoe_rejects_bike_fields(self):
        result = await tp_create_equipment(
            name="Shoe", type="shoe", wheels="Not valid",
        )
        assert result["isError"] is True
        assert "bike" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_create_rejects_phantom_success(self):
        get_response = APIResponse(success=True, data=[])
        put_response = APIResponse(success=True, data=[])

        with patch("tp_mcp.tools.equipment.TPClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.ensure_athlete_id = AsyncMock(return_value=123)
            mock_instance.get = AsyncMock(return_value=get_response)
            mock_instance.put = AsyncMock(return_value=put_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await tp_create_equipment(name="Discarded Bike", type="bike")

        assert result["isError"] is True
        assert result["error_code"] == "WRITE_NOT_CONFIRMED"

    @pytest.mark.asyncio
    async def test_create_verifies_with_readback_when_put_has_no_body(self):
        initial_response = APIResponse(success=True, data=[])
        saved_response = APIResponse(
            success=True,
            data=[
                {
                    "equipmentId": 3,
                    "name": "Readback Bike",
                    "equipmentType": 1,
                    "brand": "",
                    "model": "",
                }
            ],
        )
        put_response = APIResponse(success=True, data=None)

        with patch("tp_mcp.tools.equipment.TPClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.ensure_athlete_id = AsyncMock(return_value=123)
            mock_instance.get = AsyncMock(side_effect=[initial_response, saved_response])
            mock_instance.put = AsyncMock(return_value=put_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await tp_create_equipment(name="Readback Bike", type="bike")

        assert result["success"] is True
        assert result["equipment_id"] == "3"
        assert mock_instance.get.call_count == 2


class TestUpdateEquipment:
    @pytest.mark.asyncio
    async def test_update_merges(self):
        get_response = APIResponse(success=True, data=deepcopy(MOCK_EQUIPMENT))
        saved = deepcopy(MOCK_EQUIPMENT)
        saved[0]["name"] = "Updated Name"
        put_response = APIResponse(success=True, data=saved)

        with patch("tp_mcp.tools.equipment.TPClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.ensure_athlete_id = AsyncMock(return_value=123)
            mock_instance.get = AsyncMock(return_value=get_response)
            mock_instance.put = AsyncMock(return_value=put_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await tp_update_equipment(equipment_id="1", name="Updated Name")

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_retire_sets_date(self):
        equipment = [{"equipmentId": 1, "name": "Old", "equipmentType": 1, "retired": False}]
        get_response = APIResponse(success=True, data=deepcopy(equipment))
        saved = deepcopy(equipment)
        saved[0]["retired"] = True
        put_response = APIResponse(success=True, data=saved)

        with patch("tp_mcp.tools.equipment.TPClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.ensure_athlete_id = AsyncMock(return_value=123)
            mock_instance.get = AsyncMock(return_value=get_response)
            mock_instance.put = AsyncMock(return_value=put_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await tp_update_equipment(equipment_id="1", retired=True)

        assert result["success"] is True
        updated = mock_instance.put.call_args[1]["json"][0]
        assert updated["retired"] is True
        assert "retiredDate" in updated

    @pytest.mark.asyncio
    async def test_update_rejects_phantom_success(self):
        original = deepcopy(MOCK_EQUIPMENT)
        get_response = APIResponse(success=True, data=deepcopy(original))
        put_response = APIResponse(success=True, data=original)

        with patch("tp_mcp.tools.equipment.TPClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.ensure_athlete_id = AsyncMock(return_value=123)
            mock_instance.get = AsyncMock(return_value=get_response)
            mock_instance.put = AsyncMock(return_value=put_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await tp_update_equipment(equipment_id="1", name="Ignored")

        assert result["isError"] is True
        assert result["error_code"] == "WRITE_NOT_CONFIRMED"


class TestDeleteEquipment:
    @pytest.mark.asyncio
    async def test_delete_removes_from_array(self):
        get_response = APIResponse(success=True, data=deepcopy(MOCK_EQUIPMENT))
        put_response = APIResponse(success=True, data=None)

        with patch("tp_mcp.tools.equipment.TPClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.ensure_athlete_id = AsyncMock(return_value=123)
            mock_instance.get = AsyncMock(return_value=get_response)
            mock_instance.put = AsyncMock(return_value=put_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await tp_delete_equipment("1")

        assert result["success"] is True
        remaining = mock_instance.put.call_args[1]["json"]
        assert len(remaining) == 1
        assert remaining[0]["equipmentId"] == 2

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        get_response = APIResponse(success=True, data=MOCK_EQUIPMENT.copy())

        with patch("tp_mcp.tools.equipment.TPClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.ensure_athlete_id = AsyncMock(return_value=123)
            mock_instance.get = AsyncMock(return_value=get_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await tp_delete_equipment("999")

        assert result["isError"] is True
        assert result["error_code"] == "NOT_FOUND"
