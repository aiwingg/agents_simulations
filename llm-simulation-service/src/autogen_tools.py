"""
Autogen-compatible tool classes
Creates Tool subclasses that properly handle session isolation and contracts from ToolsSpecification
"""

import json
from typing import List, Dict, Any, Optional, Type
from typing_extensions import Annotated
from pydantic import BaseModel, Field
from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from src.tool_emulator import ToolEmulator
from src.logging_utils import get_logger

# Global tool emulator instance
tool_emulator = ToolEmulator()
logger = get_logger()


# Pydantic models for complex tool parameters based on ToolsSpecification


class CartItem(BaseModel):
    """Item to add to cart"""

    product_code: str = Field(description="Код продукта из rag_find_products")
    quantity: float = Field(description="Количество продукта (шт, кг и т.п.)")
    packaging_type: int = Field(
        description="Номер способа упаковки, если всего 1, то 1"
    )


class RagFindProductsArgs(BaseModel):
    message: Annotated[
        str,
        "Описание товаров для поиска. Может содержать производителя, термическое состояние, способ упаковки, животное, объект, дополнительные указания",
    ]


class AddToCartArgs(BaseModel):
    items: Annotated[
        List[CartItem],
        "Список продуктов с количеством. Каждый элемент содержит код продукта, количество и опционально способ упаковки",
    ]


class RemoveFromCartArgs(BaseModel):
    items: Annotated[List[str], "Список строк, где каждая строка равна коду продукта для удаления"]


class GetCartArgs(BaseModel):
    pass


class ChangeDeliveryDateArgs(BaseModel):
    delivery_date: Annotated[str, "Дата доставки в формате YYYY-MM-DD"]


class SetCurrentLocationArgs(BaseModel):
    location_id: Annotated[
        int, "Номер адреса, на который необходимо оформить заказ. Можно выбрать из списка доступных адресов"
    ]


class CallTransferArgs(BaseModel):
    reason: Annotated[str, "Reason for transferring the call"]


class JsonOutput(BaseModel):
    """Generic JSON string output"""

    output: str = Field(description="JSON-encoded string representing the tool's output")


# Base class for session-aware tools
class SessionAwareTool(BaseTool):
    """Base class for tools that need session isolation"""

    def __init__(self, session_id: str, name: str, description: str, args_type: Type[BaseModel]):
        self.session_id = session_id
        # All tools return a JSON string
        super().__init__(name=name, description=description, args_type=args_type, return_type=JsonOutput)


class RagFindProductsTool(SessionAwareTool):
    """Tool for finding products with session isolation"""

    def __init__(self, session_id: str):
        super().__init__(
            session_id=session_id,
            name="rag_find_products",
            description="Найти товары соответствующие описанию",
            args_type=RagFindProductsArgs,
        )

    async def run(self, args: RagFindProductsArgs, cancellation_token: CancellationToken) -> str:
        """Найти товары соответствующие описанию"""
        try:
            result = await tool_emulator.call_tool(
                "rag_find_products", {"message": args.message}, session_id=self.session_id
            )
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.log_error(f"rag_find_products failed: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)


class AddToCartTool(SessionAwareTool):
    """Tool for adding items to cart with session isolation"""

    def __init__(self, session_id: str):
        super().__init__(
            session_id=session_id, name="add_to_cart", description="Добавить товары в корзину", args_type=AddToCartArgs
        )

    async def run(self, args: AddToCartArgs, cancellation_token: CancellationToken) -> str:
        """Вызывается только, когда известен товар, который необходо добавить! Для сохранения товара в корзину, когда пользователь точно уверен в своем выборе."""
        try:
            # Convert Pydantic models to dict format expected by tool_emulator
            items_dict = [item.model_dump() for item in args.items]

            result = await tool_emulator.call_tool("add_to_cart", {"items": items_dict}, session_id=self.session_id)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.log_error(f"add_to_cart failed: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)


class RemoveFromCartTool(SessionAwareTool):
    """Tool for removing items from cart with session isolation"""

    def __init__(self, session_id: str):
        super().__init__(
            session_id=session_id,
            name="remove_from_cart",
            description="Удалить товары из корзины",
            args_type=RemoveFromCartArgs,
        )

    async def run(self, args: RemoveFromCartArgs, cancellation_token: CancellationToken) -> str:
        """Вызывается только, когда известен товар, который необходо удалить! Для удаления товара из корзины."""
        try:
            result = await tool_emulator.call_tool(
                "remove_from_cart", {"items": args.items}, session_id=self.session_id
            )
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.log_error(f"remove_from_cart failed: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)


class GetCartTool(SessionAwareTool):
    """Tool for getting cart contents with session isolation"""

    def __init__(self, session_id: str):
        super().__init__(
            session_id=session_id, name="get_cart", description="Получить содержимое корзины", args_type=GetCartArgs
        )

    async def run(self, args: GetCartArgs, cancellation_token: CancellationToken) -> str:
        """Для получения всех товаров из корзины."""
        try:
            result = await tool_emulator.call_tool("get_cart", {}, session_id=self.session_id)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.log_error(f"get_cart failed: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)


class ChangeDeliveryDateTool(SessionAwareTool):
    """Tool for changing delivery date with session isolation"""

    def __init__(self, session_id: str):
        super().__init__(
            session_id=session_id,
            name="change_delivery_date",
            description="Изменить дату доставки",
            args_type=ChangeDeliveryDateArgs,
        )

    async def run(self, args: ChangeDeliveryDateArgs, cancellation_token: CancellationToken) -> str:
        """Изменяет дату доставки"""
        try:
            result = await tool_emulator.call_tool(
                "change_delivery_date", {"delivery_date": args.delivery_date}, session_id=self.session_id
            )
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.log_error(f"change_delivery_date failed: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)


class SetCurrentLocationTool(SessionAwareTool):
    """Tool for setting current location with session isolation"""

    def __init__(self, session_id: str):
        super().__init__(
            session_id=session_id,
            name="set_current_location",
            description="Установить адрес доставки",
            args_type=SetCurrentLocationArgs,
        )

    async def run(self, args: SetCurrentLocationArgs, cancellation_token: CancellationToken) -> str:
        """Устанавливает адрес, на который оформляется заказ"""
        try:
            result = await tool_emulator.call_tool(
                "set_current_location", {"location_id": args.location_id}, session_id=self.session_id
            )
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.log_error(f"set_current_location failed: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)


class CallTransferTool(SessionAwareTool):
    """Tool for transferring call with session isolation"""

    def __init__(self, session_id: str):
        super().__init__(
            session_id=session_id,
            name="call_transfer",
            description="Transfer call to human operator",
            args_type=CallTransferArgs,
        )

    async def run(self, args: CallTransferArgs, cancellation_token: CancellationToken) -> str:
        """Transfer the call to a human operator"""
        try:
            result = await tool_emulator.call_tool("call_transfer", {"reason": args.reason}, session_id=self.session_id)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.log_error(f"call_transfer failed: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)


class AutogenToolFactory:
    """
    Factory for creating session-isolated Autogen Tool instances
    Each conversation gets its own set of tools with proper session_id isolation
    """

    def __init__(self, session_id: str):
        self.session_id = session_id

    def get_tools_for_agent(self, tool_names: List[str]) -> List[BaseTool]:
        """
        Get Tool instances for the specified tool names
        Maps tool names from ToolsSpecification to actual Tool objects
        """
        tool_map = {
            "rag_find_products": RagFindProductsTool,
            "add_to_cart": AddToCartTool,
            "remove_from_cart": RemoveFromCartTool,
            "get_cart": GetCartTool,
            "change_delivery_date": ChangeDeliveryDateTool,
            "set_current_location": SetCurrentLocationTool,
            "call_transfer": CallTransferTool,
        }

        tools = []
        for tool_name in tool_names:
            if tool_name in tool_map:
                tool_class = tool_map[tool_name]
                tool_instance = tool_class(self.session_id)
                tools.append(tool_instance)
                logger.log_info(f"Created Tool '{tool_name}' for session {self.session_id}")
            else:
                logger.log_warning(f"Unknown tool '{tool_name}' requested for session {self.session_id}")

        return tools
