# Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
# Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
# SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
import asyncio
import json
import os
import traceback
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

import psutil
from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, HTTPException, Request
from loguru import logger
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.web.async_slack_response import AsyncSlackResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..integrations.slack.socket_client import get_socket_mode_client
from ..models.run_model import RunModel, RunStatus
from ..models.slack_agent_model import SlackAgentModel
from ..models.task_model import TaskStatus
from ..models.workflow_model import WorkflowModel
from ..schemas.run_schemas import StartRunRequestSchema
from ..schemas.slack_schemas import (
    AgentTokenRequest,
    AgentTokenResponse,
    SlackAgentCreate,
    SlackAgentResponse,
    SlackAgentUpdate,
    SlackMessage,
    SlackMessageResponse,
    SlackSocketModeResponse,
    SlackTriggerConfig,
    WorkflowAssociation,
    WorkflowTriggerRequest,
    WorkflowTriggerResult,
    WorkflowTriggersResponse,
)
from . import key_management
from .secure_token_store import get_token_store
from .workflow_run import run_workflow_non_blocking

router = APIRouter()

# API Endpoints
SLACK_API_URL = "https://slack.com/api"
SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"

# Request timeout (in seconds)
REQUEST_TIMEOUT = 10

# Initialize the socket mode client and set up the workflow trigger callback
socket_mode_client = get_socket_mode_client()

# Define a type variable for the response objects
T = TypeVar("T")

# Add these type annotations to better handle slack_sdk method calls


def _validate_agent_socket_mode(
    db: Session, agent_id: int, say_callback: Optional[Callable[..., Any]] = None
) -> bool:
    """Validate if an agent should be processing socket mode events.

    Args:
        db: Database session
        agent_id: Agent ID to validate
        say_callback: Optional callback to send message if agent is disabled

    Returns:
        bool: True if agent should process events, False otherwise

    """
    agent = db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()

    if agent is None or not bool(agent.socket_mode_enabled):
        logger.warning(f"Rejecting event for agent {agent_id} - socket_mode_enabled=False")

        # Send response to avoid hanging the client
        if say_callback:
            try:
                say_callback(text="This Slack integration is currently disabled.")
            except Exception:
                pass
        return False

    return True


# Callback function for socket mode events to trigger workflows
async def handle_socket_mode_event(
    trigger_request: WorkflowTriggerRequest,
    agent_id: int,
    say: Callable[..., Any],
    client: Optional[WebClient] = None,
):
    """Handle a socket mode event by triggering the associated workflow"""
    logger.info(f"Handling socket mode event for agent {agent_id}")

    # This function can be called from a thread or directly, so we need to handle both cases
    # Get a database session
    db = next(get_db())

    try:
        # First, explicitly check if this agent should actually be processing events
        if not _validate_agent_socket_mode(db, agent_id, say):
            return

        agent = await _get_active_agent(db, agent_id)
        if not agent:
            return

        if await _should_trigger_workflow(agent, trigger_request):
            await _trigger_workflow(db, agent, trigger_request, say, client)

    except Exception as e:
        logger.error(f"Error in handle_socket_mode_event: {e}")
        logger.error(f"Error details: {traceback.format_exc()}")
    finally:
        db.close()


# Create a synchronous version of the handler that can be called from threads
def handle_socket_mode_event_sync(
    trigger_request: WorkflowTriggerRequest,
    agent_id: int,
    say: Callable[..., Any],
    client: Optional[WebClient] = None,
):
    """Synchronous wrapper for handle_socket_mode_event to be used in threaded contexts."""
    # Return the coroutine object without awaiting it
    # The socket client will handle awaiting it appropriately
    return handle_socket_mode_event(trigger_request, agent_id, say, client)


async def _get_active_agent(db: Session, agent_id: int) -> Optional[SlackAgentModel]:
    """Get an active agent with workflow configured."""
    agent = (
        db.query(SlackAgentModel)
        .filter(
            SlackAgentModel.id == agent_id,
            SlackAgentModel.is_active.is_(True),
            SlackAgentModel.trigger_enabled.is_(True),
            SlackAgentModel.workflow_id.isnot(None),
        )
        .first()
    )

    if not agent:
        logger.warning(f"Agent {agent_id} not found, not active, or has no workflow")
    return agent


# Handle the item typing issues in the keywords list
async def _should_trigger_workflow(
    agent: SlackAgentModel, trigger_request: WorkflowTriggerRequest
) -> bool:
    """Determine if a Slack message should trigger a workflow."""
    # Only proceed if triggering is enabled for this agent
    try:
        # Use explicit conversion for all SQLAlchemy Column boolean fields
        trigger_enabled = bool(agent.trigger_enabled)
        if not trigger_enabled:
            return False

        should_trigger = False

        # Check mention trigger - convert SQLAlchemy Column to bool for comparison
        trigger_on_mention = bool(agent.trigger_on_mention)
        if trigger_on_mention and trigger_request.event_type == "app_mention":
            should_trigger = True
        # Check direct message trigger
        elif (
            bool(agent.trigger_on_direct_message)
            and trigger_request.event_type == "message"
            and trigger_request.event_data.get("channel_type") == "im"
        ):
            should_trigger = True
        # Check channel message trigger
        elif (
            bool(agent.trigger_on_channel_message)
            and trigger_request.event_type == "message"
            and trigger_request.event_data.get("channel_type") != "im"
        ):
            # For channel messages, we need to check for keywords
            keywords = getattr(agent, "trigger_keywords", []) or []
            if isinstance(keywords, list):
                str_keywords: List[str] = []
                for item in cast(List[Union[str, None]], keywords):
                    if item is not None:
                        str_keywords.append(str(item))
                if str_keywords:
                    message_text = trigger_request.text.lower()
                    for keyword in str_keywords:
                        if keyword.lower() in message_text:
                            return True
                    return False
            else:
                return False

        return should_trigger
    except Exception as e:
        logger.error(f"Error in _should_trigger_workflow: {str(e)}")
        return False


async def _trigger_workflow(
    db: Session,
    agent: SlackAgentModel,
    trigger_request: WorkflowTriggerRequest,
    say: Callable[..., Any],
    client: Optional[WebClient] = None,
):
    """Trigger the workflow and handle the response"""
    try:
        # Prepare the run input
        run_input = {
            "message": trigger_request.text,
            "channel_id": trigger_request.channel_id,
            "user_id": trigger_request.user_id,
            "event_type": trigger_request.event_type,
            "event_data": trigger_request.event_data,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Start the workflow run
        background_tasks = BackgroundTasks()
        run = await start_workflow_run(
            db=db,
            workflow_id=str(getattr(agent, "workflow_id", "") or ""),
            run_input=run_input,
            background_tasks=background_tasks,
        )

        # Let the user know we're processing their request
        # Use client if available, otherwise fall back to say function
        if client and trigger_request.channel_id:
            try:
                client.chat_postMessage(  # type: ignore
                    channel=trigger_request.channel_id,
                    text=f"Processing your request... (Run ID: {run.id})",
                )
            except Exception as e:
                logger.error(f"Error using client to respond: {e}")
                say(text=f"Processing your request... (Run ID: {run.id})")
        else:
            say(text=f"Processing your request... (Run ID: {run.id})")

        logger.info(f"Started workflow run {run.id} for agent {agent.id}")

        # Manually execute background tasks since we're not in a FastAPI endpoint
        logger.info(f"Manually executing background tasks for workflow run {run.id}")
        for task in background_tasks.tasks:
            logger.info(f"Executing task: {str(task)}")
            await task()
        logger.info(f"Background tasks execution completed for workflow run {run.id}")

        # Wait for workflow to complete and return results to Slack
        await _send_workflow_results_to_slack(run.id, trigger_request.channel_id, client, say)

    except Exception as e:
        logger.error(f"Error triggering workflow for agent {agent.id}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        say(text=f"Sorry, I encountered an error: {str(e)}")


# Handle chat_postMessage and auth_test type issues by using proper type annotations
async def _send_workflow_results_to_slack(
    run_id: str,
    channel_id: str,
    client: Optional[WebClient] = None,
    say: Optional[Callable[..., Any]] = None,
    db: Optional[Session] = None,
):
    """Get workflow results and send them back to Slack."""
    own_db_session = db is None

    try:
        # Create a new database session if one wasn't provided
        if own_db_session:
            db = next(get_db())

        # Wait for the workflow to complete (poll status)
        # Poll for up to 2 minutes (24 attempts, 5 seconds apart)
        max_attempts = 24
        attempts = 0
        run_complete = False
        run = None

        while attempts < max_attempts and not run_complete:
            attempts += 1
            # Get the run model from database
            run = db.query(RunModel).filter(RunModel.id == run_id).first()

            if not run:
                logger.error(f"Run {run_id} not found in database")
                break

            # Check if the run has completed or failed
            if run.status in [
                RunStatus.COMPLETED,
                RunStatus.FAILED,
                RunStatus.PAUSED,
                RunStatus.CANCELED,
            ]:
                run_complete = True
                break

            # Wait before polling again
            await asyncio.sleep(5)

        # Prepare the message to send back
        if not run:
            message = f"⚠️ Could not find workflow run {run_id}"
        elif not run_complete:
            message = f"⏱️ Workflow run {run_id} is still in progress (status: {run.status})"
        elif run.status == RunStatus.COMPLETED:
            # Format the output message
            if run.outputs:
                # Find the output node
                output_content: Optional[str] = None
                # Typically outputs are stored with node IDs as keys
                for _, output in run.outputs.items():
                    # Look for output node or content that has relevant output data
                    if isinstance(output, dict) and (
                        "result" in output or "content" in output or "text" in output
                    ):
                        output_dict = cast(Dict[str, Any], output)
                        output_content = (
                            output_dict.get("result")
                            or output_dict.get("content")
                            or output_dict.get("text")
                        )
                        break

                if output_content:
                    message = (
                        f"✅ Workflow completed successfully!\n\n*Output:*\n```{output_content}```"
                    )
                else:
                    # If we can't find a specific output format, just return the full output as JSON
                    message = f"✅ Workflow completed successfully!\n\n*Output:*\n```{json.dumps(run.outputs, indent=2)}```"
            else:
                message = "✅ Workflow completed successfully! (No output data available)"
        elif run.status == RunStatus.FAILED:
            message = "❌ Workflow run failed"
            # Look for error messages in tasks
            error_messages: List[str] = []
            if run.tasks:
                for task in run.tasks:
                    if task.status == TaskStatus.FAILED and task.error:
                        error_messages.append(f"- Task {task.node_id}: {task.error}")

            if error_messages:
                message += "\n\n*Errors:*\n" + "\n".join(error_messages)
        else:
            message = f"⚠️ Workflow run {run_id} ended with status: {run.status}"

        # Send the message back to Slack
        if client and channel_id:
            try:
                logger.info(f"Sending workflow result to Slack channel {channel_id}")
                client.chat_postMessage(channel=channel_id, text=message)  # type: ignore
                logger.info("Successfully sent workflow result to Slack")
            except Exception as e:
                logger.error(f"Error sending workflow results to Slack: {e}")
                if say:
                    say(text=message)
        elif say:
            logger.info("Using say function to send workflow result")
            say(text=message)
        else:
            logger.error("Cannot send workflow results: No Slack client or say function available")

    except Exception as e:
        logger.error(f"Error sending workflow results to Slack: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        # Try to send error message
        error_msg = f"Error retrieving workflow results: {str(e)}"
        if client and channel_id:
            try:
                client.chat_postMessage(channel=channel_id, text=error_msg)  # type: ignore
            except Exception:
                if say:
                    say(text=error_msg)
        elif say:
            say(text=error_msg)
    finally:
        # Clean up if we created our own session
        if own_db_session and db:
            db.close()


# Set the callback for the socket mode client - use the sync version
socket_mode_client.set_workflow_trigger_callback(handle_socket_mode_event_sync)  # type: ignore


@router.get("/agents", response_model=List[SlackAgentResponse])
async def get_agents(db: Session = Depends(get_db)) -> List[SlackAgentResponse]:
    """Get all configured Slack agents."""
    agents = db.query(SlackAgentModel).all()
    agent_responses: List[SlackAgentResponse] = []

    for agent in agents:
        # Convert the agent to a SlackAgentResponse with proper type handling
        agent_response = _agent_to_response_model(agent)
        agent_responses.append(agent_response)

    return agent_responses


def _get_nullable_str(value: Any) -> Optional[str]:
    """Helper to safely convert nullable SQLAlchemy column to string."""
    return str(value) if value is not None else None


# Helper function to convert a SlackAgentModel to a SlackAgentResponse
def _agent_to_response_model(agent: SlackAgentModel) -> SlackAgentResponse:
    """Convert a SlackAgentModel to a SlackAgentResponse with proper type handling."""
    try:
        agent_id = int(str(agent.id))
    except (TypeError, ValueError):
        agent_id = 0

    # Build dictionary with careful conversion for SQLAlchemy types
    agent_dict = {
        "id": agent_id,
        "name": str(agent.name),
        "slack_team_id": _get_nullable_str(agent.slack_team_id),
        "slack_team_name": _get_nullable_str(agent.slack_team_name),
        "slack_channel_id": _get_nullable_str(agent.slack_channel_id),
        "slack_channel_name": _get_nullable_str(agent.slack_channel_name),
        "is_active": bool(agent.is_active),
        "workflow_id": _get_nullable_str(agent.workflow_id),
        "trigger_on_mention": bool(agent.trigger_on_mention),
        "trigger_on_direct_message": bool(agent.trigger_on_direct_message),
        "trigger_on_channel_message": bool(agent.trigger_on_channel_message),
        "trigger_keywords": [str(k) for k in getattr(agent, "trigger_keywords", []) or []],
        "trigger_enabled": bool(agent.trigger_enabled),
        "has_bot_token": bool(agent.has_bot_token),
        "has_user_token": bool(agent.has_user_token),
        "has_app_token": bool(agent.has_app_token),
        "last_token_update": _get_nullable_str(agent.last_token_update),
        "spur_type": str(getattr(agent, "spur_type", "workflow") or "workflow"),
        "created_at": str(getattr(agent, "created_at", "") or ""),
    }
    return SlackAgentResponse.model_validate(agent_dict)


@router.post("/agents", response_model=SlackAgentResponse)
async def create_agent(agent_create: SlackAgentCreate, db: Session = Depends(get_db)):
    """Create a new Slack agent configuration."""
    # Ensure workflow_id is provided
    if not agent_create.workflow_id:
        raise HTTPException(
            status_code=400,
            detail="workflow_id is required - every agent must be associated with a workflow",
        )

    # Create a new agent from the agent_create fields
    new_agent = SlackAgentModel(
        name=agent_create.name,
        slack_team_id=agent_create.slack_team_id,
        slack_team_name=agent_create.slack_team_name,
        slack_channel_id=agent_create.slack_channel_id,
        slack_channel_name=agent_create.slack_channel_name,
        is_active=bool(agent_create.is_active),
        workflow_id=agent_create.workflow_id,
        trigger_on_mention=bool(agent_create.trigger_on_mention),
        trigger_on_direct_message=bool(agent_create.trigger_on_direct_message),
        trigger_on_channel_message=bool(agent_create.trigger_on_channel_message),
        trigger_keywords=agent_create.trigger_keywords,
        trigger_enabled=bool(agent_create.trigger_enabled),
        has_bot_token=bool(agent_create.has_bot_token),
        has_user_token=bool(agent_create.has_user_token),
        has_app_token=bool(agent_create.has_app_token),
        last_token_update=agent_create.last_token_update,
        spur_type=agent_create.spur_type or "workflow",
    )

    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)

    # Convert the agent to a Pydantic model
    return _agent_to_response_model(new_agent)


@router.get("/agents/{agent_id}", response_model=SlackAgentResponse)
async def get_agent(agent_id: int, db: Session = Depends(get_db)):
    """Get a Slack agent configuration."""
    agent = db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Convert the agent to a Pydantic model
    return _agent_to_response_model(agent)


@router.post("/agents/{agent_id}/send-message", response_model=SlackMessageResponse)
async def send_agent_message(agent_id: int, message: SlackMessage, db: Session = Depends(get_db)):
    """Send a message to a channel using the Slack agent."""
    agent = db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Create a client using the agent's token
    token = None

    # If agent has a bot token, retrieve it
    has_bot_token = bool(agent.has_bot_token)
    if has_bot_token:
        logger.info(f"Retrieving bot token for agent {agent_id}")
        token_store = get_token_store()
        token = token_store.get_token(agent_id, "bot_token")

    if not token:
        raise HTTPException(status_code=400, detail="This agent has no bot token configured")

    # Send the message to Slack
    try:
        client = WebClient(token=token)
        logger.info(f"Sending message to channel '{message.channel}'")

        # Call Slack API - ignore type issues with chat_postMessage
        slack_response = client.chat_postMessage(  # type: ignore
            channel=message.channel,
            text=message.text,
        )

        # Extract data from the response
        response_data = {
            "ts": slack_response.get("ts", ""),
            "channel": slack_response.get("channel", ""),
            "message": "Message sent successfully",
            "success": True,
        }

        logger.info(f"Message sent successfully: {slack_response.get('ok', False)}")
        return response_data
    except SlackApiError as e:
        logger.error(f"Error sending message to Slack: {str(e)}")
        # If there was an error, raise an HTTPException
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Error sending message to Slack: {str(e)}",
                "success": False,
            },
        ) from e


@router.post("/send-message", response_model=SlackMessageResponse)
async def send_message(
    channel: str, text: str, agent_id: Optional[int] = None, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Send a message to a Slack channel."""
    logger.info(f"Attempting to send message to channel '{channel}' with agent_id: {agent_id}")

    # Initialize WebClient with the bot token
    token = None

    # If agent_id is provided, try to get the agent-specific token
    if agent_id is not None:
        # Try to get the agent
        logger.info(f"Searching for agent with ID: {agent_id}")
        agent = db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()

        if agent:
            has_bot_token = bool(agent.has_bot_token)
            logger.info(f"Found agent '{agent.name}' with has_bot_token={has_bot_token}")

            # If agent has a bot token, retrieve it
            if has_bot_token:
                logger.info(f"Retrieving bot token for agent {agent_id}")
                token_store = get_token_store()
                token = token_store.get_token(agent_id, "bot_token")
                logger.info(f"Token retrieved: {'Yes' if token else 'No'}")
        else:
            logger.error(f"Agent with ID {agent_id} not found")

    # If no agent-specific token, try to use the default token from environment
    if not token:
        logger.info("No agent-specific token found, using environment variables")
        token = os.getenv("SLACK_BOT_TOKEN")

    if not token:
        logger.error("No Slack bot token configured")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "No Slack bot token configured",
                "success": False,
            },
        )

    try:
        client = WebClient(token=token)
        logger.info(f"Sending message to channel '{channel}'")

        # Call Slack API - ignore type issues with chat_postMessage
        slack_response = client.chat_postMessage(  # type: ignore
            channel=channel,
            text=text,
        )

        # Extract data from the response
        response_data = {
            "ts": slack_response.get("ts", ""),
            "channel": slack_response.get("channel", ""),
            "message": "Message sent successfully",
            "success": True,
        }

        logger.info(f"Message sent successfully: {slack_response.get('ok', False)}")
        return response_data
    except SlackApiError as e:
        logger.error(f"Error sending message to Slack: {str(e)}")
        # If there was an error, raise an HTTPException
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Error sending message to Slack: {str(e)}",
                "success": False,
            },
        ) from e


@router.post("/test-message", response_model=SlackMessageResponse)
async def test_message(
    channel: str,
    text: str = "Hello from Faraflow! This is a test message.",
    agent_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Test sending a message to a Slack channel."""
    try:
        # Attempt to send the test message using the Slack client
        response = await send_message(channel=channel, text=text, agent_id=agent_id, db=db)
        return response
    except Exception as e:
        logger.error(f"Error sending test message: {e}")
        return {"success": False, "message": f"Error sending test message: {e}"}


@router.put("/agents/{agent_id}/workflow", response_model=SlackAgentResponse)
async def associate_workflow(
    agent_id: int, association: WorkflowAssociation, db: Session = Depends(get_db)
):
    """Associate a workflow with a Slack agent."""
    agent = db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.set_field("workflow_id", association.workflow_id)
    db.commit()
    db.refresh(agent)

    # Convert the agent to a Pydantic model
    return _agent_to_response_model(agent)


@router.put("/agents/{agent_id}/trigger-config", response_model=SlackAgentResponse)
async def update_trigger_config(
    agent_id: int, config: SlackTriggerConfig, db: Session = Depends(get_db)
):
    """Update the trigger configuration for a Slack agent."""
    agent = db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update agent using set_field for type safety
    agent.set_field("trigger_on_mention", config.trigger_on_mention)
    agent.set_field("trigger_on_direct_message", config.trigger_on_direct_message)
    agent.set_field("trigger_on_channel_message", config.trigger_on_channel_message)
    agent.set_field("trigger_keywords", config.trigger_keywords)
    agent.set_field("trigger_enabled", config.trigger_enabled)

    db.commit()
    db.refresh(agent)

    # Convert the agent to a Pydantic model
    return _agent_to_response_model(agent)


@router.put("/agents/{agent_id}", response_model=SlackAgentResponse)
async def update_agent(
    agent_id: int, agent_update: SlackAgentUpdate, db: Session = Depends(get_db)
):
    """Update a Slack agent configuration"""
    agent = db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update agent from the agent_update fields
    update_data = agent_update.model_dump(exclude_unset=True)

    # Ensure boolean fields are properly converted
    for field in update_data:
        setattr(agent, field, update_data[field])

    db.commit()
    db.refresh(agent)

    # Convert the agent to a Pydantic model
    return _agent_to_response_model(agent)


# Helper function to start a workflow run using the existing workflow execution system
async def start_workflow_run(
    db: Session, workflow_id: str, run_input: Dict[str, Any], background_tasks: BackgroundTasks
) -> RunModel:
    """Start a workflow run with the given input data using the standard workflow execution system."""
    # First, check if the workflow exists
    workflow = db.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Get the input node ID from the workflow
    workflow_definition = workflow.definition
    input_node = next(
        (node for node in workflow_definition["nodes"] if node["node_type"] == "InputNode"), None
    )

    if not input_node:
        raise HTTPException(status_code=400, detail="Workflow has no input node")

    # Create the request payload with the input data
    initial_inputs = {input_node["id"]: run_input}
    start_run_request = StartRunRequestSchema(initial_inputs=initial_inputs)

    # Use the standard workflow execution system to run the workflow
    run_response = await run_workflow_non_blocking(
        workflow_id=workflow_id,
        start_run_request=start_run_request,
        background_tasks=background_tasks,
        db=db,
        run_type="slack_triggered",
    )

    # Extract the RunModel from the response
    return db.query(RunModel).filter(RunModel.id == run_response.id).first()


@router.post("/trigger-workflow", response_model=WorkflowTriggersResponse)
async def trigger_workflow(
    request: WorkflowTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger workflows based on a Slack event."""
    result = WorkflowTriggersResponse(triggered_workflows=[])

    # Find agents that match the team ID
    agents = (
        db.query(SlackAgentModel)
        .filter(
            SlackAgentModel.slack_team_id == request.team_id,
            SlackAgentModel.is_active.is_(True),
            SlackAgentModel.trigger_enabled.is_(True),
            SlackAgentModel.workflow_id.isnot(None),
        )
        .all()
    )

    if not agents:
        return result

    # Process each agent to see if it should be triggered
    for agent in agents:
        # Cast SQLAlchemy Column types to Python types for the constructor
        agent_id = agent.get_id()
        workflow_id = agent.get_workflow_id()

        trigger_result = WorkflowTriggerResult(
            agent_id=agent_id,
            workflow_id=workflow_id,
            status="skipped",
        )

        # Check if this agent should be triggered based on the event type
        should_trigger = False

        # Check mention trigger - convert SQLAlchemy Column to bool for comparison
        if bool(agent.trigger_on_mention) and request.event_type == "app_mention":
            should_trigger = True

        # Check direct message trigger
        elif (
            bool(agent.trigger_on_direct_message)
            and request.event_type == "message"
            and request.event_data.get("channel_type") == "im"
        ):
            should_trigger = True

        # Check channel message trigger
        elif (
            bool(agent.trigger_on_channel_message)
            and request.event_type == "message"
            and request.event_data.get("channel_type") in ["channel", "group"]
        ):
            # If keywords are specified, check if any are in the message
            keywords = getattr(agent, "trigger_keywords", None)
            if keywords and isinstance(keywords, list):
                # Make sure keywords is a list of strings before using len
                str_keywords: List[str] = []
                for item in cast(List[Union[str, None]], keywords):
                    if item is not None:
                        str_keywords.append(str(item))
                if len(str_keywords) > 0:
                    message_text = request.text.lower()
                    for keyword in str_keywords:
                        if keyword.lower() in message_text:
                            should_trigger = True
                            break
            else:
                should_trigger = True

        if should_trigger:
            try:
                # Prepare the run input
                run_input = {
                    "message": request.text,
                    "channel_id": request.channel_id,
                    "user_id": request.user_id,
                    "event_type": request.event_type,
                    "event_data": request.event_data,
                    "timestamp": datetime.now(UTC).isoformat(),  # Use timezone-aware datetime
                }

                # Start the workflow run using the standard workflow execution system
                run = await start_workflow_run(
                    db=db,
                    workflow_id=str(getattr(agent, "workflow_id", "") or ""),
                    run_input=run_input,
                    background_tasks=background_tasks,
                )

                trigger_result.status = "triggered"
                trigger_result.run_id = run.id

            except Exception as e:
                trigger_result.status = "error"
                trigger_result.error = str(e)

        result.triggered_workflows.append(trigger_result)

    return result


@router.post("/events", status_code=200)
async def slack_events(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Handle Slack events from the Events API."""
    data = await request.json()

    # Handle Slack URL verification challenge
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}

    # Process other events
    event = data.get("event", {})
    event_type = event.get("type")

    if not event_type:
        return {"ok": True}

    # Extract relevant data
    team_id = data.get("team_id")
    user_id = event.get("user")
    channel_id = event.get("channel")
    text = event.get("text", "")

    # Skip bot messages to avoid loops
    if event.get("bot_id") or user_id == "USLACKBOT":
        return {"ok": True}

    # Create a trigger request
    trigger_request = WorkflowTriggerRequest(
        text=text,
        channel_id=channel_id,
        user_id=user_id,
        team_id=team_id,
        event_type=event_type,
        event_data=event,
    )

    # Process asynchronously to respond to Slack quickly
    background_tasks.add_task(trigger_workflow, trigger_request, background_tasks, db)

    return {"ok": True}


@router.post("/agents/{agent_id}/tokens/{token_type}", response_model=AgentTokenResponse)
async def set_agent_token(
    agent_id: int, token_type: str, token_request: AgentTokenRequest, db: Session = Depends(get_db)
):
    # Override token_request.token_type with the type from the URL
    agent = db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    token_store = get_token_store()
    token_store.store_token(agent_id, token_type, token_request.token)

    # Update agent token flag
    if token_type == "bot_token":
        agent.set_field("has_bot_token", True)

        # Try to get team information when setting a bot token
        try:
            client = AsyncWebClient(token=token_request.token)
            response: AsyncSlackResponse = await client.auth_test()  # type: ignore
            response_data: Dict[str, Any] = response.data if isinstance(response.data, dict) else {}  # type: ignore
            if response_data.get("ok"):
                team_id = str(response_data.get("team_id", ""))
                team_name = str(response_data.get("team", ""))
                if team_id:
                    agent.set_field("slack_team_id", team_id)
                    agent.set_field("slack_team_name", team_name)
                    logger.info(
                        f"Updated agent {agent_id} with team information: {team_name} ({team_id})"
                    )
        except Exception as e:
            logger.warning(f"Failed to retrieve team information: {str(e)}")
            # Don't fail the token setting if we can't get team info
            pass

    elif token_type == "user_token":
        agent.set_field("has_user_token", True)
    elif token_type == "app_token":
        agent.set_field("has_app_token", True)

    current_timestamp = datetime.now(UTC).isoformat()
    agent.set_field("last_token_update", current_timestamp)
    db.commit()
    db.refresh(agent)

    # Mask the token for the response
    masked_token = mask_token(token_request.token)
    return AgentTokenResponse(
        agent_id=agent_id,
        token_type=token_type,
        masked_token=masked_token,
        updated_at=current_timestamp,
    )


# Helper function to mask tokens for the API response
def mask_token(token: str) -> str:
    """Create a masked version of the token for display."""
    if len(token) <= 8:
        return "*" * len(token)
    return token[:4] + "*" * (len(token) - 8) + token[-4:]


@router.get("/agents/{agent_id}/tokens/{token_type}", response_model=AgentTokenResponse)
async def get_agent_token(agent_id: int, token_type: str, db: Session = Depends(get_db)):
    """Get a masked token for a Slack agent."""
    agent = db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    if token_type not in ["bot_token", "user_token", "app_token"]:
        raise HTTPException(status_code=400, detail="Invalid token type")

    token_store = get_token_store()

    # Get the token
    token = token_store.get_token(agent_id, token_type)
    if not token:
        raise HTTPException(status_code=404, detail=f"No {token_type} found for this agent")

    # Mask the token for the response
    masked_token = mask_token(token)

    # Get the last update timestamp - handle the value directly
    last_token_update = _get_nullable_str(agent.last_token_update)

    return AgentTokenResponse(
        agent_id=agent_id,
        token_type=token_type,
        masked_token=masked_token,
        updated_at=last_token_update,
    )


@router.delete("/agents/{agent_id}/tokens/{token_type}", status_code=204)
async def delete_agent_token(agent_id: int, token_type: str, db: Session = Depends(get_db)):
    """Delete a token for a Slack agent."""
    agent = db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    if token_type not in ["bot_token", "user_token", "app_token"]:
        raise HTTPException(status_code=400, detail="Invalid token type")

    token_store = get_token_store()

    # Delete the token
    token_store.delete_token(agent_id, token_type)

    # Update agent token flag
    if token_type == "bot_token":
        agent.set_field("has_bot_token", False)
    elif token_type == "user_token":
        agent.set_field("has_user_token", False)
    elif token_type == "app_token":
        agent.set_field("has_app_token", False)

    current_timestamp = datetime.now(UTC).isoformat()
    agent.set_field("last_token_update", current_timestamp)
    db.commit()

    return None


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: int, db: Session = Depends(get_db)):
    """Delete a Slack agent by ID."""
    agent = db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Delete any associated tokens
    token_store = get_token_store()
    token_store.delete_token(agent_id, "bot_token")
    token_store.delete_token(agent_id, "user_token")
    token_store.delete_token(agent_id, "app_token")

    # Delete the agent
    db.delete(agent)
    db.commit()

    return None


@router.post("/set-token", response_model=dict)
async def set_slack_token(request: Request):
    """Directly set the Slack bot token."""
    try:
        data = await request.json()
        token = data.get("token")

        if not token:
            raise HTTPException(status_code=400, detail="Token is required")

        # Store the token
        try:
            key_management.set_env_variable("SLACK_BOT_TOKEN", token)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to store token: {str(e)}") from e

        return {"success": True, "message": "Slack token has been set successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting Slack token: {str(e)}") from e


# Define a lifespan context manager for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Define startup and shutdown events for the FastAPI application."""
    # Run startup tasks
    db = next(get_db())
    try:
        logger.info("Running startup tasks for Slack API...")
        # Look for and recover orphaned workers
        await recover_orphaned_workers(db)
        logger.info("Slack API startup tasks completed.")
    except Exception as e:
        logger.error(f"Error in startup tasks: {e}")
    finally:
        db.close()

    # Yield control back to FastAPI
    yield

    # Cleanup on shutdown if needed
    logger.info("Shutting down Slack API...")


# Fix socket mode assignments for starting socket mode
@router.post("/agents/{agent_id}/socket-mode/start", response_model=SlackSocketModeResponse)
async def start_socket_mode(agent_id: int, db: Session = Depends(get_db)):
    """Start Socket Mode for a Slack agent."""
    agent = db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if the agent has an app token or if there's one in the environment
    has_app_token = bool(getattr(agent, "has_app_token", False))
    if not has_app_token and not os.getenv("SLACK_APP_TOKEN"):
        raise HTTPException(
            status_code=400,
            detail="Socket Mode requires an app token. Please configure an app token for this agent or set the SLACK_APP_TOKEN environment variable.",
        )

    # Check if the signing secret is configured
    signing_secret = os.getenv("SLACK_SIGNING_SECRET", "")
    if not signing_secret:
        raise HTTPException(
            status_code=400, detail="SLACK_SIGNING_SECRET environment variable not configured"
        )

    # Update the agent's socket_mode_enabled field - use set_field to avoid Column typing issues
    agent.set_field("socket_mode_enabled", True)
    db.commit()
    db.refresh(agent)

    # Import socket manager lazily to avoid circular imports
    from ..integrations.slack.socket_manager import SocketManager

    # Initialize socket manager and start worker
    socket_manager = SocketManager()
    success = socket_manager.start_worker(agent_id)

    if not success:
        # If worker failed to start, revert the socket_mode_enabled flag
        agent.set_field("socket_mode_enabled", False)
        db.commit()
        db.refresh(agent)
        raise HTTPException(status_code=500, detail="Failed to start Socket Mode worker")

    return SlackSocketModeResponse(
        agent_id=agent_id,
        socket_mode_active=True,
        message="Socket Mode worker started successfully.",
    )


@router.post("/agents/{agent_id}/socket-mode/stop", response_model=SlackSocketModeResponse)
async def stop_socket_mode(agent_id: int, db: Session = Depends(get_db)):
    """Stop Socket Mode for a Slack agent."""
    try:
        # Get agent
        agent = db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Check if socket mode is already disabled
        socket_mode_enabled = bool(getattr(agent, "socket_mode_enabled", False))
        if not socket_mode_enabled:
            return SlackSocketModeResponse(
                agent_id=agent_id,
                socket_mode_active=False,
                message="Socket Mode already disabled",
            )

        # Disable socket mode for the agent
        agent.set_field("socket_mode_enabled", False)
        db.commit()
        db.refresh(agent)

        # Import socket manager lazily to avoid circular imports
        from ..integrations.slack.socket_manager import SocketManager

        # Initialize socket manager and stop worker
        socket_manager = SocketManager()
        success = socket_manager.stop_worker(agent_id)

        message = (
            "Socket Mode worker stopped successfully."
            if success
            else "Failed to stop Socket Mode worker."
        )
        return SlackSocketModeResponse(
            agent_id=agent_id,
            socket_mode_active=False,
            message=message,
        )

    except Exception as e:
        logger.error(f"Error stopping socket mode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop Socket Mode: {str(e)}") from e


@router.get("/agents/{agent_id}/socket-mode/status", response_model=SlackSocketModeResponse)
async def get_socket_mode_status(agent_id: int, db: Session = Depends(get_db)):
    """Get Socket Mode status for a Slack agent."""
    agent = db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Import socket manager lazily to avoid circular imports
    from ..integrations.slack.socket_manager import SocketManager
    from ..integrations.slack.worker_status import find_running_worker_process, get_worker_status

    # Initialize socket manager
    socket_manager = SocketManager()

    # Check worker status through multiple methods to be robust
    logger.info(f"Checking socket mode status for agent {agent_id}")

    # Method 1: Check worker status through SocketManager
    worker_exists = agent_id in socket_manager.workers
    logger.info(f"Agent {agent_id} worker exists in manager: {worker_exists}")

    worker_running = False
    if worker_exists:
        worker_process = socket_manager.workers[agent_id]
        worker_running = worker_process.is_alive()
        logger.info(f"Agent {agent_id} worker process is alive: {worker_running}")

    # Method 2: Check marker files and processes
    worker_status = get_worker_status(agent_id)
    logger.info(f"Agent {agent_id} worker status from marker files: {worker_status}")

    # Method 3: Directly search for processes
    is_process_running, process_pid = find_running_worker_process(agent_id)
    logger.info(
        f"Agent {agent_id} process search result: running={is_process_running}, pid={process_pid}"
    )

    # Combine all results - if any method finds a running worker, consider it active
    worker_running = worker_running or worker_status["process_running"] or is_process_running
    logger.info(f"Agent {agent_id} combined worker running status: {worker_running}")

    # If we found a running process but it's not tracked in the socket manager, register it
    if (worker_status["process_running"] or is_process_running) and not worker_exists:
        pid = worker_status["pid"] if worker_status["process_running"] else process_pid
        if pid:
            logger.info(
                f"Registering previously untracked worker process for agent {agent_id}: pid={pid}"
            )
            process = psutil.Process(pid)
            # Store the psutil Process object directly
            socket_manager.workers[agent_id] = process
            worker_exists = True

    # Convert SQLAlchemy Columns to bool
    is_active = bool(getattr(agent, "is_active", True))
    trigger_enabled = bool(getattr(agent, "trigger_enabled", True))
    has_bot_token = bool(getattr(agent, "has_bot_token", False))
    socket_mode_enabled = bool(getattr(agent, "socket_mode_enabled", False))
    workflow_id = getattr(agent, "workflow_id", None)

    # Check if the agent should be active
    agent_is_active = (
        is_active
        and trigger_enabled
        and has_bot_token
        and workflow_id is not None
        and socket_mode_enabled
    )

    logger.info(f"Agent {agent_id} database state: socket_mode_enabled={socket_mode_enabled}")
    logger.info(f"Agent {agent_id} actual state: worker_running={worker_running}")

    # If worker is running but agent isn't marked as enabled in DB, update the DB
    if worker_running and not socket_mode_enabled:
        logger.info(f"Updating agent {agent_id} socket_mode_enabled to True to match actual state")
        agent.set_field("socket_mode_enabled", True)
        db.commit()
        db.refresh(agent)
        socket_mode_enabled = True
        agent_is_active = (
            is_active
            and trigger_enabled
            and has_bot_token
            and workflow_id is not None
            and socket_mode_enabled
        )

    # If agent is marked as enabled but worker isn't running, try to restart it
    elif socket_mode_enabled and not worker_running:
        # Wait a moment to ensure we're not catching a worker in the process of starting
        import asyncio

        await asyncio.sleep(1)

        # Check again after the delay
        if worker_exists:
            worker_running = socket_manager.workers[agent_id].is_alive()
            logger.info(f"After delay, agent {agent_id} worker is alive: {worker_running}")

        # Also check process finder again
        if not worker_running:
            is_process_running, _ = find_running_worker_process(agent_id)
            worker_running = is_process_running
            logger.info(f"After delay, process search result: running={is_process_running}")

        # If still not running, try to restart it
        if not worker_running:
            try:
                # Try to start the socket mode if the DB says it should be enabled
                logger.info(
                    f"Agent {agent_id} is marked as enabled but no worker is running - attempting to start socket mode"
                )
                success = socket_manager.start_worker(agent_id)
                if success:
                    logger.info(f"Successfully started worker for agent {agent_id}")
                    worker_running = True
                else:
                    # If we couldn't start it, update the DB to reflect reality
                    logger.info(
                        f"Failed to start worker for agent {agent_id}, updating DB state to match"
                    )
                    agent.set_field("socket_mode_enabled", False)
                    db.commit()
                    db.refresh(agent)
                    socket_mode_enabled = False
                    agent_is_active = False
            except Exception as e:
                logger.error(f"Error attempting to restore socket mode for agent {agent_id}: {e}")
                agent.set_field("socket_mode_enabled", False)
                db.commit()
                db.refresh(agent)
                socket_mode_enabled = False
                agent_is_active = False

    socket_mode_active = worker_running and agent_is_active
    logger.info(f"Final status for agent {agent_id}: socket_mode_active={socket_mode_active}")

    return SlackSocketModeResponse(
        agent_id=agent_id,
        socket_mode_active=socket_mode_active,
        message=f"Socket Mode worker is {'active' if socket_mode_active else 'inactive'}",
    )


@router.get("/agents/{agent_id}/debug-tokens")
async def debug_agent_tokens(agent_id: int, db: Session = Depends(get_db)):
    """Debug endpoint to check token storage for an agent."""
    agent = db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    token_store = get_token_store()

    # Check each token type
    token_info = {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "has_bot_token_flag": agent.has_bot_token,
        "has_user_token_flag": agent.has_user_token,
        "has_app_token_flag": agent.has_app_token,
        "last_token_update": _get_nullable_str(agent.last_token_update),
    }

    # Try to get each token and check if it exists
    try:
        bot_token = token_store.get_token(agent_id, "bot_token")
        token_info["bot_token_exists"] = bool(bot_token)
        if bot_token:
            token_info["bot_token_starts_with"] = bot_token[:5] + "..."
    except Exception as e:
        token_info["bot_token_error"] = str(e)

    try:
        user_token = token_store.get_token(agent_id, "user_token")
        token_info["user_token_exists"] = bool(user_token)
        if user_token:
            token_info["user_token_starts_with"] = user_token[:5] + "..."
    except Exception as e:
        token_info["user_token_error"] = str(e)

    try:
        app_token = token_store.get_token(agent_id, "app_token")
        token_info["app_token_exists"] = bool(app_token)
        if app_token:
            token_info["app_token_starts_with"] = app_token[:5] + "..."
    except Exception as e:
        token_info["app_token_error"] = str(e)

    return token_info


@router.post("/agents/{agent_id}/test-connection", response_model=dict)
async def test_connection(agent_id: int, db: Session = Depends(get_db)):
    """Test if the Slack connection for an agent works properly."""
    try:
        agent = db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")

        if not bool(agent.has_bot_token):
            return {"success": False, "message": "Agent doesn't have a bot token configured"}

        # Get the bot token from the token store
        token_store = get_token_store()
        bot_token = token_store.get_token(agent_id, "bot_token")

        if not bot_token:
            return {"success": False, "message": "Could not retrieve bot token"}

        # Test the token by calling auth.test
        client = AsyncWebClient(token=bot_token)

        try:
            response: AsyncSlackResponse = await client.auth_test()  # type: ignore
            response_data: Dict[str, Any] = response.data if isinstance(response.data, dict) else {}  # type: ignore
            if response_data.get("ok"):
                team = str(response_data.get("team", "Unknown workspace"))
                team_id = str(response_data.get("team_id", ""))
                user = str(response_data.get("user", "Unknown bot"))

                # Update the agent's team information
                if team_id:
                    agent.set_field("slack_team_id", team_id)
                    agent.set_field("slack_team_name", team)
                    db.commit()
                    logger.info(
                        f"Updated agent {agent_id} with team information: {team} ({team_id})"
                    )

                return {
                    "success": True,
                    "message": f"Successfully connected to {team} as {user}",
                    "team_id": team_id,
                    "bot_id": response_data["bot_id"],
                    "user_id": response_data["user_id"],
                }
            else:
                return {
                    "success": False,
                    "message": (
                        f"API call succeeded but returned not OK: "
                        f"{response_data.get('error', 'Unknown error')}"
                    ),
                }
        except SlackApiError as e:
            error_response = cast(Dict[str, Any], getattr(e, "response", {}))
            error_message = str(error_response.get("error", str(e)))
            return {"success": False, "message": f"API Error: {error_message}"}
    except Exception as e:
        logger.error(f"Error testing Slack connection: {e}")
        return {"success": False, "message": f"Error: {str(e)}", "error": str(e)}


@router.post("/socket-workers/recover", status_code=200)
async def recover_orphaned_workers(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Find and recover any orphaned socket workers during backend startup.

    This checks for worker marker files and ensures the database state
    reflects any running workers.
    """
    try:
        # Import socket manager lazily to avoid circular imports
        from ..integrations.slack.socket_manager import SocketManager

        socket_manager = SocketManager()

        # Check for marker files indicating running workers
        marker_dir = "/tmp/pyspur_socket_workers"
        if not os.path.exists(marker_dir):
            logger.info("No socket worker marker directory found, skipping recovery")
            return {"recovered": 0, "message": "No marker directory found"}

        recovered = 0
        markers: List[int] = []

        # Look for marker files matching agent_*.pid pattern
        for filename in os.listdir(marker_dir):
            if filename.startswith("agent_") and filename.endswith(".pid"):
                try:
                    # Extract agent ID from filename
                    agent_id_str = filename[6:-4]  # Remove "agent_" prefix and ".pid" suffix
                    agent_id = int(agent_id_str)
                    markers.append(agent_id)

                    # Check if process is running
                    pid_file = os.path.join(marker_dir, filename)
                    with open(pid_file, "r") as f:
                        pid = int(f.read().strip())

                    # Check if process is still running
                    is_running = False

                    process = psutil.Process(pid)
                    # Check if the command line contains socket_worker.py
                    cmdline = process.cmdline()
                    cmdline_str = " ".join(cmdline)
                    if (
                        "socket_worker.py" in cmdline_str
                        and f"SLACK_AGENT_ID={agent_id}" in cmdline_str
                    ):
                        is_running = True
                        logger.info(f"Found running worker process for agent {agent_id}: pid={pid}")

                    if is_running:
                        # Update the agent record to reflect the running worker
                        agent = (
                            db.query(SlackAgentModel).filter(SlackAgentModel.id == agent_id).first()
                        )
                        if agent:
                            if not bool(getattr(agent, "socket_mode_enabled", False)):
                                logger.info(
                                    f"Recovering agent {agent_id} - worker is running but DB state was socket_mode_enabled=False"
                                )
                                agent.set_field("socket_mode_enabled", True)
                                db.commit()

                                # Try to register the process with the socket manager
                                try:
                                    process = psutil.Process(pid)
                                    # Store the psutil Process object directly
                                    socket_manager.workers[agent_id] = process
                                    recovered += 1
                                except Exception as e:
                                    logger.error(f"Error registering worker process: {e}")
                        else:
                            logger.warning(
                                f"Found marker for agent {agent_id}, but agent does not exist in database"
                            )
                    else:
                        # Process is not running - clean up the marker file
                        logger.warning(f"Found stale marker file for agent {agent_id}, removing")
                        try:
                            os.remove(pid_file)
                        except Exception as e:
                            logger.error(f"Error removing stale marker file: {e}")
                except Exception as e:
                    logger.error(f"Error processing marker file {filename}: {e}")

        return {
            "recovered": recovered,
            "markers": markers,
            "message": f"Recovered {recovered} worker(s)",
        }
    except Exception as e:
        logger.error(f"Error in recover_orphaned_workers: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"recovered": 0, "error": str(e)}
