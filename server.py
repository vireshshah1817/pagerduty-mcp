"""
    PagerDuty MCP Server
    This script creates a Model Context Protocol (MCP) server that connects AI assistants 
    to your PagerDuty account, allowing them to fetch active incidents.
"""

import os
import httpx
from mcp.server.fastmcp import FastMCP


port = int(os.getenv("PORT", 8080))
# Initialize the MCP Server
mcp = FastMCP(
    "PagerDuty-GCP", 
    host="0.0.0.0", 
    port=port
)

PAGERDUTY_API_KEY = os.getenv("PAGERDUTY_API_KEY")
PAGERDUTY_USER_EMAIL = os.getenv("PAGERDUTY_USER_EMAIL")
PD_BASE_URL = "https://api.pagerduty.com"

def get_headers(require_email=False):
    """
        Constructs the HTTP headers required by the PagerDuty API.
        It includes the authorization token and specifies the API version.
    """

    headers = {
        "Authorization": f"Token token={PAGERDUTY_API_KEY}",
        "Accept": "application/vnd.pagerduty+json;version=2",
        "Content-Type": "application/json"
    }
    # If the tool modifies data, PagerDuty requires the 'From' header
    if require_email and PAGERDUTY_USER_EMAIL:
        headers["From"] = PAGERDUTY_USER_EMAIL

    return headers


@mcp.tool()
async def list_incidents(limit: int = 5) -> str:
    """
        Fetch the latest unresolved incidents from PagerDuty.
    """

    if not PAGERDUTY_API_KEY:
        return "Error: PAGERDUTY_API_KEY environment variable is missing."

    # Open an asynchronous HTTP session. Using 'async with' ensures the 
    # connection is properly closed after the request is finished
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PD_BASE_URL}/incidents",
            headers=get_headers(),
            params={"limit": limit, "statuses[]": ["triggered", "acknowledged"]}
        )
        response.raise_for_status()
        incidents = response.json().get("incidents", [])
        
        if not incidents:
            return "No unresolved incidents found."
            
        result = "Current PagerDuty Incidents:\n"
        for inc in incidents:
            result += f"- [{inc['status'].upper()}] {inc['title']} (URL: {inc['html_url']})\n"

        return result
    

@mcp.tool()
async def acknowledge_incident(incident_id: str) -> str:
    """
        Acknowledge a specific PagerDuty incident to halt the escalation policy.
        Requires the incident's ID (e.g., 'PT4KHLK').
    """
    if not PAGERDUTY_API_KEY or not PAGERDUTY_USER_EMAIL:
        return "Error: Both PAGERDUTY_API_KEY and PAGERDUTY_USER_EMAIL environment variables are required to update incidents."

    # The payload tells PagerDuty we want to update the status to "acknowledged"
    payload = {
        "incident": {
            "type": "incident_reference",
            "status": "acknowledged"
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{PD_BASE_URL}/incidents/{incident_id}",
            # Pass require_email=True to inject the 'From' header
            headers=get_headers(require_email=True),
            json=payload
        )
        
        if response.status_code == 200:
            inc = response.json().get("incident", {})
            return f"✅ Successfully acknowledged incident '{inc.get('title')}' (ID: {incident_id})."
        else:
            return f"❌ Failed to acknowledge incident. API returned: {response.status_code} - {response.text}"


if __name__ == "__main__":
    # Use SSE transport for both local testing and Cloud Run deployment
    # Cloud Run injects the PORT environment variable (defaults to 8080)
    # port = int(os.getenv("PORT", 8080)
    host = "0.0.0.0" # Must bind to 0.0.0.0 for Docker/Cloud Run
    
    try:
        # For mcp Python SDK versions < 1.27
        mcp.run(transport="sse", host=host, port=port)
    except TypeError:
        # For mcp Python SDK versions >= 1.27
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.run(transport="sse")
