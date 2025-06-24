"""
Autogen-compatible tool classes
Creates Tool subclasses that properly handle session isolation and contracts from ToolsSpecification
"""
import json
from typing import List, Dict, Any, Optional
from typing_extensions import Annotated
from pydantic import BaseModel, Field
from autogen_core import CancellationToken
from autogen_core.tools import Tool
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
    packaging_type: Optional[int] = Field(description="Номер способа упаковки (опционально в случае нескольких способов)", default=None)


# Base class for session-aware tools
class SessionAwareTool(Tool):
    """Base class for tools that need session isolation"""
    
    def __init__(self, session_id: str, name: str, description: str):
        self.session_id = session_id
        super().__init__(name=name, description=description)


class RagFindProductsTool(SessionAwareTool):
    """Tool for finding products with session isolation"""
    
    def __init__(self, session_id: str):
        super().__init__(
            session_id=session_id,
            name="rag_find_products",
            description="Найти товары соответствующие описанию"
        )
    
    async def run(
        self,
        message: Annotated[str, "Описание товаров для поиска. Может содержать производителя, термическое состояние, способ упаковки, животное, объект, дополнительные указания"],
        execution_message: Annotated[str, "Сообщение пользователю при вызове инструмента. Должно вписываться в разговор естественно"],
        cancellation_token: CancellationToken
    ) -> str:
        """Найти товары соответствующие описанию"""
        try:
            result = await tool_emulator.call_tool(
                "rag_find_products", 
                {"message": message, "execution_message": execution_message},
                session_id=self.session_id
            )
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.log_error(f"rag_find_products failed: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)


class AddToCartTool(SessionAwareTool):
    """Tool for adding items to cart with session isolation"""
    
    def __init__(self, session_id: str):
        super().__init__(
            session_id=session_id,
            name="add_to_cart",
            description="Добавить товары в корзину"
        )
    
    async def run(
        self,
        items: Annotated[List[CartItem], "Список продуктов с количеством. Каждый элемент содержит код продукта, количество и опционально способ упаковки"],
        execution_message: Annotated[str, "Сообщение пользователю при вызове инструмента"],
        cancellation_token: CancellationToken
    ) -> str:
        """Вызывается только, когда известен товар, который необходо добавить! Для сохранения товара в корзину, когда пользователь точно уверен в своем выборе."""
        try:
            # Convert Pydantic models to dict format expected by tool_emulator
            items_dict = [item.model_dump() for item in items]
            
            result = await tool_emulator.call_tool(
                "add_to_cart",
                {"items": items_dict, "execution_message": execution_message},
                session_id=self.session_id
            )
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
            description="Удалить товары из корзины"
        )
    
    async def run(
        self,
        items: Annotated[List[str], "Список строк, где каждая строка равна коду продукта для удаления"],
        execution_message: Annotated[str, "Сообщение пользователю при вызове инструмента"],
        cancellation_token: CancellationToken
    ) -> str:
        """Вызывается только, когда известен товар, который необходо удалить! Для удаления товара из корзины."""
        try:
            result = await tool_emulator.call_tool(
                "remove_from_cart",
                {"items": items, "execution_message": execution_message},
                session_id=self.session_id
            )
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.log_error(f"remove_from_cart failed: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)


class GetCartTool(SessionAwareTool):
    """Tool for getting cart contents with session isolation"""
    
    def __init__(self, session_id: str):
        super().__init__(
            session_id=session_id,
            name="get_cart",
            description="Получить содержимое корзины"
        )
    
    async def run(
        self,
        execution_message: Annotated[str, "Сообщение пользователю при вызове инструмента"],
        cancellation_token: CancellationToken
    ) -> str:
        """Для получения всех товаров из корзины."""
        try:
            result = await tool_emulator.call_tool(
                "get_cart",
                {"execution_message": execution_message},
                session_id=self.session_id
            )
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
            description="Изменить дату доставки"
        )
    
    async def run(
        self,
        delivery_date: Annotated[str, "Дата доставки в формате YYYY-MM-DD"],
        execution_message: Annotated[str, "Сообщение пользователю при вызове инструмента"],
        cancellation_token: CancellationToken
    ) -> str:
        """Изменяет дату доставки"""
        try:
            result = await tool_emulator.call_tool(
                "change_delivery_date",
                {"delivery_date": delivery_date, "execution_message": execution_message},
                session_id=self.session_id
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
            description="Установить адрес доставки"
        )
    
    async def run(
        self,
        location_id: Annotated[int, "Номер адреса, на который необходимо оформить заказ. Можно выбрать из списка доступных адресов"],
        execution_message: Annotated[str, "Сообщение пользователю при вызове инструмента"],
        cancellation_token: CancellationToken
    ) -> str:
        """Устанавливает адрес, на который оформляется заказ"""
        try:
            result = await tool_emulator.call_tool(
                "set_current_location",
                {"location_id": location_id, "execution_message": execution_message},
                session_id=self.session_id
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
            description="Transfer call to human operator"
        )
    
    async def run(
        self,
        reason: Annotated[str, "Reason for transferring the call"],
        cancellation_token: CancellationToken
    ) -> str:
        """Transfer the call to a human operator"""
        try:
            result = await tool_emulator.call_tool(
                "call_transfer",
                {"reason": reason},
                session_id=self.session_id
            )
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.log_error(f"call_transfer failed: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)


class EndCallTool(SessionAwareTool):
    """Tool for ending call with session isolation"""
    
    def __init__(self, session_id: str):
        super().__init__(
            session_id=session_id,
            name="end_call",
            description="End the conversation"
        )
    
    async def run(
        self,
        reason: Annotated[str, "Reason for ending the call"],
        cancellation_token: CancellationToken
    ) -> str:
        """End the conversation"""
        try:
            result = await tool_emulator.call_tool(
                "end_call",
                {"reason": reason},
                session_id=self.session_id
            )
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.log_error(f"end_call failed: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)


class AutogenToolFactory:
    """
    Factory for creating session-isolated Autogen Tool instances
    Each conversation gets its own set of tools with proper session_id isolation
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        
    def get_tools_for_agent(self, tool_names: List[str]) -> List[Tool]:
        """
        Get Tool instances for the specified tool names
        Maps tool names from ToolsSpecification to actual Tool objects
        """
        tool_map = {
            'rag_find_products': lambda: RagFindProductsTool(self.session_id),
            'add_to_cart': lambda: AddToCartTool(self.session_id),
            'remove_from_cart': lambda: RemoveFromCartTool(self.session_id),
            'get_cart': lambda: GetCartTool(self.session_id),
            'change_delivery_date': lambda: ChangeDeliveryDateTool(self.session_id),
            'set_current_location': lambda: SetCurrentLocationTool(self.session_id),
            'call_transfer': lambda: CallTransferTool(self.session_id),
            'end_call': lambda: EndCallTool(self.session_id)
        }
        
        tools = []
        for tool_name in tool_names:
            if tool_name in tool_map:
                tool = tool_map[tool_name]()
                tools.append(tool)
                logger.log_info(f"Created Tool '{tool_name}' for session {self.session_id}")
            else:
                logger.log_warning(f"Unknown tool '{tool_name}' requested for session {self.session_id}")
        
        return tools