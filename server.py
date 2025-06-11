from fastapi import FastAPI, HTTPException, Query, Depends, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
from typing import Dict, Optional, List, Tuple
import uvicorn
import hydra
from omegaconf import DictConfig
from hydra import compose, initialize
from opentelemetry import trace
import json
import logging
import logging.config
import yaml
from pathlib import Path
from uuid import uuid4
from session import Session
from vtd_client import VTDClient
from vtd_connector import VTDConnector
from schedules import ScheduleManager
from rag_clean import RAG
from querry_yandex_db import get_random_client
import hashlib
from datetime import datetime
import os
#zerodiff
# Configure logging
log_config_path = Path(__file__).parent / "logging.yaml"
with open(log_config_path) as f:
    log_config = yaml.safe_load(f)
    logging.config.dictConfig(log_config)

logger = logging.getLogger("rag")

app = FastAPI(title="RAG Service API", description="API for RAG-based product search", root_path="/rag")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
vtd_client = None
vtd_connector = None
rag = None
sessions = {}
schedule_manager = None

def register_payload_handlers(HANDLES):
    for handle_name, handler_func in HANDLES.items():
        def create_handler(handle_name, handler_func):
            async def handler(request: Request):
    
                post_data = await request.json()
                logger.info(f"Received request for endpoint {handle_name}: {post_data}")
                try:
                    dynvars = post_data['call']['retell_llm_dynamic_variables']
                    session_id = dynvars.get('session_id', None)
                    if not session_id or session_id not in sessions:
                        try:
                            if not session_id:
                                user_phone = post_data['call']['retell_llm_dynamic_variables']['user_number']
                                session_id = hashlib.md5(user_phone.encode()).hexdigest()
                            if session_id not in sessions:
                                clients = await vtd_connector.get_client(user_phone)
                                sessions[session_id] = Session(rag, clients, schedule_manager)
                                logger.info(f"Created new session with ID: {session_id}")
                        except Exception as e:
                            logger.error(f"Failed to process client data: {str(e)}", exc_info=True)
                            raise HTTPException(status_code=500, detail="Failed to create new session from user phone")
                    
                    logger.debug(f"handling /{handle_name} request for session {session_id}")
                    session = sessions[session_id]
                    # Call the appropriate session method based on the handler
                    result = await handler_func(session=session, **post_data['args'])
                    
                except KeyError as e:
                    logger.error(f"Missing required data: {str(e)}")
                    raise HTTPException(status_code=400, detail=f"Missing required data: {str(e)}")
                except Exception as e:
                    logger.error(f"Error processing request for endpoint {handle_name}: {str(e)}", exc_info=True)
                    return {"result": "Ошибка при выполнении запроса"}
                
                return result
            return handler
            
        endpoint_path = f"/{handle_name}"
        app.post(endpoint_path, response_class=JSONResponse)(create_handler(handle_name, handler_func))
        logger.info(f"Registered endpoint: {endpoint_path}")

@app.on_event("startup")
async def startup_event():
    """Initialize the RAG handler and other dependencies on startup"""
    global vtd_client, vtd_connector, rag, schedule_manager
    logger.info("Starting RAG service initialization")
    
    with initialize(version_base=None, config_path="../../configs"):
        cfg = compose(config_name="rag_config")
    
    # Initialize all required components
    vtd_client = VTDClient()
    vtd_connector = VTDConnector(vtd_client)
    rag = RAG(vtd_connector, cfg)
    schedule_manager = ScheduleManager(await vtd_connector.get_producer_schedules())
    
    logger.info("RAG handler and dependencies initialized successfully")

    # Update HANDLES to use session methods directly
    HANDLES = {
        'rag_find_products': lambda session, message: session.find_products(message),
        'add_to_cart': lambda session, items: session.add_to_cart(items),
        'remove_from_cart': lambda session, items: session.remove_from_cart(items),
        'get_cart': lambda session: session.get_cart(),
        'get_purchase_history': lambda session: session.get_purchase_history(),
        'change_delivery_date': lambda session, delivery_date: session.change_delivery_date(delivery_date),
        'set_current_location': lambda session, location_id: session.set_current_location(location_id)
    }
    register_payload_handlers(HANDLES)
    logger.info("All endpoints registered successfully")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if rag is None:
        logger.error("Health check failed: Service not initialized")
        raise HTTPException(status_code=503, description="Service not initialized")
    logger.info("Health check passed successfully")
    return {"status": "healthy"}

async def get_client_by_number(user_number : str):
    client_number = await get_random_client(tester_id=user_number)
    if client_number:
        # if tester makes call
        # get client number for this tester
        clients = await vtd_connector.get_client(client_number)
    else:
        # if we make web call or for clients who don't have tester
        clients = await vtd_connector.get_client(user_number)
    
    if len(clients) == 0:
        # client = await vtd_connector.get_random_client() 
        #TODO: remove this line after testing
        clients = await vtd_connector.get_client("9280291870")
    return clients

@app.get("/get_orders")
async def get_orders(client_number: str = Query(..., description="Client phone number")):
    clients = await get_client_by_number(client_number)
    orders = await vtd_client.get_orders([client.clientId for client in clients])
    return JSONResponse(content=orders)
        
@app.post("/webhook")
async def handle_webhook(request: Request):
    """
    Webhook для получения дополнительной информации о клиенте по номеру телефона
    """
    global rag, vtd_connector

    payload = await request.json()
    logger.info(f"/webhook Received webhook payload: {payload}")

    try:
        inbound_info = payload["call_inbound"]
        user_number = inbound_info["from_number"]
    except KeyError:
        logger.error("Invalid payload structure")
        raise HTTPException(status_code=400, detail="Invalid payload structure")
    
    logger.info(f"Matching client with number: {user_number}")

    try:
        clients = await get_client_by_number(user_number)
        session = Session(rag, clients, schedule_manager)
        sessions[session.session_id] = session
        response_data = {
            "call_inbound": {
                "dynamic_variables": session.get_dynamic_variables()
            }
        }
        response_data['call_inbound']['dynamic_variables']['session_id'] = session.session_id
        logger.info(f"Created new session with ID: {session.session_id}")

    except Exception as e:
        logger.error(f"Failed to process client data: {str(e)}")
        import traceback
        logger.error(f"Failed to process client data: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to process client data")

    logger.info(f"webhook response: {json.dumps(response_data, ensure_ascii=False)}")
    return JSONResponse(content=response_data)


from chatwoot.client import ChatwootClient

@app.post("/new_webhook")
async def handle_new_webhook(request: Request):
    """
    Webhook for new web call
    """
    payload = await request.json()
    logger.info(f"Received request for /new_webhook: {payload}")
    if payload['event'] == "call_started":
        logger.info(f"Started call  {payload['call']['call_id']}")
        return
    elif payload['event'] == "call_ended":
        logger.info(f"Ended call from {payload['call']['call_id']}")
        dynvars = payload['call']['retell_llm_dynamic_variables']
        session_id = dynvars['session_id']
        try:
            session_id = dynvars['session_id']
            session = sessions[session_id]
            await session.commit_order() # TODO: provide as tool to llm
            del sessions[session_id]
        except KeyError:
            logger.error(f"No session ID {session_id} found in dynamic variables")
            return
        try:
            chatwoot_acc_id = int(dynvars['chatwoot_account_id'])
        except KeyError:
            logger.error("No chatwoot account ID found in dynamic variables")
            return
        chatwoot_client = ChatwootClient(token = os.getenv("CHATWOOT_TOKEN"), account_id = chatwoot_acc_id)
        role_map = {
            'user' : ChatwootClient.MessageType.INCOMING,
            'agent': ChatwootClient.MessageType.OUTGOING,
        }
        contact = chatwoot_client.find_contact()
        conversation = chatwoot_client.create_conversation(contact)

        for message in payload['call']['transcript_object']:
            try:
                message_type = role_map[message['role']]
            except KeyError:
                continue
            chatwoot_client.add_message(conversation, message['content'], message_type)
        return
