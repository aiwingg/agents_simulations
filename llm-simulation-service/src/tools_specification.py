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
                "description": "Search for products in the database using RAG (Retrieval-Augmented Generation)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The search query for products"
                        }
                    },
                    "required": ["message"]
                }
            }
        },
        "add_to_cart": {
            "type": "function",
            "function": {
                "name": "add_to_cart",
                "description": "Add products to the shopping cart",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "products": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "product_code": {"type": "string"},
                                    "quantity": {"type": "integer"},
                                    "packaging_type": {"type": "integer", "description": "Optional packaging type number"}
                                },
                                "required": ["product_code", "quantity"]
                            },
                            "description": "List of products to add to cart"
                        }
                    },
                    "required": ["products"]
                }
            }
        },
        "remove_from_cart": {
            "type": "function",
            "function": {
                "name": "remove_from_cart",
                "description": "Remove products from the shopping cart",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_code": {
                            "type": "string",
                            "description": "The product code to remove from cart"
                        }
                    },
                    "required": ["product_code"]
                }
            }
        },
        "get_cart": {
            "type": "function",
            "function": {
                "name": "get_cart",
                "description": "Get the current contents of the shopping cart",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        "change_delivery_date": {
            "type": "function",
            "function": {
                "name": "change_delivery_date",
                "description": "Change the delivery date for the order",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "delivery_date": {
                            "type": "string",
                            "description": "The new delivery date"
                        }
                    },
                    "required": ["delivery_date"]
                }
            }
        },
        "set_current_location": {
            "type": "function",
            "function": {
                "name": "set_current_location",
                "description": "Set the delivery location for the order",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The delivery address"
                        }
                    },
                    "required": ["location"]
                }
            }
        },
        "call_transfer": {
            "type": "function",
            "function": {
                "name": "call_transfer",
                "description": "Transfer the call to a human operator",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Reason for transferring the call"
                        }
                    },
                    "required": ["reason"]
                }
            }
        },
        "end_call": {
            "type": "function",
            "function": {
                "name": "end_call",
                "description": "End the conversation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Reason for ending the call"
                        }
                    },
                    "required": ["reason"]
                }
            }
        }
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
    def get_tools_by_names(cls, tool_names: List[str], handoffs: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
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
            if tool_name.startswith('handoff_'):
                # This is a handoff tool - generate it dynamically
                target_agent = tool_name.replace('handoff_', '')
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
                        "reason": {
                            "type": "string",
                            "description": "Reason for the handoff"
                        },
                        "context": {
                            "type": "string",
                            "description": "Brief context about the conversation so far"
                        }
                    },
                    "required": ["reason"]
                }
            }
        }
    
    @classmethod
    def is_handoff_tool(cls, tool_name: str) -> bool:
        """Check if a tool name represents a handoff tool"""
        return tool_name.startswith('handoff_')
    
    @classmethod
    def get_handoff_target_agent(cls, tool_name: str) -> Optional[str]:
        """Extract the target agent name from a handoff tool name"""
        if cls.is_handoff_tool(tool_name):
            return tool_name.replace('handoff_', '')
        return None