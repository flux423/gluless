import urllib.request
import urllib.parse
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from gluless.models import Utility

@dataclass
class ExecutableBinding:
    server: str
    method: str
    path: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Any] = field(default_factory=dict)

    def execute(self, inputs: Dict[str, Any]) -> Any:
        """
        Executes the binding as a real HTTP request using urllib.
        Interpolates path parameters and appends query parameters.
        """
        # Interpolate path parameters
        url_path = self.path
        query_params = {}
        
        path_param_names = [p["name"] for p in self.parameters if p.get("in") == "path"]
        query_param_names = [p["name"] for p in self.parameters if p.get("in") == "query"]

        for name, val in inputs.items():
            if name in path_param_names:
                url_path = url_path.replace(f"{{{name}}}", str(val))
            elif name in query_param_names:
                query_params[name] = str(val)

        # Build full URL
        base_url = self.server.rstrip("/")
        full_url = f"{base_url}{url_path}"
        if query_params:
            full_url += "?" + urllib.parse.urlencode(query_params)

        # Prepare request body
        data_bytes = None
        headers = {}
        
        # Check if we should extract request body properties from inputs
        if self.method.upper() in ("POST", "PUT", "PATCH"):
            headers["Content-Type"] = "application/json"
            # If inputs contains a key that is the request body itself, or we map matching body fields
            body_payload = {}
            if self.request_body and isinstance(self.request_body, dict):
                props = self.request_body.get("properties", {})
                for prop_name in props:
                    if prop_name in inputs:
                        body_payload[prop_name] = inputs[prop_name]
            
            # Fallback to direct input if no body properties matched
            if not body_payload and inputs:
                body_payload = inputs

            data_bytes = json.dumps(body_payload).encode("utf-8")

        req = urllib.request.Request(full_url, data=data_bytes, headers=headers, method=self.method.upper())
        
        try:
            with urllib.request.urlopen(req) as response:
                status_code = response.status
                response_body = response.read().decode("utf-8")
                
                # Try parsing as JSON
                try:
                    res_data = json.loads(response_body)
                except Exception:
                    res_data = response_body
                    
                return {
                    "status_code": status_code,
                    "body": res_data
                }
        except urllib.error.HTTPError as e:
            # Handle non-2xx responses gracefully for verification
            try:
                err_body = json.loads(e.read().decode("utf-8"))
            except Exception:
                err_body = e.reason
            return {
                "status_code": e.code,
                "body": err_body,
                "error": str(e)
            }
        except Exception as e:
            return {
                "status_code": 500,
                "body": {},
                "error": str(e)
            }

class UtilityResolver:
    """
    Resolves a semantic Utility to an ExecutableBinding.
    """
    def __init__(self, server_url: str):
        self.server_url = server_url

    def resolve(self, utility: Utility) -> ExecutableBinding:
        t = utility.transport
        # Use transport server if defined, otherwise fall back to target server_url
        server = self.server_url
        return ExecutableBinding(
            server=server,
            method=t.method,
            path=t.path,
            parameters=t.parameters,
            request_body=t.request_body,
            responses=t.responses
        )
