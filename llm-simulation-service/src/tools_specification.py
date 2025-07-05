"""
Tools specification for conversation simulation
Defines available tools and handles handoff tool generation
"""

from typing import Dict, List, Any, Optional


class ToolsSpecification:
    """Specification for tools available in the conversation system"""

    # Define all available tools with their schemas
    AVAILABLE_TOOLS = {
        "rag_find_products": {
            "type": "function",
            "function": {
                "name": "rag_find_products",
                "description": "Найти товары соответствующие описанию",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "title": "Message",
                            "type": "string",
                            "description": 'Описание товаров для поиска. Описание может содержать\n- Специфичного производителя, например "ООО Золотой Бык"\n- Термическое состояние (охлажденное, замороженное, и тд)\n- Способ упаковки (пакет, поштучно, и тд)\n- Животное (курица, говядина, и тд)\n- Объект (курица, грудка, и тд)\n- Дополнительные указания, например "в маринаде"\n\nПример описания: "курица замороженная, в маринаде, 100 кг, упаковка по 1 кг"\n',
                        },
                        "execution_message": {
                            "type": "string",
                            "description": "The message you will say to user when calling this tool. Make sure it fits into the conversation smoothly. Do not use a question. Use everyday language.",
                        },
                    },
                    "required": ["message", "execution_message"],
                },
            },
        },
        "add_to_cart": {
            "type": "function",
            "function": {
                "name": "add_to_cart",
                "description": "Вызывается только, когда известен товар, который необходо добавить! Для сохранения товара в корзину, когда пользователь точно уверен в своем выборе. Принимает код товара и кол-во, и номер способа упаковки в случае наличия нескольких вариантов",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "description": "Список продуктов с количеством. Каждый элемент содержит:\n- код продукта (можно получить через инструмент rag_find_products)\n- количество продукта (в штуках, кг и т.д.)",
                            "type": "array",
                            "title": "Items",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "product_code": {
                                        "type": "string",
                                        "description": "Код продукта из rag_find_products",
                                    },
                                    "quantity": {
                                        "type": "number",
                                        "description": "Количество продукта (шт, кг и т.п.)",
                                    },
                                    "packaging_type": {
                                        "type": "integer",
                                        "description": "Номер способа упаковки (опционально в случае нескольких способов)",
                                    },
                                },
                                "required": ["product_code", "quantity"],
                            },
                        },
                        "execution_message": {
                            "type": "string",
                            "description": "The message you will say to user when calling this tool. Make sure it fits into the conversation smoothly. Do not use a question. Use everyday language.",
                        },
                    },
                    "required": ["items", "execution_message"],
                },
            },
        },
        "remove_from_cart": {
            "type": "function",
            "function": {
                "name": "remove_from_cart",
                "description": "Вызывается только, когда известен товар, который необходо удалить! Для удаления товара из корзины. Принимает код товара.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "description": "Функция принимает список строк, где каждая строка должна быть равна коду продукта, который можно получить из инструмента rag_find_products\n",
                            "title": "Items",
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "execution_message": {
                            "type": "string",
                            "description": "The message you will say to user when calling this tool. Make sure it fits into the conversation smoothly. Do not use a question. Use everyday language.",
                        },
                    },
                    "required": ["items", "execution_message"],
                },
            },
        },
        "get_cart": {
            "type": "function",
            "function": {
                "name": "get_cart",
                "description": "Для получения всех товаров из карзины.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "execution_message": {
                            "type": "string",
                            "description": "The message you will say to user when calling this tool. Make sure it fits into the conversation smoothly. Do not use a question. Use everyday language.",
                        }
                    },
                    "required": ["execution_message"],
                },
            },
        },
        "change_delivery_date": {
            "type": "function",
            "function": {
                "name": "change_delivery_date",
                "description": "Изменяет дату доставки",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "delivery_date": {"type": "string", "description": "Дата доставки в формате YYYY-MM-DD"},
                        "execution_message": {
                            "type": "string",
                            "description": "The message you will say to user when calling this tool. Make sure it fits into the conversation smoothly. Do not use a question. Use everyday language.",
                        },
                    },
                    "required": ["delivery_date", "execution_message"],
                },
            },
        },
        "set_current_location": {
            "type": "function",
            "function": {
                "name": "set_current_location",
                "description": "Устанавливает адрес, на который оформляется заказ",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location_id": {
                            "type": "integer",
                            "description": "Номер адреса, на который необходимо оформить заказ. Можно выбрать из списка доступных адресов. По умолчанию используется адрес с индексом 1.",
                        },
                        "execution_message": {
                            "type": "string",
                            "description": "The message you will say to user when calling this tool. Make sure it fits into the conversation smoothly. Do not use a question. Use everyday language.",
                        },
                    },
                    "required": ["location_id", "execution_message"],
                },
            },
        },
        "call_transfer": {
            "type": "function",
            "function": {
                "name": "call_transfer",
                "description": "Transfer call to human operator",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string", "description": "Reason for transferring the call"}
                    },
                    "required": ["reason"],
                },
            },
        },
    }

    @classmethod
    def get_available_tool_names(cls) -> List[str]:
        """Get list of all available tool names"""
        return list(cls.AVAILABLE_TOOLS.keys())

    @classmethod
    def get_tool_schema(cls, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific tool"""
        return cls.AVAILABLE_TOOLS.get(tool_name)

    @classmethod
    def get_tools_by_names(
        cls, tool_names: List[str], handoffs: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get tool schemas for the specified tool names.
        Automatically generates handoff tools based on handoffs configuration.

        Args:
            tool_names: List of tool names to include
            handoffs: Dictionary of {agent_name: description} for handoff generation

        Returns:
            List of tool schemas
        """
        schemas = []

        for tool_name in tool_names:
            if tool_name.startswith("handoff_"):
                # This is a handoff tool - generate it dynamically
                target_agent = tool_name.replace("handoff_", "")
                if handoffs and target_agent in handoffs:
                    handoff_description = handoffs[target_agent]
                    schema = cls._generate_handoff_tool_schema(target_agent, handoff_description)
                    schemas.append(schema)
            else:
                # Regular tool - get from predefined schemas
                schema = cls.get_tool_schema(tool_name)
                if schema:
                    schemas.append(schema)

        return schemas

    @classmethod
    def _generate_handoff_tool_schema(cls, target_agent: str, description: str) -> Dict[str, Any]:
        """Generate a handoff tool schema for transferring to another agent"""
        return {
            "type": "function",
            "function": {
                "name": f"handoff_{target_agent}",
                "description": f"Transfer the conversation to {target_agent}. {description}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string", "description": "Reason for the handoff"},
                        "context": {"type": "string", "description": "Brief context about the conversation so far"},
                    },
                    "required": ["reason"],
                },
            },
        }

    @classmethod
    def is_handoff_tool(cls, tool_name: str) -> bool:
        """Check if a tool name represents a handoff tool"""
        return tool_name.startswith("handoff_")

    @classmethod
    def get_handoff_target_agent(cls, tool_name: str) -> Optional[str]:
        """Extract the target agent name from a handoff tool name"""
        if cls.is_handoff_tool(tool_name):
            return tool_name.replace("handoff_", "")
        return None
