"""
Tool emulation system for conversation simulation
"""
import json
import random
from typing import Dict, Any, List, Optional
from src.logging_utils import get_logger

class ToolEmulator:
    """Emulates external tools/APIs for conversation simulation"""
    
    def __init__(self):
        self.logger = get_logger()
        
        # Sample data for tool responses
        self.menu_items = [
            {"name": "филе курицы", "price": 450, "category": "мясо"},
            {"name": "пицца маргарита", "price": 650, "category": "пицца"},
            {"name": "суши сет", "price": 890, "category": "суши"},
            {"name": "роллы филадельфия", "price": 520, "category": "роллы"},
            {"name": "борщ", "price": 280, "category": "супы"},
            {"name": "салат цезарь", "price": 380, "category": "салаты"}
        ]
        
        self.delivery_zones = [
            {"zone": "центр", "delivery_time": "30-45 мин", "fee": 0},
            {"zone": "север", "delivery_time": "45-60 мин", "fee": 100},
            {"zone": "юг", "delivery_time": "40-55 мин", "fee": 80},
            {"zone": "восток", "delivery_time": "50-65 мин", "fee": 120},
            {"zone": "запад", "delivery_time": "35-50 мин", "fee": 90}
        ]
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Simulate calling an external tool"""
        
        self.logger.log_info(f"Tool call: {tool_name}", extra_data={
            'session_id': session_id,
            'parameters': parameters
        })
        
        try:
            if tool_name == "search_menu":
                return await self._search_menu(parameters)
            elif tool_name == "check_availability":
                return await self._check_availability(parameters)
            elif tool_name == "calculate_delivery":
                return await self._calculate_delivery(parameters)
            elif tool_name == "create_order":
                return await self._create_order(parameters)
            elif tool_name == "get_customer_history":
                return await self._get_customer_history(parameters)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            self.logger.log_error(f"Tool emulation error for {tool_name}", exception=e)
            return {"error": f"Tool execution failed: {str(e)}"}
    
    async def _search_menu(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Emulate menu search"""
        query = parameters.get("query", "").lower()
        category = parameters.get("category", "").lower()
        
        results = []
        for item in self.menu_items:
            if (not query or query in item["name"].lower()) and \
               (not category or category in item["category"].lower()):
                results.append(item)
        
        return {
            "status": "success",
            "results": results,
            "total_found": len(results)
        }
    
    async def _check_availability(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Emulate availability check"""
        item_name = parameters.get("item_name", "")
        quantity = parameters.get("quantity", 1)
        
        # Simulate random availability
        available = random.choice([True, True, True, False])  # 75% chance available
        
        if available:
            return {
                "status": "available",
                "item": item_name,
                "quantity_available": quantity + random.randint(0, 10),
                "estimated_prep_time": f"{random.randint(15, 45)} мин"
            }
        else:
            return {
                "status": "unavailable",
                "item": item_name,
                "reason": "временно отсутствует",
                "alternatives": random.sample([item["name"] for item in self.menu_items], 2)
            }
    
    async def _calculate_delivery(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Emulate delivery calculation"""
        address = parameters.get("address", "")
        
        # Simulate zone detection
        zone_info = random.choice(self.delivery_zones)
        
        return {
            "status": "success",
            "zone": zone_info["zone"],
            "delivery_time": zone_info["delivery_time"],
            "delivery_fee": zone_info["fee"],
            "address": address
        }
    
    async def _create_order(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Emulate order creation"""
        items = parameters.get("items", [])
        customer_info = parameters.get("customer_info", {})
        
        order_id = f"ORD-{random.randint(10000, 99999)}"
        total_amount = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
        
        return {
            "status": "created",
            "order_id": order_id,
            "total_amount": total_amount,
            "estimated_delivery": f"{random.randint(30, 60)} мин",
            "items": items,
            "customer": customer_info
        }
    
    async def _get_customer_history(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Emulate customer history lookup"""
        phone = parameters.get("phone", "")
        
        # Simulate customer history
        has_history = random.choice([True, False])
        
        if has_history:
            return {
                "status": "found",
                "customer_id": f"CUST-{random.randint(1000, 9999)}",
                "previous_orders": random.randint(1, 15),
                "favorite_items": random.sample([item["name"] for item in self.menu_items], 2),
                "last_order_date": "2025-05-28"
            }
        else:
            return {
                "status": "not_found",
                "message": "новый клиент"
            }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools and their descriptions"""
        return [
            {
                "name": "search_menu",
                "description": "Search menu items by name or category",
                "parameters": ["query", "category"]
            },
            {
                "name": "check_availability",
                "description": "Check if item is available in requested quantity",
                "parameters": ["item_name", "quantity"]
            },
            {
                "name": "calculate_delivery",
                "description": "Calculate delivery time and fee for address",
                "parameters": ["address"]
            },
            {
                "name": "create_order",
                "description": "Create new order with items and customer info",
                "parameters": ["items", "customer_info"]
            },
            {
                "name": "get_customer_history",
                "description": "Get customer order history by phone number",
                "parameters": ["phone"]
            }
        ]

