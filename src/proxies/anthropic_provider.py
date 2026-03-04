"""Anthropic Messages API Provider Wrapper.

This module provides conversion between Anthropic Messages API format and OpenAI
chat completions format, enabling Anthropic-compatible requests to be proxied
through OpenAI-compatible backends.

Architecture:
    Anthropic Request → AnthropicProvider → OpenAI Request → Backend
    Backend Response → OpenAI Format → AnthropicProvider → Anthropic Response

Supported Features:
    - Text messages
    - System prompts
    - Image blocks (base64 and URL)
    - Tool use and tool results
    - Streaming responses with SSE events
    - Model routing with provider prefixes
"""

from __future__ import annotations

import json
from typing import Any

from fastapi.responses import JSONResponse, StreamingResponse
from tools.serialization import to_dict


class AnthropicProvider:
    """Anthropic Messages API format converter.
    
    Converts between Anthropic Messages API format and OpenAI chat completions
    format to enable Anthropic-compatible clients to use OpenAI-compatible backends.
    """

    # Known parameters accepted by the Anthropic Messages API.
    ANTHROPIC_MESSAGES_KNOWN_PARAMS: set[str] = {
        "model",
        "messages",
        "max_tokens",
        "system",
        "temperature",
        "top_p",
        "top_k",
        "stop_sequences",
        "stream",
        "metadata",
        "tools",
        "tool_choice",
    }

    # Maps OpenAI finish_reason values to Anthropic stop_reason values.
    FINISH_REASON_MAP: dict[str, str] = {
        "stop": "end_turn",
        "length": "max_tokens",
        "tool_calls": "tool_use",
    }

    @staticmethod
    def anthropic_to_openai_request(body: dict[str, Any], model_name: str) -> dict[str, Any]:
        """Convert Anthropic Messages API request to OpenAI chat completions format.

        Args:
            body: Raw Anthropic request body.
            model_name: Provider-stripped model name (e.g. "gpt-4o").

        Returns:
            Dict suitable for passing to the AsyncOpenAI client.
        """
        oai: dict[str, Any] = {"model": model_name}
        messages: list[dict[str, Any]] = []

        # Convert system prompt
        system: Any = body.get("system")
        if system:
            if isinstance(system, str):
                system_text: str = system
            else:
                # System can be array of text blocks
                system_text = " ".join(
                    str(blk.get("text", ""))
                    for blk in system
                    if isinstance(blk, dict) and blk.get("type") == "text"
                )
            messages.append({"role": "system", "content": system_text})

        # Convert messages
        raw_messages: list[Any] = body.get("messages") or []
        for msg in raw_messages:
            msg_dict_raw: dict[str, Any] = msg if isinstance(msg, dict) else {}
            role: str = str(msg_dict_raw.get("role") or "")
            content: Any = msg_dict_raw.get("content")

            # Simple text content
            if isinstance(content, str):
                messages.append({"role": role, "content": content})
                continue

            # Non-list content
            if not isinstance(content, list):
                messages.append({"role": role, "content": content})
                continue

            # Complex content with multiple blocks
            oai_content: list[dict[str, Any]] = []
            tool_calls: list[dict[str, Any]] = []
            tool_result_messages: list[dict[str, Any]] = []

            for block in content:
                block_d: dict[str, Any] = block if isinstance(block, dict) else {}
                block_type: Any = block_d.get("type")

                if block_type == "text":
                    oai_content.append({"type": "text", "text": str(block_d.get("text") or "")})

                elif block_type == "image":
                    source: dict[str, Any] = block_d.get("source") if isinstance(block_d.get("source"), dict) else {}
                    src_type: Any = source.get("type")
                    if src_type == "base64":
                        media_type: str = str(source.get("media_type") or "image/jpeg")
                        data: str = str(source.get("data") or "")
                        url: str = f"data:{media_type};base64,{data}"
                    elif src_type == "url":
                        url = str(source.get("url") or "")
                    else:
                        url = ""
                    oai_content.append({"type": "image_url", "image_url": {"url": url}})

                elif block_type == "tool_use":
                    tool_calls.append({
                        "id": str(block_d.get("id") or ""),
                        "type": "function",
                        "function": {
                            "name": str(block_d.get("name") or ""),
                            "arguments": json.dumps(block_d.get("input") or {}),
                        },
                    })

                elif block_type == "tool_result":
                    raw_result: Any = block_d.get("content") or ""
                    if isinstance(raw_result, list):
                        result_content: str = " ".join(
                            str(b.get("text") or "")
                            for b in raw_result
                            if isinstance(b, dict) and b.get("type") == "text"
                        )
                    else:
                        result_content = str(raw_result)
                    tool_result_messages.append({
                        "role": "tool",
                        "tool_call_id": str(block_d.get("tool_use_id") or ""),
                        "content": result_content,
                    })

            # Append messages based on what was parsed
            if tool_result_messages:
                messages.extend(tool_result_messages)
            elif tool_calls:
                assembled: dict[str, Any] = {"role": role}
                if oai_content:
                    assembled["content"] = oai_content
                assembled["tool_calls"] = tool_calls
                messages.append(assembled)
            elif len(oai_content) == 1 and oai_content[0].get("type") == "text":
                messages.append({"role": role, "content": str(oai_content[0].get("text") or "")})
            else:
                messages.append({"role": role, "content": oai_content})

        oai["messages"] = messages

        # Map standard parameters
        for param in ("max_tokens", "temperature", "top_p", "stream"):
            if param in body:
                oai[param] = body[param]

        # Map stop_sequences to stop
        if "stop_sequences" in body:
            oai["stop"] = body["stop_sequences"]

        # Extract user_id from metadata
        metadata: Any = body.get("metadata")
        if isinstance(metadata, dict) and "user_id" in metadata:
            oai["user"] = metadata["user_id"]

        # Map top_k (may not be supported by all backends)
        if "top_k" in body:
            oai["top_k"] = body["top_k"]

        # Convert tools
        raw_tools: Any = body.get("tools")
        if raw_tools:
            tools_list: list[Any] = raw_tools if isinstance(raw_tools, list) else []
            oai["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": str(t.get("name") or "") if isinstance(t, dict) else "",
                        "description": str(t.get("description") or "") if isinstance(t, dict) else "",
                        "parameters": t.get("input_schema") or {} if isinstance(t, dict) else {},
                    },
                }
                for t in tools_list
            ]

        # Convert tool_choice
        raw_tool_choice: Any = body.get("tool_choice")
        if raw_tool_choice and isinstance(raw_tool_choice, dict):
            tool_choice: dict[str, Any] = raw_tool_choice
            tc_type: Any = tool_choice.get("type")
            if tc_type == "auto":
                oai["tool_choice"] = "auto"
            elif tc_type == "any":
                oai["tool_choice"] = "required"
            elif tc_type == "tool":
                oai["tool_choice"] = {
                    "type": "function",
                    "function": {"name": str(tool_choice.get("name") or "")},
                }

        return oai

    @staticmethod
    def openai_to_anthropic_response(response: Any, model_id: str) -> dict[str, Any]:
        """Convert OpenAI chat completion response to Anthropic Messages API format.

        Args:
            response: OpenAI response object or dict.
            model_id: Original model ID from the Anthropic request (e.g. "openai_gpt-4o").

        Returns:
            Dict conforming to the Anthropic Messages API response schema.
        """
        resp_dict: dict[str, Any] = to_dict(response)

        choices: list[Any] = resp_dict.get("choices") or []
        choice: dict[str, Any] = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}

        message: dict[str, Any] = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        content: list[dict[str, Any]] = []

        # Convert text content
        text: Any = message.get("content")
        if text:
            content.append({"type": "text", "text": str(text)})

        # Convert tool calls
        raw_tool_calls: Any = message.get("tool_calls")
        for tc in (raw_tool_calls if isinstance(raw_tool_calls, list) else []):
            tc_d: dict[str, Any] = tc if isinstance(tc, dict) else {}
            fn: dict[str, Any] = tc_d.get("function") if isinstance(tc_d.get("function"), dict) else {}
            try:
                input_data: Any = json.loads(str(fn.get("arguments") or "{}"))
            except (json.JSONDecodeError, ValueError):
                input_data = {}
            content.append({
                "type": "tool_use",
                "id": str(tc_d.get("id") or ""),
                "name": str(fn.get("name") or ""),
                "input": input_data,
            })

        # Map finish_reason to stop_reason
        finish_reason: str = str(choice.get("finish_reason") or "stop")
        stop_reason: str = AnthropicProvider.FINISH_REASON_MAP.get(finish_reason, "end_turn")

        # Convert usage
        usage_raw: dict[str, Any] = resp_dict.get("usage") if isinstance(resp_dict.get("usage"), dict) else {}
        usage = {
            "input_tokens": int(usage_raw.get("prompt_tokens") or 0),
            "output_tokens": int(usage_raw.get("completion_tokens") or 0),
        }

        return {
            "id": str(resp_dict.get("id") or ""),
            "type": "message",
            "role": "assistant",
            "content": content,
            "model": model_id,
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": usage,
        }

    @staticmethod
    async def format_anthropic_streaming_response(stream: Any, model_id: str) -> StreamingResponse:
        """Wrap OpenAI SSE stream as Anthropic-format SSE events.

        Args:
            stream: Async iterable of OpenAI completion chunks.
            model_id: Original model ID from the Anthropic request.

        Returns:
            StreamingResponse emitting Anthropic SSE events.
        """
        async def generator():
            msg_id: str = "msg_stream"
            output_tokens: int = 0
            stop_reason: str = "end_turn"
            started: bool = False

            async for chunk in stream:
                chunk_dict: dict[str, Any] = to_dict(chunk)

                if not started:
                    msg_id = str(chunk_dict.get("id") or "msg_stream")
                    # Emit message_start event
                    yield (
                        f"event: message_start\n"
                        f"data: {json.dumps({'type': 'message_start', 'message': {'id': msg_id, 'type': 'message', 'role': 'assistant', 'content': [], 'model': model_id, 'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 0, 'output_tokens': 0}}})}\n\n"
                    )
                    # Emit content_block_start event
                    yield (
                        f"event: content_block_start\n"
                        f"data: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"
                    )
                    # Emit ping event
                    yield f"event: ping\ndata: {json.dumps({'type': 'ping'})}\n\n"
                    started = True

                raw_choices: Any = chunk_dict.get("choices")
                choices: list[Any] = raw_choices if isinstance(raw_choices, list) else []
                if choices:
                    choice: dict[str, Any] = choices[0] if isinstance(choices[0], dict) else {}
                    delta: dict[str, Any] = choice.get("delta") if isinstance(choice.get("delta"), dict) else {}
                    text: Any = delta.get("content")
                    if text:
                        # Emit content_block_delta event
                        yield (
                            f"event: content_block_delta\n"
                            f"data: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': str(text)}})}\n\n"
                        )
                    raw_finish: Any = choice.get("finish_reason")
                    if raw_finish:
                        stop_reason = AnthropicProvider.FINISH_REASON_MAP.get(str(raw_finish), "end_turn")

                raw_usage: Any = chunk_dict.get("usage")
                if isinstance(raw_usage, dict):
                    usage: dict[str, Any] = raw_usage
                    output_tokens = int(usage.get("completion_tokens") or output_tokens)

            # Emit content_block_stop event
            yield (
                f"event: content_block_stop\n"
                f"data: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
            )
            # Emit message_delta event
            yield (
                f"event: message_delta\n"
                f"data: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': stop_reason, 'stop_sequence': None}, 'usage': {'output_tokens': output_tokens}})}\n\n"
            )
            # Emit message_stop event
            yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"

        return StreamingResponse(generator(), media_type="text/event-stream")
