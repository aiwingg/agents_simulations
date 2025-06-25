"""
OpenAI API wrapper with retry logic and rate limiting
"""
import asyncio
import json
import time
import uuid
import os
from typing import Dict, List, Optional, Any, Tuple
from openai import AsyncOpenAI
from asyncio_throttle import Throttler
import random
from src.config import Config
from src.logging_utils import get_logger

# Braintrust imports
from braintrust import init_logger, wrap_openai

class OpenAIWrapper:
    """Wrapper for OpenAI API with retry logic and rate limiting"""
    
    def __init__(self, api_key: str, model: str = None, max_retries: int = 3):
        # Initialize standard OpenAI client
        self.client = AsyncOpenAI(api_key=api_key)
        
        # Initialize Braintrust tracing
        if os.getenv('BRAINTRUST_API_KEY'):
            try:
                self.braintrust_logger = init_logger(
                    project="LLM Simulation Service",
                    api_key=os.getenv('BRAINTRUST_API_KEY')
                )
                # Wrap the OpenAI client with Braintrust tracing
                self.client = wrap_openai(self.client)
                self.logger = get_logger()
                self.logger.log_info("Braintrust tracing initialized successfully")
            except Exception as e:
                self.logger = get_logger()
                self.logger.log_error(f"Failed to initialize Braintrust tracing: {e}")
        else:
            self.logger = get_logger()
            self.logger.log_info("BRAINTRUST_API_KEY not set - tracing disabled")
        
        self.model = model or Config.OPENAI_MODEL
        self.max_retries = max_retries
        self.throttler = Throttler(rate_limit=200, period=1)  # 200 requests per second
        
        # Token cost estimates (per 1K tokens) - approximate values
        self.token_costs = {
            'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
            'gpt-4.1-mini': {'input': 0.0003, 'output': 0.0012},
            'gpt-4o': {'input': 0.005, 'output': 0.015},
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002}
        }
    
    async def _make_request_with_retry(self, messages: List[Dict[str, str]], 
                                     session_id: str, 
                                     temperature: float = 0.7,
                                     seed: Optional[int] = None,
                                     response_format: Optional[Dict[str, str]] = None,
                                     tools: Optional[List[Dict[str, Any]]] = None) -> Tuple[Any, Dict[str, int]]:
        """Make OpenAI API request with retry logic"""
        
        # Generate unique request ID for tracking
        request_id = str(uuid.uuid4())
        
        # Log the request
        self.logger.log_openai_request(
            session_id=session_id,
            request_id=request_id,
            model=self.model,
            messages=messages,
            temperature=temperature,
            seed=seed,
            tools=tools,
            response_format=response_format
        )
        
        for attempt in range(self.max_retries):
            request_start_time = time.time()
            
            try:
                async with self.throttler:
                    # Prepare request parameters
                    request_params = {
                        'model': self.model,
                        'messages': messages,
                        'temperature': temperature,
                    }
                    
                    if seed is not None:
                        request_params['seed'] = seed
                    
                    if response_format:
                        request_params['response_format'] = response_format
                    
                    if tools:
                        request_params['tools'] = tools
                        request_params['tool_choice'] = 'auto'
                    
                    # Make the API call
                    response = await self.client.chat.completions.create(**request_params)
                    
                    # Calculate request duration
                    duration_ms = (time.time() - request_start_time) * 1000
                    
                    # Extract response data
                    message = response.choices[0].message
                    
                    # Return the full message object if tools were used, otherwise just content
                    if tools and hasattr(message, 'tool_calls') and message.tool_calls:
                        content = message  # Return full message object with tool_calls
                    else:
                        content = message.content
                    usage = {
                        'prompt_tokens': response.usage.prompt_tokens,
                        'completion_tokens': response.usage.completion_tokens,
                        'total_tokens': response.usage.total_tokens
                    }
                    
                    # Calculate cost estimate
                    cost_estimate = self._calculate_cost(usage)
                    
                    # Log successful response
                    self.logger.log_openai_response(
                        session_id=session_id,
                        request_id=request_id,
                        response_content=message,
                        usage=usage,
                        cost_estimate=cost_estimate,
                        duration_ms=duration_ms,
                        attempt=attempt + 1
                    )
                    
                    # Log token usage
                    self.logger.log_token_usage(
                        session_id=session_id,
                        model=self.model,
                        prompt_tokens=usage['prompt_tokens'],
                        completion_tokens=usage['completion_tokens'],
                        total_tokens=usage['total_tokens'],
                        cost_estimate=cost_estimate
                    )
                    
                    return content, usage
                    
            except Exception as e:
                # Calculate request duration for failed request
                duration_ms = (time.time() - request_start_time) * 1000
                
                error_context = {
                    'session_id': session_id, 
                    'model': self.model,
                    'attempt': attempt + 1,
                    'max_retries': self.max_retries,
                    'error_type': type(e).__name__,
                    'messages_count': len(messages),
                    'has_tools': bool(tools),
                    'temperature': temperature,
                    'request_id': request_id,
                    'duration_ms': duration_ms
                }
                
                # Log failed response
                self.logger.log_openai_response(
                    session_id=session_id,
                    request_id=request_id,
                    response_content=None,
                    usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                    cost_estimate=0.0,
                    duration_ms=duration_ms,
                    attempt=attempt + 1,
                    error=str(e)
                )
                
                # Check for specific error types and handle accordingly
                error_message = str(e).lower()
                
                # Handle geographic restrictions (403 errors)
                if 'unsupported_country_region_territory' in error_message or '403' in error_message:
                    self.logger.log_error(f"OpenAI geographic restriction detected (attempt {attempt + 1}/{self.max_retries}): {str(e)}", exception=e, extra_data=error_context)
                    
                    raise Exception(f"OpenAI API blocked due to geographic restrictions after {self.max_retries} attempts")
                
                # Log different types of OpenAI errors differently
                elif 'rate_limit' in error_message:
                    self.logger.log_error(f"OpenAI rate limit exceeded (attempt {attempt + 1}/{self.max_retries})", exception=e, extra_data=error_context)
                    # Longer wait for rate limits
                    if attempt < self.max_retries - 1:
                        wait_time = (2 ** (attempt + 2)) + random.uniform(2, 5)  # 6-9s, 10-13s, 18-21s
                        await asyncio.sleep(wait_time)
                        continue
                elif 'timeout' in error_message:
                    self.logger.log_error(f"OpenAI request timeout (attempt {attempt + 1}/{self.max_retries})", exception=e, extra_data=error_context)
                elif 'quota' in error_message:
                    self.logger.log_error(f"OpenAI quota exceeded (attempt {attempt + 1}/{self.max_retries})", exception=e, extra_data=error_context)
                elif 'connection' in error_message or 'network' in error_message:
                    self.logger.log_error(f"OpenAI connection error (attempt {attempt + 1}/{self.max_retries})", exception=e, extra_data=error_context)
                else:
                    self.logger.log_error(f"OpenAI API request failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}", exception=e, extra_data=error_context)
                
                if attempt == self.max_retries - 1:
                    raise e
                
                # Standard exponential backoff with jitter for other errors
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(wait_time)
        
        raise Exception(f"Failed to complete OpenAI request after {self.max_retries} attempts")
    
    def _calculate_cost(self, usage: Dict[str, int]) -> float:
        """Calculate estimated cost based on token usage"""
        if self.model not in self.token_costs:
            return 0.0
        
        costs = self.token_costs[self.model]
        input_cost = (usage['prompt_tokens'] / 1000) * costs['input']
        output_cost = (usage['completion_tokens'] / 1000) * costs['output']
        
        return input_cost + output_cost
    
    async def chat_completion(self, messages: List[Dict[str, str]], 
                            session_id: str,
                            temperature: float = 0.7,
                            seed: Optional[int] = None,
                            tools: Optional[List[Dict[str, Any]]] = None) -> Tuple[Any, Dict[str, int]]:
        """Standard chat completion"""
        return await self._make_request_with_retry(
            messages=messages,
            session_id=session_id,
            temperature=temperature,
            seed=seed,
            tools=tools
        )
    
    async def json_completion(self, messages: List[Dict[str, str]], 
                            session_id: str,
                            temperature: float = 0.3,
                            seed: Optional[int] = None) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """Chat completion with JSON response format"""
        content, usage = await self._make_request_with_retry(
            messages=messages,
            session_id=session_id,
            temperature=temperature,
            seed=seed,
            response_format={"type": "json_object"}
        )
        
        try:
            json_response = json.loads(content)
            return json_response, usage
        except json.JSONDecodeError as e:
            self.logger.log_error(
                f"Failed to parse JSON response from OpenAI",
                exception=e,
                extra_data={'session_id': session_id, 'content': content}
            )
            # Return fallback response
            return {"error": "invalid_json", "content": content}, usage

