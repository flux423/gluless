import yaml
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from gluless.models import Utility, UtilityTransport, UtilityType, SideEffectType

def resolve_ref(ref_str: str, document: Dict[str, Any]) -> Any:
    if not ref_str.startswith("#/"):
        return {"$ref": ref_str}
    parts = ref_str.lstrip("#/").split("/")
    curr = document
    for part in parts:
        if isinstance(curr, dict) and part in curr:
            curr = curr[part]
        elif isinstance(curr, list):
            try:
                curr = curr[int(part)]
            except (ValueError, IndexError):
                return {"$ref": ref_str}
        else:
            return {"$ref": ref_str}
    return curr

def resolve_all_refs(node: Any, document: Dict[str, Any], resolved_paths: Optional[set] = None) -> Any:
    if resolved_paths is None:
        resolved_paths = set()
        
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str):
            ref = node["$ref"]
            if ref in resolved_paths:
                return {"$ref": ref}
            resolved_paths.add(ref)
            resolved_val = resolve_ref(ref, document)
            return resolve_all_refs(resolved_val, document, resolved_paths)
        return {k: resolve_all_refs(v, document, resolved_paths.copy()) for k, v in node.items()}
    elif isinstance(node, list):
        return [resolve_all_refs(item, document, resolved_paths.copy()) for item in node]
    return node

def derive_utility_name(method: str, path: str, operation_id: Optional[str] = None) -> Tuple[str, str]:
    # Clean version/prefix segments
    path_clean = path.strip("/")
    segments = path_clean.split("/")
    
    # Skip common version prefixes (v0, v1, api, etc.)
    prefix_patterns = [r"^v[0-9]+$", r"^api$", r"^v[0-9]+\.[0-9]+$"]
    while segments and any(re.match(pattern, segments[0], re.IGNORECASE) for pattern in prefix_patterns):
        segments.pop(0)
        
    if not segments:
        return ("root", method.lower())
        
    # Filter parameter slots to get clean word segments
    word_segments = [seg for seg in segments if not (seg.startswith("{") and seg.endswith("}"))]
    if not word_segments:
        # Fall back to segments if all segments were parameter slots
        word_segments = [seg.replace("{", "").replace("}", "") for seg in segments]
        
    resource = word_segments[0]
    
    # Try to derive action
    if operation_id:
        # Extract camelCase/snake_case action prefix
        # e.g., listCities -> list, nudgeSession -> nudge
        # Find first lowercase word segment or verb
        match = re.match(r"^([a-z]+)", operation_id)
        if match:
            action = match.group(1)
            # If action matches resource name exactly, check verb
            if action.lower() == resource.lower() and len(operation_id) > len(action):
                # Fall back to method-based mapping if action is just resource name
                pass
            else:
                # Map common action verbs to standardized names
                verb_mapping = {
                    "get": "read",
                    "show": "read",
                    "post": "create",
                    "put": "update",
                    "patch": "update"
                }
                action = verb_mapping.get(action.lower(), action)
                return (resource, action)
                
    # Fallback to path segment structures + method
    if len(word_segments) > 1:
        # If segments has multiple names (e.g. sessions/nudge), action is the last segment
        action = word_segments[-1]
    else:
        # Standard HTTP mapping
        method_upper = method.upper()
        if method_upper == "GET":
            # If path ends with parameter slot (e.g. /{id}), it is a read. Otherwise list.
            if segments[-1].startswith("{") and segments[-1].endswith("}"):
                action = "read"
            else:
                action = "list"
        elif method_upper == "POST":
            action = "create"
        elif method_upper in ("PUT", "PATCH"):
            action = "update"
        elif method_upper == "DELETE":
            action = "delete"
        else:
            action = method.lower()
            
    return (resource, action)

class OpenAPIImporter:
    def __init__(self, default_namespace: str = "Default"):
        self.default_namespace = default_namespace

    def import_spec(self, spec_content: str) -> List[Utility]:
        # Load content as YAML (YAML is a superset of JSON, so this handles both)
        document = yaml.safe_load(spec_content)
        if not isinstance(document, dict):
            raise ValueError("Invalid OpenAPI document structure")
            
        # Determine namespace from custom x-provider-name or info title
        namespace = self.default_namespace
        if "x-provider-name" in document:
            namespace = document["x-provider-name"]
        elif "info" in document and isinstance(document["info"], dict) and "title" in document["info"]:
            # Slugify info title as a fallback namespace
            title = document["info"]["title"]
            namespace = re.sub(r'[^a-zA-Z0-9]', '', title)
            
        utilities = []
        paths = document.get("paths", {})
        
        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
                
            # Keep path-level parameters
            path_params = path_item.get("parameters", [])
            
            for method, operation in path_item.items():
                if method.lower() in ("parameters", "$ref") or not isinstance(operation, dict):
                    continue
                    
                # Clean and resolve refs inside the operation
                op_resolved = resolve_all_refs(operation, document)
                
                # Combine path parameters and operation parameters
                op_params = op_resolved.get("parameters", [])
                combined_params = path_params + op_params
                resolved_params = resolve_all_refs(combined_params, document)
                
                # Determine names
                resource, action = derive_utility_name(method, path, op_resolved.get("operationId"))
                
                # Support overrides via extensions
                custom_name = op_resolved.get("x-gluless-name")
                if custom_name:
                    parts = custom_name.split(".")
                    if len(parts) >= 3:
                        ns = parts[0]
                        resource = parts[1]
                        action = ".".join(parts[2:])
                    elif len(parts) == 2:
                        ns = namespace
                        resource = parts[0]
                        action = parts[1]
                    else:
                        ns = namespace
                        action = custom_name
                else:
                    ns = namespace
                    
                utility_id = f"{ns}.{resource}.{action}"
                short_name = f"{resource}.{action}"
                
                # Determine SideEffectType and UtilityType
                method_upper = method.upper()
                if method_upper == "GET":
                    side_effects = SideEffectType.READ
                    utility_type = UtilityType.READ
                elif method_upper == "POST":
                    side_effects = SideEffectType.CREATE
                    utility_type = UtilityType.MUTATION
                elif method_upper in ("PUT", "PATCH"):
                    side_effects = SideEffectType.UPDATE
                    utility_type = UtilityType.MUTATION
                elif method_upper == "DELETE":
                    side_effects = SideEffectType.DELETE
                    utility_type = UtilityType.MUTATION
                else:
                    side_effects = SideEffectType.UNKNOWN
                    utility_type = UtilityType.MUTATION
                    
                # Support extension overrides for types and side effects
                custom_type = op_resolved.get("x-gluless-type")
                if custom_type:
                    try:
                        utility_type = UtilityType(custom_type.lower())
                    except ValueError:
                        pass
                        
                custom_side_effects = op_resolved.get("x-gluless-side-effects")
                if custom_side_effects:
                    try:
                        side_effects = SideEffectType(custom_side_effects.lower())
                    except ValueError:
                        pass
                        
                # Extract Request Body schema
                req_body = op_resolved.get("requestBody")
                resolved_req_body = None
                if req_body and isinstance(req_body, dict):
                    content = req_body.get("content", {})
                    # Prefer application/json schema
                    json_content = content.get("application/json", {})
                    resolved_req_body = json_content.get("schema")
                    
                # Extract Responses schemas
                responses = op_resolved.get("responses", {})
                resolved_responses = {}
                for status, resp in responses.items():
                    if isinstance(resp, dict):
                        content = resp.get("content", {})
                        json_content = content.get("application/json", {})
                        schema = json_content.get("schema")
                        if schema:
                            resolved_responses[status] = schema
                        else:
                            resolved_responses[status] = {"type": "object", "properties": {}}
                            
                # Transport Definition
                transport = UtilityTransport(
                    type="openapi",
                    method=method_upper,
                    path=path,
                    parameters=resolved_params,
                    request_body=resolved_req_body,
                    responses=resolved_responses
                )
                
                # Auth requirements
                security = op_resolved.get("security", document.get("security", []))
                
                utilities.append(Utility(
                    id=utility_id,
                    name=short_name,
                    namespace=ns,
                    description=op_resolved.get("summary") or op_resolved.get("description") or "",
                    type=utility_type,
                    side_effects=side_effects,
                    transport=transport,
                    auth=security
                ))
                
        return utilities
